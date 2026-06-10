import threading
import time
import numpy as np


class InferenceState:
    def __init__(self):
        # Multi-object dictionary structure:
        # {
        #    obj_id: {
        #        "points": [[x, y], ...],
        #        "labels": [label, ...],
        #        "mask": np.ndarray | None,
        #        "color": [r, g, b],
        #        "name": str
        #    }
        # }
        self.objects: dict = {
            1: {
                "points": [],
                "labels": [],
                "mask": None,
                "color": [0, 230, 100],  # default bright green
                "name": "Objeto 1"
            }
        }
        self.active_obj_id: int = 1
        self.mode: str = "segment"  # segment, track, auto, off
        self.opacity: float = 0.45
        self.show_contour: bool = True
        self.show_points: bool = True
        self.source: str = "0"
        self.source_changed: bool = False

        # Visual Modes
        self.render_mode: str = "normal"  # normal, chroma_key, alpha_mask
        self.blur_background: bool = False
        self.blur_strength: int = 21

        # Recording State
        self.is_recording: bool = False
        self.recording_path: str | None = None

        # Performance Stats
        self.frame_count: int = 0
        self.fps: float = 0.0
        self.last_time: float = time.time()

        # Internals for SAM2VideoPredictor
        self.sam2_state_initialized: bool = False
        self.current_frame_idx: int = 0
        self.auto_masks: list | None = None
        self.auto_colors: list = []

        self._lock = threading.Lock()

    def __enter__(self):
        self._lock.acquire()
        return self

    def __exit__(self, *args):
        self._lock.release()

    def add_object(self, obj_id: int, name: str, color: list):
        with self._lock:
            if obj_id not in self.objects:
                self.objects[obj_id] = {
                    "points": [],
                    "labels": [],
                    "mask": None,
                    "color": color,
                    "name": name
                }
                # If it's the only object, make it active
                if len(self.objects) == 1:
                    self.active_obj_id = obj_id

    def remove_object(self, obj_id: int):
        with self._lock:
            if obj_id in self.objects:
                del self.objects[obj_id]
                # If deleted the active one, pick another one
                if self.active_obj_id == obj_id:
                    if self.objects:
                        self.active_obj_id = next(iter(self.objects.keys()))
                    else:
                        self.active_obj_id = 1
                        self.objects[1] = {
                            "points": [],
                            "labels": [],
                            "mask": None,
                            "color": [0, 230, 100],
                            "name": "Objeto 1"
                        }
                self.sam2_state_initialized = False

    def select_object(self, obj_id: int):
        with self._lock:
            if obj_id in self.objects:
                self.active_obj_id = obj_id

    def add_point(self, x: int, y: int, label: int):
        with self._lock:
            obj = self.objects.get(self.active_obj_id)
            if obj is not None:
                obj["points"].append([x, y])
                obj["labels"].append(label)
                # Invalidate mask and trigger SAM2 update on the current frame
                obj["mask"] = None
                # We do NOT set self.sam2_state_initialized = False here.
                # Wiping the state on every click forces the video predictor to reset,
                # which discards the entire tracking history and conditioning frames.
                # Keeping it True allows SAM2 to perform multi-frame propagation and correction.

    def clear_points(self, obj_id: int | None = None):
        with self._lock:
            if obj_id is None:
                # Clear active object
                obj = self.objects.get(self.active_obj_id)
                if obj is not None:
                    obj["points"].clear()
                    obj["labels"].clear()
                    obj["mask"] = None
            elif obj_id in self.objects:
                self.objects[obj_id]["points"].clear()
                self.objects[obj_id]["labels"].clear()
                self.objects[obj_id]["mask"] = None
            self.sam2_state_initialized = False

    def clear_all_points(self):
        with self._lock:
            for obj in self.objects.values():
                obj["points"].clear()
                obj["labels"].clear()
                obj["mask"] = None
            self.sam2_state_initialized = False
            self.auto_masks = None

    def set_source(self, source: str):
        with self._lock:
            self.source = source
            self.source_changed = True
            self.clear_all_points()
            self.sam2_state_initialized = False
            self.current_frame_idx = 0

    def consume_source_changed(self) -> str | None:
        with self._lock:
            if self.source_changed:
                self.source_changed = False
                return self.source
            return None

    def update_fps(self):
        now = time.time()
        with self._lock:
            self.frame_count += 1
            if now - self.last_time >= 1.0:
                self.fps = self.frame_count / (now - self.last_time)
                self.frame_count = 0
                self.last_time = now

    def apply_config(self, data: dict):
        with self._lock:
            if "mode" in data and data["mode"] != self.mode:
                self.mode = data["mode"]
                if data["mode"] == "auto":
                    self.auto_masks = None
                # Reset SAM2 tracking state if switching mode to track
                if data["mode"] == "track":
                    self.sam2_state_initialized = False

            for k in ("opacity", "show_contour", "show_points", "render_mode", "blur_background", "blur_strength"):
                if k in data:
                    setattr(self, k, data[k])

            if "active_obj_id" in data:
                self.select_object(int(data["active_obj_id"]))

            if "clear_points" in data:
                self.clear_all_points()

            if "is_recording" in data:
                self.is_recording = bool(data["is_recording"])
