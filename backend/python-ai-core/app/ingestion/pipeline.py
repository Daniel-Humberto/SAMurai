import cv2
import numpy as np
import supervision as sv
from typing import Optional, Callable

from app.vision.detector import YoloDetector
from app.vision.tracker import ObjectTracker
from app.vision.segmenter import SAMSegmenter
from app.vision.homography import HomographyEngine
from app.analytics.metrics import MetricsEngine
from app.analytics.events import EventDetector
from app.analytics.heatmap import HeatmapAccumulator
from app.analytics.voronoi import VoronoiEngine
from app.forecast.trajectory import TrajectoryForecaster
from app.core.state import SessionState

class PipelineOrchestrator:
    """Orchestrates the entire computer vision and analytics pipeline for a session."""
    def __init__(self, session_id: str, fps: float = 30.0, sam_skip: int = 4):
        """
        sam_skip: ejecutar SAM cada N frames (default 4).
        Entre frames SAM, usar solo YOLO+ByteTrack para mantener FPS.
        """
        self.session_id = session_id
        self.fps = fps
        self.sam_skip = sam_skip
        self.frame_idx = 0

        from app.config import get_settings
        _cfg = get_settings()

        self.detector = YoloDetector(model_name=_cfg.yolo_model)
        self.tracker = ObjectTracker()
        self.segmenter = SAMSegmenter(size=_cfg.sam_model_size)
        self.homography = HomographyEngine()
        self.metrics = MetricsEngine(fps=fps)
        self.event_detector = EventDetector(fps=fps)
        self.heatmap = HeatmapAccumulator()
        self.voronoi = VoronoiEngine()
        self.forecaster = TrajectoryForecaster(fps=fps)

    def set_homography(self, src_points: np.ndarray):
        """Calibrar homografía con 4 puntos de esquina."""
        self.homography.calibrate(src_points)

    def process_frame(self, frame_bgr: np.ndarray) -> dict:
        """
        Pipeline completo por frame:

        1. detect_and_classify(frame) → detections
        2. tracker.update(detections) → detections con tracker_id
        3. if frame_idx % sam_skip == 0 and homography.calibrated:
               segmenter.segment(frame, detections) → detections con masks
        4. if homography.calibrated:
               projected = homography.project_detections(detections)
               for obj in projected: 
                   if obj["tracker_id"] >= 0:
                       forecaster.update(obj["tracker_id"], obj["x_cm"], obj["y_cm"])
               metrics_frame = metrics.compute(projected, frame_idx)
               events = event_detector.detect(projected, frame_idx, metrics_frame.possession)
               
               # Warp masks if SAM generated masks
               masks_warped = None
               if detections.mask is not None:
                   masks_warped = {}
                   for i in range(len(detections)):
                       tid = int(detections.tracker_id[i]) if detections.tracker_id is not None else -1
                       if tid >= 0:
                           masks_warped[tid] = self.homography.warp_mask(detections.mask[i])

               heatmap.update(projected, masks_warped=masks_warped)
               voronoi_data = voronoi.compute(projected)
               predictions = forecaster.all_predictions()
               heatmap_update = True
           else:
               projected = []
               events = []
               metrics_frame = None
               voronoi_data = {}
               predictions = {}
               heatmap_update = False

        5. Construir y retornar FrameResult dict (ver abajo)
        6. Incrementar frame_idx
        """
        # 1. detect_and_classify
        detections = self.detector.detect_and_classify(frame_bgr)

        # 2. tracker update
        detections = self.tracker.update(detections)

        # 3. segmenter
        if self.frame_idx % self.sam_skip == 0 and self.homography.calibrated:
            detections = self.segmenter.segment(frame_bgr, detections)

        # 4. analytics & forecast
        if self.homography.calibrated:
            projected = self.homography.project_detections(detections)
            for obj in projected:
                tid = obj["tracker_id"]
                if tid >= 0:
                    self.forecaster.update(tid, obj["x_cm"], obj["y_cm"])
            
            metrics_frame = self.metrics.compute(projected, self.frame_idx)
            events = self.event_detector.detect(projected, self.frame_idx, metrics_frame.possession)
            
            # Warp masks
            masks_warped = None
            if detections.mask is not None:
                masks_warped = {}
                for i in range(len(detections)):
                    tid = int(detections.tracker_id[i]) if detections.tracker_id is not None else -1
                    if tid >= 0:
                        masks_warped[tid] = self.homography.warp_mask(detections.mask[i])
            
            self.heatmap.update(projected, masks_warped=masks_warped)
            voronoi_data = self.voronoi.compute(projected)
            predictions = self.forecaster.all_predictions()
            heatmap_update = True
        else:
            projected = []
            events = []
            metrics_frame = None
            voronoi_data = {}
            predictions = {}
            heatmap_update = False

        # Serialize events
        serialized_events = []
        for ev in events:
            serialized_events.append({
                "event_type": ev.event_type,
                "frame_idx": ev.frame_idx,
                "timestamp_s": ev.timestamp_s,
                "objects_involved": ev.objects_involved,
                "position_cm": ev.position_cm,
                "metadata": ev.metadata
            })

        # Serialize metrics
        serialized_metrics = {}
        if metrics_frame is not None:
            serialized_metrics = {
                "frame_idx": metrics_frame.frame_idx,
                "possession": metrics_frame.possession,
                "distances": metrics_frame.distances,
                "speeds": metrics_frame.speeds,
                "zone_control": metrics_frame.zone_control
            }

        # 5. Build FrameResult dict
        result = {
            "frame_idx": self.frame_idx,
            "detections_count": len(detections),
            "projected": projected,
            "events": serialized_events,
            "metrics": serialized_metrics,
            "voronoi": voronoi_data,
            "predictions": predictions,
            "heatmap_update": heatmap_update,
            "calibrated": self.homography.calibrated
        }

        # 6. Increment frame index
        self.frame_idx += 1

        return result

    def get_heatmap_snapshot(self) -> dict:
        """Retorna heatmap.to_json() para envío periódico al frontend."""
        return self.heatmap.to_json()

    def get_session_summary(self) -> dict:
        """
        {
          "total_frames": int,
          "fps_actual": float,
          "possession": self.metrics.cumulative_possession(),
          "total_events": int,
          "events_by_type": dict,
          "heatmaps": heatmap.to_json(),
        }
        """
        events_by_type = {}
        for ev in self.event_detector._detected_events:
            events_by_type[ev.event_type] = events_by_type.get(ev.event_type, 0) + 1

        return {
            "total_frames": self.frame_idx,
            "fps_actual": self.fps,
            "possession": self.metrics.cumulative_possession(),
            "total_events": len(self.event_detector._detected_events),
            "events_by_type": events_by_type,
            "heatmaps": self.heatmap.to_json(),
        }


class VisionPipeline:
    """Legacy/compatibility pipeline class representing vision processing stages."""
    def describe(self) -> dict:
        return {
            "stages": [
                {"component": "detector", "task": "bbox detection"},
                {"component": "tracker", "task": "ByteTrack tracking"},
                {"component": "segmenter", "task": "SAM segmentation"},
                {"component": "homography", "task": "field projection"},
            ]
        }
