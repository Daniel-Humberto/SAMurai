from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class GameEvent:
    """Dataclass representing a game event (e.g. goal, pass, collision)."""
    event_type: str    # "pass" | "interception" | "collision" | "goal" | "possession_change"
    frame_idx: int
    timestamp_s: float
    objects_involved: list[int]   # tracker_ids
    position_cm: Optional[tuple]  # (x, y) en cm
    metadata: dict

class EventDetector:
    """Engine to detect high-level game events based on object position heuristics."""
    COLLISION_DIST_CM    = 12.0
    PASS_DIST_CM         = 25.0
    INTERCEPTION_DIST_CM = 18.0   # robot rival corta el pase dentro de este radio
    GOAL_ZONE_Y_CM       = 20.0   # últimos 20 cm = zona de portería

    def __init__(self, fps: float = 30.0):
        self.fps = fps
        self._prev_possession: Optional[int] = None
        self._prev_ball_pos: Optional[tuple] = None
        self._prev_possessor_team: Optional[str] = None
        self._detected_events: list[GameEvent] = []

    def is_on_cooldown(self, event_type: str, frame_idx: int) -> bool:
        """Checks if an event of the same type occurred within the last 15 frames."""
        for ev in reversed(self._detected_events):
            if ev.event_type == event_type:
                if frame_idx - ev.frame_idx < 15:
                    return True
                break
        return False

    def detect(
        self,
        projected: list[dict],
        frame_idx: int,
        current_possession: dict
    ) -> list[GameEvent]:
        """
        Heurísticas por frame:

        COLLISION: dos robots con dist_between < COLLISION_DIST_CM
        PASS: balón se aleja del robot poseedor >PASS_DIST_CM en un frame
        POSSESSION_CHANGE: tracker_id poseedor cambia entre frames consecutivos
        GOAL: balón entra en GOAL_ZONE_Y_CM (y_cm < GOAL_ZONE_Y_CM o
              y_cm > FIELD_H_CM - GOAL_ZONE_Y_CM)

        Retorna lista de GameEvent detectados en este frame.
        Evita duplicar eventos: un mismo evento no se reporta en frames
        consecutivos (cooldown de 15 frames por tipo de evento).
        """
        events_this_frame = []
        
        # Extract ball and robots
        ball = None
        for obj in projected:
            if obj["class_id"] == 2:
                ball = obj
                break
        robots = [obj for obj in projected if obj["class_id"] in (0, 1)]

        # Get current possessor
        curr_possessor_id = None
        for k, v in current_possession.items():
            if k != "team" and v is True:
                curr_possessor_id = k
                break

        # Equipo del poseedor actual
        curr_team = None
        for r in robots:
            if r["tracker_id"] == curr_possessor_id:
                curr_team = r.get("team")
                break

        # 1. POSSESSION_CHANGE
        if (self._prev_possession is not None and
                curr_possessor_id is not None and
                curr_possessor_id != self._prev_possession):
            if not self.is_on_cooldown("possession_change", frame_idx):
                ev = GameEvent(
                    event_type="possession_change",
                    frame_idx=frame_idx,
                    timestamp_s=frame_idx / self.fps,
                    objects_involved=[self._prev_possession, curr_possessor_id],
                    position_cm=None,
                    metadata={
                        "prev_possessor": self._prev_possession,
                        "new_possessor":  curr_possessor_id,
                        "team":           curr_team,
                    },
                )
                events_this_frame.append(ev)

                # 1b. INTERCEPTION — cambio de posesión entre equipos rivales
                if (self._prev_possessor_team and curr_team and
                        self._prev_possessor_team != curr_team and
                        not self.is_on_cooldown("interception", frame_idx)):
                    curr_robot = next((r for r in robots if r["tracker_id"] == curr_possessor_id), None)
                    pos = (curr_robot["x_cm"], curr_robot["y_cm"]) if curr_robot else None
                    ev_int = GameEvent(
                        event_type="interception",
                        frame_idx=frame_idx,
                        timestamp_s=frame_idx / self.fps,
                        objects_involved=[self._prev_possession, curr_possessor_id],
                        position_cm=pos,
                        metadata={
                            "interceptor_id":   curr_possessor_id,
                            "interceptor_team": curr_team,
                            "prev_team":        self._prev_possessor_team,
                        },
                    )
                    events_this_frame.append(ev_int)

        # 2. PASS
        if ball is not None and self._prev_possession is not None:
            # Find the previous possessor in the current frame
            prev_robot = None
            for r in robots:
                if r["tracker_id"] == self._prev_possession:
                    prev_robot = r
                    break
            if prev_robot is not None:
                dist = float(np.hypot(prev_robot["x_cm"] - ball["x_cm"], prev_robot["y_cm"] - ball["y_cm"]))
                if dist > self.PASS_DIST_CM:
                    if not self.is_on_cooldown("pass", frame_idx):
                        ev = GameEvent(
                            event_type="pass",
                            frame_idx=frame_idx,
                            timestamp_s=frame_idx / self.fps,
                            objects_involved=[self._prev_possession],
                            position_cm=(ball["x_cm"], ball["y_cm"]),
                            metadata={"distance_cm": dist}
                        )
                        events_this_frame.append(ev)

        # 3. COLLISION
        for i in range(len(robots)):
            for j in range(i + 1, len(robots)):
                r1, r2 = robots[i], robots[j]
                if r1["tracker_id"] < 0 or r2["tracker_id"] < 0:
                    continue
                dist = float(np.hypot(r1["x_cm"] - r2["x_cm"], r1["y_cm"] - r2["y_cm"]))
                if dist < self.COLLISION_DIST_CM:
                    if not self.is_on_cooldown("collision", frame_idx):
                        ev = GameEvent(
                            event_type="collision",
                            frame_idx=frame_idx,
                            timestamp_s=frame_idx / self.fps,
                            objects_involved=[r1["tracker_id"], r2["tracker_id"]],
                            position_cm=((r1["x_cm"] + r2["x_cm"]) / 2.0, (r1["y_cm"] + r2["y_cm"]) / 2.0),
                            metadata={"distance_cm": dist}
                        )
                        events_this_frame.append(ev)

        # 4. GOAL
        if ball is not None:
            y_cm = ball["y_cm"]
            if y_cm < self.GOAL_ZONE_Y_CM or y_cm > (243.0 - self.GOAL_ZONE_Y_CM):
                if not self.is_on_cooldown("goal", frame_idx):
                    ev = GameEvent(
                        event_type="goal",
                        frame_idx=frame_idx,
                        timestamp_s=frame_idx / self.fps,
                        objects_involved=[],
                        position_cm=(ball["x_cm"], ball["y_cm"]),
                        metadata={"y_cm": y_cm}
                    )
                    events_this_frame.append(ev)

        # State updates
        self._prev_possession = curr_possessor_id
        self._prev_possessor_team = curr_team
        if ball is not None:
            self._prev_ball_pos = (ball["x_cm"], ball["y_cm"])
        else:
            self._prev_ball_pos = None

        self._detected_events.extend(events_this_frame)
        return events_this_frame

    def summary(self) -> dict:
        """Resumen agregado de todos los eventos detectados en la sesión."""
        from collections import Counter
        counts = Counter(ev.event_type for ev in self._detected_events)
        return {
            "total":      len(self._detected_events),
            "by_type":    dict(counts),
            "goals":      counts.get("goal", 0),
            "passes":     counts.get("pass", 0),
            "collisions": counts.get("collision", 0),
            "interceptions": counts.get("interception", 0),
            "possession_changes": counts.get("possession_change", 0),
        }
