import sys
import traceback
import numpy as np
import torch
import cv2

sys.path.insert(0, "/app/sam2")

from sam2.build_sam import build_sam2_video_predictor, build_sam2
from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator

from app.config import CKPT, CFG, DEVICE

if DEVICE == "cuda":
    DTYPE = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
else:
    DTYPE = torch.float32


def to_numpy(x):
    if x is None:
        return None
    if hasattr(x, "cpu"):
        return x.cpu().numpy()
    return np.asarray(x)


class Segmenter:
    def __init__(self):
        print(f"[SAM2] Cargando Video Predictor (device: {DEVICE}, dtype: {DTYPE})...")
        # Build the official SAM 2 Video Predictor
        self._video_predictor = build_sam2_video_predictor(CFG, CKPT, device=DEVICE)
        self._auto_gen: SAM2AutomaticMaskGenerator | None = None
        self._last_error: str | None = None
        print("[SAM2] Video Predictor cargado")

    def pop_error(self) -> str | None:
        e = self._last_error
        self._last_error = None
        return e

    def preprocess_frame(self, frame_rgb: np.ndarray) -> torch.Tensor:
        img_mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        img_std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)

        # SAM2 expects size 1024x1024
        img_resized = cv2.resize(frame_rgb, (1024, 1024))
        # Keep tensor on CPU to reduce GPU VRAM usage and comply with offload_video_to_cpu=True
        img_tensor = torch.from_numpy(img_resized).permute(2, 0, 1).to(dtype=torch.float32) / 255.0
        img_tensor = (img_tensor - img_mean) / img_std
        return img_tensor

    def init_in_memory_state(self, first_frame_rgb: np.ndarray) -> dict:
        import os
        # Ensure dummy folder exists in RAM disk
        os.makedirs("/dev/shm/sam2_live", exist_ok=True)
        dummy_img_path = "/dev/shm/sam2_live/00000.jpg"
        if not os.path.exists(dummy_img_path):
            cv2.imwrite(dummy_img_path, np.zeros((10, 10, 3), dtype=np.uint8))

        with torch.inference_mode(), torch.autocast(DEVICE, dtype=DTYPE):
            # offload_video_to_cpu=True keeps GPU VRAM consumption extremely low
            inference_state = self._video_predictor.init_state(
                video_path="/dev/shm/sam2_live",
                offload_video_to_cpu=True,
                offload_state_to_cpu=False
            )

        h, w = first_frame_rgb.shape[:2]
        img_tensor = self.preprocess_frame(first_frame_rgb)
        inference_state["images"] = [img_tensor]
        inference_state["num_frames"] = 1
        inference_state["video_height"] = h
        inference_state["video_width"] = w

        # Run encoder on the first frame
        with torch.inference_mode(), torch.autocast(DEVICE, dtype=DTYPE):
            self._video_predictor._get_image_feature(inference_state, frame_idx=0, batch_size=1)

        return inference_state

    def add_frame(self, inference_state: dict, frame_rgb: np.ndarray) -> int:
        img_tensor = self.preprocess_frame(frame_rgb)
        inference_state["images"].append(img_tensor)
        inference_state["num_frames"] = len(inference_state["images"])
        frame_idx = inference_state["num_frames"] - 1

        # Run image encoder on the new frame
        with torch.inference_mode(), torch.autocast(DEVICE, dtype=DTYPE):
            self._video_predictor._get_image_feature(inference_state, frame_idx=frame_idx, batch_size=1)

        # Prune state to keep only the last 15 frames
        self.prune_state(inference_state, frame_idx, keep_window=15)

        return frame_idx

    def prune_state(self, inference_state: dict, current_frame_idx: int, keep_window: int = 15):
        if current_frame_idx < keep_window:
            return

        limit = current_frame_idx - keep_window

        # Identify all conditioning frames (those containing user clicks/prompts) to avoid pruning them
        cond_frame_indices = set()
        for key in ["point_inputs_per_obj", "mask_inputs_per_obj"]:
            if key in inference_state:
                for obj_idx in inference_state[key].keys():
                    for f_idx in inference_state[key][obj_idx].keys():
                        cond_frame_indices.add(f_idx)

        # 1. Prune images list (set old non-conditioning frames to None to free CPU/GPU RAM)
        for i in range(min(limit, len(inference_state["images"]))):
            if i not in cond_frame_indices:
                inference_state["images"][i] = None

        # 2. Prune cached features
        if "cached_features" in inference_state:
            keys_to_del = [k for k in inference_state["cached_features"].keys() if k < limit and k not in cond_frame_indices]
            for k in keys_to_del:
                del inference_state["cached_features"][k]

        # 3. Prune output_dict
        if "output_dict" in inference_state:
            for key in ["cond_frame_outputs", "non_cond_frame_outputs"]:
                if key in inference_state["output_dict"]:
                    keys_to_del = [k for k in inference_state["output_dict"][key].keys() if k < limit and k not in cond_frame_indices]
                    for k in keys_to_del:
                        del inference_state["output_dict"][key][k]

        # 4. Prune output_dict_per_obj
        if "output_dict_per_obj" in inference_state:
            for obj_idx in inference_state["output_dict_per_obj"].keys():
                for key in ["cond_frame_outputs", "non_cond_frame_outputs"]:
                    if key in inference_state["output_dict_per_obj"][obj_idx]:
                        keys_to_del = [k for k in inference_state["output_dict_per_obj"][obj_idx][key].keys() if k < limit and k not in cond_frame_indices]
                        for k in keys_to_del:
                            del inference_state["output_dict_per_obj"][obj_idx][key][k]

        # 5. Prune temp_output_dict_per_obj
        if "temp_output_dict_per_obj" in inference_state:
            for obj_idx in inference_state["temp_output_dict_per_obj"].keys():
                for key in ["cond_frame_outputs", "non_cond_frame_outputs"]:
                    if key in inference_state["temp_output_dict_per_obj"][obj_idx]:
                        keys_to_del = [k for k in inference_state["temp_output_dict_per_obj"][obj_idx][key].keys() if k < limit and k not in cond_frame_indices]
                        for k in keys_to_del:
                            del inference_state["temp_output_dict_per_obj"][obj_idx][key][k]

        # 6. Prune frames_already_tracked
        if "frames_already_tracked" in inference_state:
            keys_to_del = [k for k in inference_state["frames_already_tracked"].keys() if k < limit and k not in cond_frame_indices]
            for k in keys_to_del:
                del inference_state["frames_already_tracked"][k]

    def add_clicks(self, inference_state: dict, frame_idx: int, obj_id: int, pts: list, labels: list) -> dict:
        if not pts:
            return {}

        pts_np = np.array(pts, dtype=np.float32)
        lbls_np = np.array(labels, dtype=np.int32)

        try:
            with torch.inference_mode(), torch.autocast(DEVICE, dtype=DTYPE):
                _, obj_ids, mask_logits = self._video_predictor.add_new_points_or_box(
                    inference_state=inference_state,
                    frame_idx=frame_idx,
                    obj_id=obj_id,
                    points=pts_np,
                    labels=lbls_np
                )

            masks = {}
            for i, oid in enumerate(obj_ids):
                mask_bool = (mask_logits[i, 0] > 0.0).cpu().numpy()
                masks[oid] = mask_bool
            return masks
        except Exception as e:
            self._last_error = f"Error al añadir clics: {e}"
            traceback.print_exc()
            return {}

    def track_step(self, inference_state: dict, current_frame_idx: int) -> dict:
        if current_frame_idx <= 0:
            return {}

        try:
            with torch.inference_mode(), torch.autocast(DEVICE, dtype=DTYPE):
                # Start propagation at current frame and only track 1 frame.
                # Since the previous frames were already processed, their features and masks
                # are already encoded in the memory bank (non_cond_frame_outputs).
                # This cuts GPU/CPU redundant workload in half.
                generator = self._video_predictor.propagate_in_video(
                    inference_state,
                    start_frame_idx=current_frame_idx,
                    max_frame_num_to_track=1,
                    reverse=False
                )

                res = {}
                for frame_idx, obj_ids, mask_logits in generator:
                    if frame_idx == current_frame_idx:
                        for i, oid in enumerate(obj_ids):
                            mask_bool = (mask_logits[i, 0] > 0.0).cpu().numpy()
                            res[oid] = mask_bool
                return res
        except Exception as e:
            self._last_error = f"Error en propagación: {e}"
            traceback.print_exc()
            return {}

    def reset_predictor_state(self, inference_state: dict):
        try:
            with torch.inference_mode():
                self._video_predictor.reset_state(inference_state)
        except Exception as e:
            print(f"Error reseteando predictor: {e}")

    def predict_auto(self, frame_rgb: np.ndarray) -> list[dict]:
        try:
            if self._auto_gen is None:
                print("[SAM2] Cargando modelo base para Auto Gen...")
                base_model = build_sam2(CFG, CKPT, device=DEVICE)
                self._auto_gen = SAM2AutomaticMaskGenerator(
                    model=base_model,
                    points_per_side=16,  # 16 instead of 32 for speedup
                    points_per_batch=64, # batching for optimal GPU performance
                    pred_iou_thresh=0.7,
                    stability_score_thresh=0.8,
                    box_nms_thresh=0.7,
                )
            masks_data = self._auto_gen.generate(frame_rgb)
            for md in masks_data:
                md["segmentation"] = to_numpy(md["segmentation"]).astype(bool)
            return masks_data
        except Exception as e:
            msg = f"[SAM2 auto error] {e}"
            print(msg)
            traceback.print_exc()
            self._last_error = str(e)
            return []
