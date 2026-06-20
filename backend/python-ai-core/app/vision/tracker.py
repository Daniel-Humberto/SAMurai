import supervision as sv

class ObjectTracker:
    """Tracker adapter using ByteTrack for tracking robots and balls."""
    def __init__(self):
        self.tracker = sv.ByteTrack()

    def update(self, detections: sv.Detections) -> sv.Detections:
        """
        Actualiza ByteTrack con las detecciones del frame actual.
        Retorna sv.Detections con tracker_id poblado.
        Si len(detections) == 0, retorna detections sin modificar.
        """
        if len(detections) == 0:
            return detections
        return self.tracker.update_with_detections(detections)
