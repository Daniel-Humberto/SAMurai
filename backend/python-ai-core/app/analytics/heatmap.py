import numpy as np
import cv2
from typing import Optional

CANVAS_W = 364
CANVAS_H = 486

class HeatmapAccumulator:
    """Accumulates and normalizes team and ball spatial occupancy heatmaps."""
    def __init__(self):
        self.maps: dict[str, np.ndarray] = {
            "azul":   np.zeros((CANVAS_H, CANVAS_W), dtype=np.float32),
            "rojo":   np.zeros((CANVAS_H, CANVAS_W), dtype=np.float32),
            "balon":  np.zeros((CANVAS_H, CANVAS_W), dtype=np.float32),
        }
        self.frame_count = 0

    def _accumulate_gaussian(self, heatmap: np.ndarray, cx: float, cy: float, radius: int = 15):
        """Accumulates a 2D Gaussian blob representing a point coordinate."""
        h, w = heatmap.shape
        x0 = int(max(0, cx - radius))
        x1 = int(min(w, cx + radius + 1))
        y0 = int(max(0, cy - radius))
        y1 = int(min(h, cy + radius + 1))
        
        if x1 <= x0 or y1 <= y0:
            return
            
        sigma = radius / 3.0
        ys, xs = np.ogrid[y0 - cy : y1 - cy, x0 - cx : x1 - cx]
        gaussian = np.exp(-(xs**2 + ys**2) / (2 * sigma**2))
        heatmap[y0:y1, x0:x1] += gaussian.astype(np.float32)

    def update(self, projected: list[dict], masks_warped: Optional[dict] = None):
        """
        Para cada objeto proyectado:
        - Si masks_warped disponible: acumular máscara warped
        - Si no: acumular punto gaussiano (radio 15px) en posición canónica
        Incrementa frame_count.
        """
        for obj in projected:
            # Map team/class to valid map key
            team = obj.get("team")
            if team not in self.maps:
                cid = obj.get("class_id")
                if cid == 0:
                    team = "azul"
                elif cid == 1:
                    team = "rojo"
                else:
                    team = "balon"

            tid = obj.get("tracker_id", -1)
            cx, cy = obj.get("x_px", 0.0), obj.get("y_px", 0.0)

            if masks_warped is not None and tid in masks_warped:
                mask = masks_warped[tid]
                # Check shape matches
                if mask.shape == (CANVAS_H, CANVAS_W):
                    self.maps[team] += mask.astype(np.float32)
                else:
                    # Rescale mask or fallback
                    try:
                        mask_resized = cv2.resize(mask.astype(np.uint8), (CANVAS_W, CANVAS_H), interpolation=cv2.INTER_NEAREST)
                        self.maps[team] += mask_resized.astype(np.float32)
                    except Exception:
                        self._accumulate_gaussian(self.maps[team], cx, cy)
            else:
                self._accumulate_gaussian(self.maps[team], cx, cy)

        self.frame_count += 1

    def normalized(self, key: str) -> np.ndarray:
        """Retorna heatmap normalizado a [0,1]."""
        hmap = self.maps[key]
        max_val = np.max(hmap)
        if max_val > 0.0:
            return hmap / max_val
        return hmap.copy()

    def to_json(self) -> dict:
        """
        Serializa los 3 heatmaps como listas 2D para envío por WebSocket.
        Reducir resolución a la mitad (182x243) para reducir payload.
        """
        result = {}
        for key in self.maps.keys():
            norm_map = self.normalized(key)
            # Width = 182, Height = 243
            resized = cv2.resize(norm_map, (182, 243), interpolation=cv2.INTER_AREA)
            result[key] = resized.tolist()
        return result
