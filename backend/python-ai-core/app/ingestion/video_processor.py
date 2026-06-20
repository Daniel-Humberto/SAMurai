from __future__ import annotations

from math import atan2, degrees, hypot
from pathlib import Path

import cv2

from app.analytics.metrics import MetricsEngine
from app.narrative.llm_adapter import LLMAdapter


class VideoProcessor:
    FIELD_WIDTH_CM = 900.0
    FIELD_HEIGHT_CM = 600.0

    def __init__(self):
        self.metrics = MetricsEngine()
        self.llm = LLMAdapter()

    def process(self, video_path: str | Path, progress_callback=None) -> dict:
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise RuntimeError(f"No se pudo abrir el video: {video_path}")

        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        stride = max(1, int(round(fps / 6)))

        telemetry = []
        trajectories = []
        events = []

        previous_gray = None
        previous_point = None
        previous_speed = 0.0
        previous_angle = None
        cooldowns: dict[str, int] = {}

        frame_idx = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            if frame_idx % stride != 0:
                frame_idx += 1
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (11, 11), 0)
            if previous_gray is None:
                previous_gray = gray
                frame_idx += 1
                continue

            delta = cv2.absdiff(previous_gray, gray)
            _, thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)
            thresh = cv2.dilate(thresh, None, iterations=2)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            previous_gray = gray

            dominant = None
            area = 0.0
            if contours:
                dominant = max(contours, key=cv2.contourArea)
                area = float(cv2.contourArea(dominant))

            if dominant is None or area < 60.0:
                frame_idx += 1
                continue

            moments = cv2.moments(dominant)
            if moments["m00"] == 0:
                frame_idx += 1
                continue

            cx = moments["m10"] / moments["m00"]
            cy = moments["m01"] / moments["m00"]
            x_cm = round((cx / max(width, 1)) * self.FIELD_WIDTH_CM, 2)
            y_cm = round((cy / max(height, 1)) * self.FIELD_HEIGHT_CM, 2)

            timestamp_s = round(frame_idx / fps, 3)
            speed = 0.0
            angle = None
            predicted_x = x_cm
            predicted_y = y_cm

            if previous_point is not None:
                dt = max(stride / fps, 1 / fps)
                dx = x_cm - previous_point[0]
                dy = y_cm - previous_point[1]
                speed = hypot(dx, dy) / dt
                angle = degrees(atan2(dy, dx))
                predicted_x = round(x_cm + dx, 2)
                predicted_y = round(y_cm + dy, 2)

                if speed > 180 and previous_speed <= 180 and cooldowns.get("pass", -999) + 8 < frame_idx:
                    events.append(self._build_event("pass", frame_idx, timestamp_s, speed, x_cm, y_cm))
                    cooldowns["pass"] = frame_idx
                if previous_angle is not None and angle is not None:
                    turn = abs(angle - previous_angle)
                    turn = min(turn, 360 - turn)
                    if turn > 95 and cooldowns.get("interception", -999) + 8 < frame_idx:
                        events.append(self._build_event("interception", frame_idx, timestamp_s, speed, x_cm, y_cm))
                        cooldowns["interception"] = frame_idx
                if area > 2000 and speed < 75 and cooldowns.get("collision", -999) + 10 < frame_idx:
                    events.append(self._build_event("collision", frame_idx, timestamp_s, speed, x_cm, y_cm))
                    cooldowns["collision"] = frame_idx
                if (x_cm < 35 or x_cm > self.FIELD_WIDTH_CM - 35) and speed > 150 and cooldowns.get("goal", -999) + 12 < frame_idx:
                    events.append(self._build_event("goal", frame_idx, timestamp_s, speed, x_cm, y_cm))
                    cooldowns["goal"] = frame_idx

            telemetry_point = {
                "frame_idx": frame_idx,
                "timestamp_s": timestamp_s,
                "x_cm": x_cm,
                "y_cm": y_cm,
                "speed_cm_s": round(speed, 2),
                "area_px": int(area),
            }
            telemetry.append(telemetry_point)
            trajectories.append(
                {
                    "session_id": None,
                    "frame_idx": frame_idx,
                    "object_id": 1,
                    "object_class": "motion_cluster",
                    "x_cm": x_cm,
                    "y_cm": y_cm,
                    "area_px": int(area),
                    "predicted_x_cm": predicted_x,
                    "predicted_y_cm": predicted_y,
                }
            )

            previous_point = (x_cm, y_cm)
            previous_speed = speed
            previous_angle = angle

            if progress_callback is not None and frame_count > 0 and len(telemetry) % 10 == 0:
                progress_callback(frame_idx, min(99.0, round((frame_idx / frame_count) * 100, 2)), telemetry)

            frame_idx += 1

        capture.release()

        for event in events:
            event["narration_text"] = self.llm.generate_narration(event, {"telemetry_count": len(telemetry)})

        stats = self.metrics.snapshot(telemetry)
        stats.update(
            {
                "mode": "video",
                "video_fps": round(fps, 2),
                "frame_count": frame_count,
                "processed_points": len(telemetry),
                "width": width,
                "height": height,
                "event_count": len(events),
                "duration_s": round(frame_count / fps, 2) if fps else 0.0,
            }
        )

        media_info = {
            "fps": round(fps, 2),
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "processed_stride": stride,
        }

        return {
            "telemetry": telemetry,
            "trajectories": trajectories,
            "events": events,
            "stats": stats,
            "media_info": media_info,
        }

    def _build_event(self, event_type: str, frame_idx: int, timestamp_s: float, speed: float, x_cm: float, y_cm: float) -> dict:
        return {
            "frame_idx": frame_idx,
            "timestamp_s": timestamp_s,
            "event_type": event_type,
            "metadata": {
                "speed_cm_s": round(speed, 2),
                "x_cm": x_cm,
                "y_cm": y_cm,
            },
            "narration_text": None,
        }
