from ultralytics import YOLO
import supervision as sv
import numpy as np
import cv2

CLASS_MAP = {
    0: "robot",      # person class de YOLO base como proxy
    32: "balon",     # sports ball
}

class YoloDetector:
    """Detector class using YOLO for detecting robots and balls."""
    def __init__(self, model_name: str = "yolov8n.pt", conf: float = 0.35):
        self.model = YOLO(model_name)
        self.conf = conf

    def detect(self, frame_bgr: np.ndarray) -> sv.Detections:
        """
        Ejecuta YOLO sobre frame_bgr.
        Filtra solo clases relevantes (robots y balón).
        Retorna sv.Detections con class_id remapeado:
          0 → robot (puede ser azul o rojo, diferenciado por HSV en classify_teams)
          1 → balón
        """
        results = self.model(frame_bgr, conf=self.conf, verbose=False)[0]
        detections = sv.Detections.from_ultralytics(results)
        
        if detections.class_id is not None and len(detections.class_id) > 0:
            mask = np.isin(detections.class_id, [0, 32])
            detections = detections[mask]
            
            # Remap class ids: 0 -> 0 (robot), 32 -> 1 (balon)
            new_class_ids = np.array([0 if cid == 0 else 1 for cid in detections.class_id], dtype=np.int32)
            detections.class_id = new_class_ids
            
        return detections

    def classify_teams(
        self, frame_bgr: np.ndarray, detections: sv.Detections
    ) -> sv.Detections:
        """
        Para cada detección de robot (class_id==0), recorta la región del bbox,
        calcula el tono HSV dominante y reasigna class_id:
          0 → robot_azul  (H en [100, 125])
          1 → robot_rojo  (H en [0,10] o [170,179])
          2 → balón       (sin cambio)
        Retorna sv.Detections con class_id actualizado y
        data["team"] como array de strings.
        """
        if detections.class_id is None or len(detections.class_id) == 0:
            detections.data["team"] = np.array([], dtype=object)
            return detections

        new_class_ids = []
        team_names = []
        h, w, _ = frame_bgr.shape

        for i in range(len(detections)):
            class_id = detections.class_id[i]
            if class_id == 0:  # robot
                bbox = detections.xyxy[i]
                x1, y1, x2, y2 = map(int, bbox)
                x1 = max(0, min(x1, w - 1))
                y1 = max(0, min(y1, h - 1))
                x2 = max(0, min(x2, w - 1))
                y2 = max(0, min(y2, h - 1))

                if x2 > x1 and y2 > y1:
                    crop = frame_bgr[y1:y2, x1:x2]
                    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                    h_channel = hsv[:, :, 0]
                    s_channel = hsv[:, :, 1]
                    v_channel = hsv[:, :, 2]
                    
                    # Píxeles con color saturado (excluye negro/blanco/gris)
                    colored_mask = (s_channel > 60) & (v_channel > 40)
                    if np.any(colored_mask):
                        h_values = h_channel[colored_mask]
                        hist, _ = np.histogram(h_values, bins=180, range=(0, 180))
                        dominant_h = int(np.argmax(hist))
                        colored_ratio = np.sum(colored_mask) / colored_mask.size
                    else:
                        dominant_h = -1  # sin color dominante → robot negro
                        colored_ratio = 0.0
                else:
                    dominant_h = -1
                    colored_ratio = 0.0

                # Robots negros: poca saturación → identificar por marcas de color
                # Si menos del 10% del recorte tiene color saturado, es negro
                if dominant_h == -1 or colored_ratio < 0.10:
                    new_class_id = 0
                    team_name = "azul"   # equipo por defecto; sin marcas no podemos distinguir
                elif 100 <= dominant_h <= 125:
                    new_class_id = 0
                    team_name = "azul"
                elif (0 <= dominant_h <= 10) or (170 <= dominant_h <= 179):
                    new_class_id = 1
                    team_name = "rojo"
                elif 10 < dominant_h <= 30:  # naranja/amarillo → marca identificadora
                    new_class_id = 0
                    team_name = "azul"
                else:
                    dist_blue = abs(dominant_h - 112.5)
                    dist_red = min(abs(dominant_h - 0), abs(dominant_h - 180))
                    if dist_blue < dist_red:
                        new_class_id = 0
                        team_name = "azul"
                    else:
                        new_class_id = 1
                        team_name = "rojo"
            else:  # class_id == 1 is balón
                new_class_id = 2  # balon
                team_name = "balon"

            new_class_ids.append(new_class_id)
            team_names.append(team_name)

        detections.class_id = np.array(new_class_ids, dtype=np.int32)
        detections.data["team"] = np.array(team_names, dtype=object)
        return detections

    def detect_and_classify(self, frame_bgr: np.ndarray) -> sv.Detections:
        """Pipeline completo: detect → classify_teams"""
        detections = self.detect(frame_bgr)
        return self.classify_teams(frame_bgr, detections)
