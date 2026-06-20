import cv2
import numpy as np
import supervision as sv
from typing import Optional, Tuple

# Dimensiones canónicas campo RCJ Soccer (en cm)
FIELD_W_CM = 182.0
FIELD_H_CM = 243.0

# Canvas en píxeles (2px por cm)
CANVAS_W = 364
CANVAS_H = 486
SCALE_PX_PER_CM = 2.0

class HomographyEngine:
    """Engine to compute and apply homography transformations for field projection."""
    def __init__(self):
        self.H: Optional[np.ndarray] = None
        self.H_inv: Optional[np.ndarray] = None
        self.calibrated: bool = False

    def calibrate(self, src_points: np.ndarray) -> np.ndarray:
        """
        src_points: np.float32 shape (4,2) — esquinas del campo en imagen de cámara
        Orden: TL, TR, BR, BL
        Calcula H con getPerspectiveTransform hacia campo canónico CANVAS_W x CANVAS_H.
        Almacena H y H_inv.
        Retorna H.
        """
        src_pts = np.array(src_points, dtype=np.float32)
        dst_pts = np.array([
            [0.0, 0.0],
            [CANVAS_W, 0.0],
            [CANVAS_W, CANVAS_H],
            [0.0, CANVAS_H]
        ], dtype=np.float32)
        
        self.H = cv2.getPerspectiveTransform(src_pts, dst_pts)
        self.H_inv = np.linalg.inv(self.H)
        self.calibrated = True
        return self.H

    def project_point(self, pt_cam: Tuple[float, float]) -> Tuple[float, float]:
        """
        Proyecta un punto (x, y) en coords de cámara al campo canónico (px).
        Usa perspectiveTransform.
        Retorna (x_canon, y_canon) en píxeles del canvas.
        Lanza ValueError si no está calibrado.
        """
        if not self.calibrated or self.H is None:
            raise ValueError("Homography engine is not calibrated.")
        
        pts = np.array([[[pt_cam[0], pt_cam[1]]]], dtype=np.float32)
        projected = cv2.perspectiveTransform(pts, self.H)
        x_canon, y_canon = projected[0, 0]
        return (float(x_canon), float(y_canon))

    def project_to_cm(self, pt_cam: Tuple[float, float]) -> Tuple[float, float]:
        """
        Proyecta punto de cámara a coordenadas en centímetros reales.
        Retorna (x_cm, y_cm).
        """
        x_canon, y_canon = self.project_point(pt_cam)
        return (x_canon / SCALE_PX_PER_CM, y_canon / SCALE_PX_PER_CM)

    def project_detections(self, detections: sv.Detections) -> list[dict]:
        """
        Para cada detección:
          - robots: usa BOTTOM_CENTER del bbox
          - balón (class_id==2): usa centro geométrico
        Retorna lista de dicts:
          {
            tracker_id, class_id, team,
            x_px, y_px,          # canónico en píxeles
            x_cm, y_cm,          # en cm reales
            area_px              # área de máscara si existe, sino -1
          }
        """
        if not self.calibrated or self.H is None:
            raise ValueError("Homography engine is not calibrated.")

        results = []
        for i in range(len(detections)):
            bbox = detections.xyxy[i]
            class_id = int(detections.class_id[i]) if detections.class_id is not None else 0
            tracker_id = int(detections.tracker_id[i]) if detections.tracker_id is not None else -1
            
            # Extract team if present
            if detections.data is not None and "team" in detections.data and i < len(detections.data["team"]):
                team = detections.data["team"][i]
            else:
                if class_id == 0:
                    team = "azul"
                elif class_id == 1:
                    team = "rojo"
                else:
                    team = "balon"

            x1, y1, x2, y2 = bbox
            if class_id == 2:  # balón: centro geométrico
                x_cam = (x1 + x2) / 2.0
                y_cam = (y1 + y2) / 2.0
            else:  # robots: bottom-center
                x_cam = (x1 + x2) / 2.0
                y_cam = y2

            x_px, y_px = self.project_point((x_cam, y_cam))
            x_cm, y_cm = x_px / SCALE_PX_PER_CM, y_px / SCALE_PX_PER_CM

            area_px = -1
            if detections.mask is not None:
                area_px = int(np.sum(detections.mask[i]))

            results.append({
                "tracker_id": tracker_id,
                "class_id": class_id,
                "team": team,
                "x_px": x_px,
                "y_px": y_px,
                "x_cm": x_cm,
                "y_cm": y_cm,
                "area_px": area_px
            })

        return results

    def warp_frame(self, frame_bgr: np.ndarray) -> np.ndarray:
        """
        Aplica warpPerspective al frame completo.
        Retorna vista cenital CANVAS_W x CANVAS_H BGR.
        """
        if not self.calibrated or self.H is None:
            raise ValueError("Homography engine is not calibrated.")
        return cv2.warpPerspective(frame_bgr, self.H, (CANVAS_W, CANVAS_H))

    def warp_mask(self, mask: np.ndarray) -> np.ndarray:
        """
        Aplica warpPerspective a una máscara booleana.
        Retorna máscara warped uint8.
        """
        if not self.calibrated or self.H is None:
            raise ValueError("Homography engine is not calibrated.")
        mask_uint8 = mask.astype(np.uint8) * 255
        warped = cv2.warpPerspective(mask_uint8, self.H, (CANVAS_W, CANVAS_H), flags=cv2.INTER_NEAREST)
        return warped

    def serialize(self) -> Optional[list]:
        """Serializa H a lista anidada para JSON/PostgreSQL."""
        if self.H is None:
            return None
        return self.H.tolist()

    @classmethod
    def from_serialized(cls, data: list) -> "HomographyEngine":
        """Reconstruye HomographyEngine desde lista serializada."""
        engine = cls()
        if data is not None:
            engine.H = np.array(data, dtype=np.float32)
            engine.H_inv = np.linalg.inv(engine.H)
            engine.calibrated = True
        return engine
