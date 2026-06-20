from dataclasses import dataclass, field
from collections import defaultdict
from typing import Optional
import numpy as np

@dataclass
class FrameMetrics:
    """Dataclass holding performance metrics for a single video frame."""
    frame_idx: int
    possession: dict          # {tracker_id: bool, "team": "azul"|"rojo"|"ninguno"}
    distances: dict           # {tracker_id: float} distancia al balón en cm
    speeds: dict              # {tracker_id: float} cm/s estimada
    zone_control: dict        # {"azul": float, "rojo": float} % campo canónico

class MetricsEngine:
    """Engine for computing and accumulating real-time game analytics and metrics."""
    def __init__(self, fps: float = 30.0):
        self.fps = fps
        self._prev_positions: dict = {}
        self._possession_history: list = []

    def compute(
        self,
        projected: list[dict],   # output de homography.project_detections()
        frame_idx: int
    ) -> FrameMetrics:
        """
        Calcula para el frame actual:
        1. possession: robot más cercano al balón (< 15cm) tiene posesión.
           Si ninguno, possession["team"] = "ninguno".
        2. distances: distancia euclidiana de cada robot al balón en cm reales.
        3. speeds: delta posición entre frame actual y anterior × fps.
        4. zone_control: % de campo en la mitad de cada equipo
           (mitad superior = equipo rojo, inferior = azul, por convención).
        Actualiza _prev_positions y _possession_history.
        """
        # Find the ball (class_id == 2)
        ball = None
        for obj in projected:
            if obj["class_id"] == 2:
                ball = obj
                break

        # Separate robots
        robots = [obj for obj in projected if obj["class_id"] in (0, 1)]

        # 1. possession & 2. distances
        possession = {}
        distances = {}
        possessor_id = -1
        min_dist = float('inf')

        # Initialize all robots to False for possession
        for r in robots:
            tid = r["tracker_id"]
            if tid >= 0:
                possession[tid] = False

        if ball is not None:
            ball_x, ball_y = ball["x_cm"], ball["y_cm"]
            for r in robots:
                tid = r["tracker_id"]
                if tid < 0:
                    continue
                dist = float(np.hypot(r["x_cm"] - ball_x, r["y_cm"] - ball_y))
                distances[tid] = dist
                if dist < min_dist:
                    min_dist = dist
                    possessor_id = tid

            if min_dist < 15.0 and possessor_id >= 0:
                possession[possessor_id] = True
                # Find team of possessor
                possessor_team = "ninguno"
                for r in robots:
                    if r["tracker_id"] == possessor_id:
                        possessor_team = r["team"]
                        break
                possession["team"] = possessor_team
            else:
                possession["team"] = "ninguno"
        else:
            possession["team"] = "ninguno"

        self._possession_history.append(possession["team"])

        # 3. speeds
        speeds = {}
        for obj in projected:
            tid = obj["tracker_id"]
            if tid < 0:
                continue
            curr_pos = (obj["x_cm"], obj["y_cm"])
            if tid in self._prev_positions:
                prev_pos = self._prev_positions[tid]
                dist = float(np.hypot(curr_pos[0] - prev_pos[0], curr_pos[1] - prev_pos[1]))
                speeds[tid] = dist * self.fps
            else:
                speeds[tid] = 0.0

        # Update prev positions
        new_prev_positions = {}
        for obj in projected:
            tid = obj["tracker_id"]
            if tid >= 0:
                new_prev_positions[tid] = (obj["x_cm"], obj["y_cm"])
        self._prev_positions = new_prev_positions

        # 4. zone_control
        # Mitad superior = equipo rojo (Y < 121.5), inferior = azul (Y >= 121.5)
        num_superior = sum(1 for r in robots if r["y_cm"] < 121.5)
        num_inferior = sum(1 for r in robots if r["y_cm"] >= 121.5)
        total_robots = num_superior + num_inferior

        if total_robots > 0:
            rojo_pct = (num_superior / total_robots) * 100.0
            azul_pct = (num_inferior / total_robots) * 100.0
        else:
            rojo_pct = 50.0
            azul_pct = 50.0

        zone_control = {
            "azul": azul_pct,
            "rojo": rojo_pct
        }

        return FrameMetrics(
            frame_idx=frame_idx,
            possession=possession,
            distances=distances,
            speeds=speeds,
            zone_control=zone_control
        )

    def compute_snapshot(self, telemetry: list[dict] | None) -> dict:
        telemetry = telemetry or []
        if not telemetry:
            return self.bootstrap_metrics()

        speeds = [float(point.get("speed_cm_s", 0.0) or 0.0) for point in telemetry]
        areas  = [float(point.get("area_px",    0.0) or 0.0) for point in telemetry]
        xs     = [float(point.get("x_cm",       0.0) or 0.0) for point in telemetry]
        ys     = [float(point.get("y_cm",       0.0) or 0.0) for point in telemetry]

        # Posesión real derivada del historial acumulado
        poss = self.cumulative_possession()

        return {
            "processed_points": len(telemetry),
            "avg_speed_cm_s":   round(sum(speeds) / len(speeds), 2),
            "max_speed_cm_s":   round(max(speeds), 2),
            "avg_area_px":      round(sum(areas) / len(areas), 2),
            "last_x_cm":        round(xs[-1], 2),
            "last_y_cm":        round(ys[-1], 2),
            "min_x_cm":         round(min(xs), 2),
            "max_x_cm":         round(max(xs), 2),
            "min_y_cm":         round(min(ys), 2),
            "max_y_cm":         round(max(ys), 2),
            "possession_blue":    round(poss["azul"],   2),
            "possession_red":     round(poss["rojo"],   2),
            "possession_neutral": round(poss["ninguno"], 2),
        }

    def bootstrap_metrics(self) -> dict:
        return {
            "processed_points": 0,
            "avg_speed_cm_s": 0.0,
            "max_speed_cm_s": 0.0,
            "avg_area_px": 0.0,
            "last_x_cm": 0.0,
            "last_y_cm": 0.0,
            "min_x_cm": 0.0,
            "max_x_cm": 0.0,
            "min_y_cm": 0.0,
            "max_y_cm": 0.0,
            "possession_blue": 0.0,
            "possession_red": 0.0,
            "possession_neutral": 100.0,
        }

    def cumulative_possession(self) -> dict:
        """
        Retorna {"azul": float, "rojo": float, "ninguno": float}
        como % del total de frames procesados.
        """
        if not self._possession_history:
            return {"azul": 0.0, "rojo": 0.0, "ninguno": 100.0}
        
        total = len(self._possession_history)
        azul_count = self._possession_history.count("azul")
        rojo_count = self._possession_history.count("rojo")
        ninguno_count = self._possession_history.count("ninguno")

        return {
            "azul": (azul_count / total) * 100.0,
            "rojo": (rojo_count / total) * 100.0,
            "ninguno": (ninguno_count / total) * 100.0
        }
