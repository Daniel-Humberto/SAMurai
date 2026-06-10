import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
import asyncio
import base64
import csv
import json
import queue
import random
import threading
import time

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.config import DEVICE, FPS_CAP, PORT
from app.state import InferenceState
from app.model import Segmenter

state = InferenceState()
segmenter = Segmenter()

app = FastAPI(title="SAM2 Live v6")
app.mount("/static", StaticFiles(directory="/app/static"), name="static")

# CSV Path for Trajectories
os.makedirs("/app/outputs", exist_ok=True)
CSV_PATH = "/app/outputs/trajectories.csv"

# Global references for recording
video_writer = None
current_recording_path = None


class VideoCaptureThread:
    def __init__(self, source: str):
        self.source = int(source) if source.isdigit() else source
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            print(f"[Capture Thread] Error: No se pudo abrir la fuente {self.source}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        self.queue = queue.Queue(maxsize=3)
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                # Auto-loop video files
                if isinstance(self.source, str):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                time.sleep(0.033)
                continue

            # Push to queue, dropping older frames if queue is full
            if self.queue.full():
                try:
                    self.queue.get_nowait()
                except queue.Empty:
                    pass
            self.queue.put(frame)
            time.sleep(0.01)

    def read(self):
        try:
            frame = self.queue.get(timeout=0.1)
            return True, frame
        except queue.Empty:
            return False, None

    def release(self):
        self.running = False
        try:
            self.thread.join(timeout=1.0)
        except Exception:
            pass
        self.cap.release()


@app.get("/")
async def root():
    return HTMLResponse(open("/app/static/index.html").read())


@app.post("/config")
async def set_config(body: dict):
    state.apply_config(body)
    if "source" in body:
        state.set_source(body["source"])
    return {"ok": True}


@app.post("/object/add")
async def add_object(body: dict):
    obj_id = body.get("id")
    name = body.get("name", f"Objeto {obj_id}")
    color = body.get("color", [random.randint(50, 255) for _ in range(3)])
    state.add_object(obj_id, name, color)
    return {"ok": True}


@app.post("/object/remove")
async def remove_object(body: dict):
    obj_id = body.get("id")
    state.remove_object(obj_id)
    return {"ok": True}


@app.get("/status")
async def get_status():
    with state:
        objs_info = []
        for oid, obj in state.objects.items():
            objs_info.append({
                "id": oid,
                "name": obj["name"],
                "color": obj["color"],
                "points_count": len(obj["points"]),
                "has_mask": obj["mask"] is not None
            })
        return {
            "device": DEVICE,
            "mode": state.mode,
            "fps": round(state.fps, 1),
            "active_obj_id": state.active_obj_id,
            "objects": objs_info,
            "render_mode": state.render_mode,
            "blur_background": state.blur_background,
            "is_recording": state.is_recording
        }


@app.post("/restart")
async def restart_system():
    # Reset states
    state.clear_all_points()
    with state:
        state.sam2_state_initialized = False
        state.current_frame_idx = 0
        state.source_changed = True
    return {"ok": True}


@app.post("/hard-restart")
async def hard_restart():
    import os
    import time

    def force_exit():
        time.sleep(0.5)
        os._exit(0)

    asyncio.create_task(asyncio.to_thread(force_exit))
    return {"ok": True, "message": "Contenedor reiniciando..."}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    print("[WS] Cliente conectado v6")

    # Reset state on connection
    state.clear_all_points()
    with state:
        state.sam2_state_initialized = False
        state.current_frame_idx = 0
        state.auto_masks = None

    cap_thread = None
    loop = asyncio.get_event_loop()
    paused_frame = None
    inference_state = None
    auto_frame_counter = 0
    auto_updating = False
    loop_frame_counter = 0

    def get_source():
        src = state.consume_source_changed()
        if src is None:
            with state:
                src = state.source
        return src

    try:
        while True:
            frame_start_time = time.time()
            loop_frame_counter += 1

            if loop_frame_counter % 30 == 0:
                import torch
                import gc
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            # Initialize capture thread if none
            if cap_thread is None:
                src = get_source()
                cap_thread = VideoCaptureThread(src)
                # Wait briefly for frames to load
                await asyncio.sleep(0.5)

            # Check if source changed
            new_src = state.consume_source_changed()
            if new_src is not None:
                cap_thread.release()
                cap_thread = VideoCaptureThread(new_src)
                with state:
                    state.sam2_state_initialized = False
                    state.current_frame_idx = 0
                if inference_state is not None:
                    segmenter.reset_predictor_state(inference_state)
                    inference_state = None
                await asyncio.sleep(0.5)

            # Non-blocking WebSocket message polling
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=0.001)
                _handle_message(json.loads(msg))
            except asyncio.TimeoutError:
                pass

            err = segmenter.pop_error()
            if err:
                try:
                    await ws.send_text(json.dumps({"error": f"SAM2 Live v6: {err}"}))
                except Exception:
                    pass

            with state:
                mode = state.mode

            if mode == "off":
                # Static paused frame mode
                if paused_frame is None:
                    ret, frame = cap_thread.read()
                    if ret:
                        paused_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                if paused_frame is not None:
                    # Initialize in-memory state if needed
                    with state:
                        init_needed = not state.sam2_state_initialized or inference_state is None
                    
                    if init_needed:
                        if inference_state is not None:
                            segmenter.reset_predictor_state(inference_state)
                        inference_state = segmenter.init_in_memory_state(paused_frame)
                        with state:
                            state.sam2_state_initialized = True
                            state.current_frame_idx = 0

                    out, telemetries = _process_frame_step(paused_frame, inference_state, mode, frame_is_static=True)
                    state.update_fps()
                    with state:
                        current_fps = state.fps
                    await _send_frame(ws, out, current_fps, mode, telemetries)
                    _handle_recording(out)

                elapsed = time.time() - frame_start_time
                await asyncio.sleep(max(0.001, 0.033 - elapsed))
                continue

            # Mode != off
            paused_frame = None
            ret, frame = cap_thread.read()
            if not ret:
                await asyncio.sleep(0.005)
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            if mode == "auto":
                needs_refresh = state.auto_masks is None
                if not needs_refresh and auto_frame_counter > 0 and auto_frame_counter % 60 == 0:
                    needs_refresh = True

                if needs_refresh and not auto_updating:
                    auto_updating = True

                    def run_auto_in_bg(img):
                        try:
                            return segmenter.predict_auto(img)
                        finally:
                            nonlocal auto_updating
                            auto_updating = False

                    async def update_auto_masks(img):
                        new_masks = await loop.run_in_executor(None, run_auto_in_bg, img)
                        with state:
                            state.auto_masks = new_masks
                            state.auto_colors = [[random.randint(50, 255) for _ in range(3)] for _ in new_masks]

                    asyncio.create_task(update_auto_masks(frame_rgb.copy()))

                out, auto_count = _process_auto_render(frame_rgb)
                auto_frame_counter += 1
                telemetries = []
                state.update_fps()
                with state:
                    current_fps = state.fps
                await _send_frame(ws, out, current_fps, mode, telemetries, auto_count)
                _handle_recording(out)
            else:
                # Segment or Track mode
                with state:
                    init_needed = not state.sam2_state_initialized or inference_state is None
                
                if init_needed:
                    if inference_state is not None:
                        segmenter.reset_predictor_state(inference_state)
                    inference_state = segmenter.init_in_memory_state(frame_rgb)
                    with state:
                        state.sam2_state_initialized = True
                        state.current_frame_idx = 0
                else:
                    # Append new frame to list
                    f_idx = segmenter.add_frame(inference_state, frame_rgb)
                    with state:
                        state.current_frame_idx = f_idx

                out, telemetries = _process_frame_step(frame_rgb, inference_state, mode, frame_is_static=False)
                _log_trajectories_csv(telemetries)
                state.update_fps()
                with state:
                    current_fps = state.fps
                await _send_frame(ws, out, current_fps, mode, telemetries)
                _handle_recording(out)

            # Maintain frame cap rate without compounding latency
            elapsed = time.time() - frame_start_time
            sleep_time = max(0.001, (1.0 / FPS_CAP) - elapsed)
            await asyncio.sleep(sleep_time)

    except WebSocketDisconnect:
        print("[WS] Cliente desconectado")
    finally:
        if cap_thread is not None:
            cap_thread.release()
        if inference_state is not None:
            segmenter.reset_predictor_state(inference_state)
        _release_recording()


def _handle_message(data: dict):
    t = data.get("type")
    if t == "click":
        label = 1 if data.get("button", "left") == "left" else 0
        state.add_point(int(data["x"]), int(data["y"]), label)
    elif t == "clear":
        state.clear_points()
    elif t == "clear_all":
        state.clear_all_points()
    elif t == "config":
        state.apply_config(data)
        if "source" in data:
            state.set_source(data["source"])


def _process_frame_step(frame_rgb: np.ndarray, inference_state: dict, mode: str, frame_is_static: bool = False):
    with state:
        frame_idx = state.current_frame_idx
        objects = {oid: dict(obj) for oid, obj in state.objects.items()}

    # Add clicks to any object which has uncomputed points
    for oid, obj in objects.items():
        # Points added on the active object that haven't been computed
        if obj["points"] and obj["mask"] is None:
            updated_masks = segmenter.add_clicks(inference_state, frame_idx, oid, obj["points"], obj["labels"])
            # Update state with click output masks
            for m_id, m_val in updated_masks.items():
                with state:
                    if m_id in state.objects:
                        state.objects[m_id]["mask"] = m_val

    # If in track mode and it's not a static frame, perform the propagation step
    if mode == "track" and not frame_is_static and frame_idx > 0:
        tracked_masks = segmenter.track_step(inference_state, frame_idx)
        for m_id, m_val in tracked_masks.items():
            with state:
                if m_id in state.objects:
                    state.objects[m_id]["mask"] = m_val

    # Render results
    telemetry_list = []
    out = _render_overlay(frame_rgb, state, telemetry_list)
    return out, telemetry_list


def _process_auto_render(frame_rgb: np.ndarray):
    with state:
        masks_data = state.auto_masks
        colors = list(state.auto_colors)
        opacity = state.opacity
        render_mode = state.render_mode
        blur_background = state.blur_background
        blur_strength = state.blur_strength

    h, w = frame_rgb.shape[:2]

    # Blur background
    if blur_background:
        ksize = max(3, blur_strength | 1)
        blurred = cv2.GaussianBlur(frame_rgb, (ksize, ksize), 0)
    else:
        blurred = None

    # Compute combined auto mask
    combined_mask = np.zeros((h, w), dtype=bool)
    if masks_data:
        for md in masks_data:
            combined_mask |= md["segmentation"]

    # Base frame
    if render_mode == "chroma_key":
        out = np.zeros_like(frame_rgb)
        out[:, :] = [0, 255, 0]
    elif render_mode == "alpha_mask":
        out = np.zeros_like(frame_rgb)
    else:
        out = frame_rgb.copy()

    # Draw blurred background
    if render_mode == "normal" and blur_background and blurred is not None:
        out = np.where(combined_mask[:, :, None], out, blurred)

    # Blend original content onto Chroma Key / Alpha Mask inside masks
    if render_mode in ("chroma_key", "alpha_mask"):
        if render_mode == "chroma_key":
            out = np.where(combined_mask[:, :, None], frame_rgb, out)
        else:
            out = np.where(combined_mask[:, :, None], [255, 255, 255], out)

    # Draw colored masks
    if render_mode in ("normal", "chroma_key") and masks_data:
        overlay = np.zeros_like(out)
        for i, md in enumerate(masks_data):
            seg = md["segmentation"]
            c = colors[i % len(colors)]
            overlay[seg] = c
        out = cv2.addWeighted(out, 1 - opacity, overlay, opacity, 0)

    out = out.astype(np.uint8)
    return out, len(masks_data) if masks_data else 0


def _render_overlay(frame: np.ndarray, state_obj: InferenceState, telemetry_list: list) -> np.ndarray:
    with state_obj:
        render_mode = state_obj.render_mode
        blur_background = state_obj.blur_background
        blur_strength = state_obj.blur_strength
        opacity = state_obj.opacity
        show_contour = state_obj.show_contour
        show_points = state_obj.show_points
        objects = {oid: dict(obj) for oid, obj in state_obj.objects.items()}

    h, w = frame.shape[:2]

    # Blur background
    if blur_background:
        ksize = max(3, blur_strength | 1)
        blurred = cv2.GaussianBlur(frame, (ksize, ksize), 0)
    else:
        blurred = None

    # Compute combined mask
    combined_mask = np.zeros((h, w), dtype=bool)
    for oid, obj in objects.items():
        if obj["mask"] is not None:
            combined_mask |= obj["mask"]

    # Base frame
    if render_mode == "chroma_key":
        out = np.zeros_like(frame)
        out[:, :] = [0, 255, 0]
    elif render_mode == "alpha_mask":
        out = np.zeros_like(frame)
    else:
        out = frame.copy()

    # Draw blurred background
    if render_mode == "normal" and blur_background and blurred is not None:
        out = np.where(combined_mask[:, :, None], out, blurred)

    # Blend original content onto Chroma Key / Alpha Mask inside masks
    if render_mode in ("chroma_key", "alpha_mask"):
        if render_mode == "chroma_key":
            out = np.where(combined_mask[:, :, None], frame, out)
        else:
            out = np.where(combined_mask[:, :, None], np.array([255, 255, 255], dtype=np.uint8), out)

    # Draw colored overlay masks
    if render_mode in ("normal", "chroma_key"):
        overlay = np.zeros_like(out)
        for oid, obj in objects.items():
            mask = obj["mask"]
            if mask is not None:
                color = obj["color"]
                overlay[mask] = color

                # Render contour
                if show_contour:
                    m8 = (mask * 255).astype(np.uint8)
                    contours, _ = cv2.findContours(m8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cv2.drawContours(out, contours, -1, color, 2)

        out = cv2.addWeighted(out, 1 - opacity, overlay, opacity, 0)

    # Draw point prompts
    if show_points and render_mode != "alpha_mask":
        for oid, obj in objects.items():
            pts = obj["points"]
            lbls = obj["labels"]
            color = obj["color"]
            for (px, py), lbl in zip(pts, lbls):
                c_inner = (80, 255, 120) if lbl == 1 else (255, 80, 80)
                c_outer = tuple(color)
                cv2.circle(out, (px, py), 6, c_inner, -1)
                cv2.circle(out, (px, py), 8, c_outer, 2)
                cv2.circle(out, (px, py), 9, (255, 255, 255), 1)

    # Compute telemetries
    for oid, obj in objects.items():
        mask = obj["mask"]
        if mask is not None and np.any(mask):
            y_idx, x_idx = np.where(mask)
            cx = float(np.mean(x_idx))
            cy = float(np.mean(y_idx))
            area = int(len(x_idx))
            telemetry_list.append({
                "id": oid,
                "name": obj["name"],
                "color": obj["color"],
                "cx": round(cx / w, 4),
                "cy": round(cy / h, 4),
                "area_px": area,
                "area_pct": round(area / (w * h) * 100, 2)
            })

    return out


async def _send_frame(ws: WebSocket, out: np.ndarray, fps: float, mode: str, telemetries: list, auto_count: int = 0):
    _, buf = cv2.imencode(
        ".jpg", cv2.cvtColor(out, cv2.COLOR_RGB2BGR),
        [cv2.IMWRITE_JPEG_QUALITY, 80],
    )
    b64 = base64.b64encode(buf).decode()
    payload = {
        "frame": b64,
        "fps": round(fps, 1),
        "mode": mode,
        "auto_count": auto_count,
        "telemetry": telemetries
    }
    await ws.send_text(json.dumps(payload))


def _handle_recording(out_frame: np.ndarray):
    global video_writer, current_recording_path
    with state:
        is_rec = state.is_recording

    if is_rec:
        if video_writer is None:
            current_recording_path = f"/app/outputs/recording_{int(time.time())}.mp4"
            h, w = out_frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            video_writer = cv2.VideoWriter(current_recording_path, fourcc, 20.0, (w, h))
            print(f"[Recording] Iniciando grabación en {current_recording_path}")
        video_writer.write(cv2.cvtColor(out_frame, cv2.COLOR_RGB2BGR))
    else:
        _release_recording()


def _release_recording():
    global video_writer, current_recording_path
    if video_writer is not None:
        video_writer.release()
        video_writer = None
        print(f"[Recording] Grabación guardada en {current_recording_path}")
        current_recording_path = None


def _log_trajectories_csv(telemetries: list):
    if not telemetries:
        return
    file_exists = os.path.exists(CSV_PATH)
    try:
        with open(CSV_PATH, mode="a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "object_id", "object_name", "centroid_x", "centroid_y", "area_px", "area_pct"])
            now = time.time()
            for tel in telemetries:
                writer.writerow([
                    now,
                    tel["id"],
                    tel["name"],
                    tel["cx"],
                    tel["cy"],
                    tel["area_px"],
                    tel["area_pct"]
                ])
    except Exception as e:
        print(f"Error escribiendo trayectoria a CSV: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
