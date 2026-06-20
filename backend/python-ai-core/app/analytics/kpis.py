"""
KPI Engine — métricas agregadas de sesión para FutBotMX.

Consume:
  - session_summary: dict del PipelineOrchestrator.get_session_summary()
  - telemetry:       list[dict] con puntos {tracker_id, team, frame_idx,
                     timestamp_s, x_cm, y_cm, speed_cm_s}
  - events:          list[dict] serializados de GameEvent

Produce:
  - dict con KPIs por equipo, globales y por robot individual.
"""

from collections import defaultdict
from typing import Optional
import numpy as np


# ---------------------------------------------------------------------------
# Constantes de campo (cm)
# ---------------------------------------------------------------------------
FIELD_W_CM = 182.0
FIELD_H_CM = 243.0
FIELD_AREA_CM2 = FIELD_W_CM * FIELD_H_CM

# Colores canónicos por equipo
TEAM_COLORS = {
    "azul":  "#2563EB",
    "rojo":  "#DC2626",
    "balon": "#F59E0B",
    "ninguno": "#6B7280",
}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _safe_mean(values: list) -> float:
    return float(np.mean(values)) if values else 0.0


def _safe_max(values: list) -> float:
    return float(np.max(values)) if values else 0.0


def _group_telemetry(telemetry: list[dict]) -> dict[int, list[dict]]:
    """Agrupa puntos de telemetría por tracker_id."""
    groups: dict[int, list[dict]] = defaultdict(list)
    for pt in telemetry:
        tid = pt.get("tracker_id", -1)
        if tid >= 0:
            groups[tid].append(pt)
    return dict(groups)


def _distance_covered(points: list[dict]) -> float:
    """Distancia total recorrida (cm) para una secuencia de puntos ordenados."""
    if len(points) < 2:
        return 0.0
    pts = sorted(points, key=lambda p: p.get("frame_idx", 0))
    total = 0.0
    for i in range(1, len(pts)):
        dx = pts[i].get("x_cm", 0) - pts[i - 1].get("x_cm", 0)
        dy = pts[i].get("y_cm", 0) - pts[i - 1].get("y_cm", 0)
        total += float(np.hypot(dx, dy))
    return round(total, 2)


def _robot_team(points: list[dict]) -> str:
    """Equipo dominante para un tracker_id."""
    teams = [p.get("team", "ninguno") for p in points if p.get("team") not in (None, "balon")]
    if not teams:
        return "ninguno"
    return max(set(teams), key=teams.count)


# ---------------------------------------------------------------------------
# Motor principal
# ---------------------------------------------------------------------------

class KPIEngine:
    """Calcula KPIs tácticos a partir de los datos acumulados de sesión."""

    def compute(
        self,
        session_summary: dict,
        telemetry: list[dict],
        events: list[dict],
        voronoi_snapshots: Optional[list[dict]] = None,
    ) -> dict:
        """
        Retorna dict estructurado con:
          global    → KPIs generales de sesión
          azul      → KPIs del equipo azul
          rojo      → KPIs del equipo rojo
          robots    → KPIs por tracker_id individual
          events    → conteo y distribución de eventos
          timeline  → series temporales para graficado
        """
        total_frames = session_summary.get("total_frames", 0)
        fps = session_summary.get("fps_actual", 30.0) or 30.0
        duration_s = total_frames / fps if fps > 0 else 0.0

        # Posesión acumulada de session_summary
        possession = session_summary.get("possession", {})
        poss_azul  = possession.get("azul",   0.0)
        poss_rojo  = possession.get("rojo",   0.0)
        poss_none  = possession.get("ninguno", 100.0)

        # Telemetría agrupada por tracker_id
        by_robot = _group_telemetry(telemetry)

        # KPIs por robot
        robots_kpi: dict[int, dict] = {}
        team_speeds: dict[str, list[float]] = defaultdict(list)
        team_distances: dict[str, float] = defaultdict(float)

        for tid, pts in by_robot.items():
            team = _robot_team(pts)
            speeds = [p.get("speed_cm_s", 0.0) or 0.0 for p in pts]
            dist   = _distance_covered(pts)

            robots_kpi[tid] = {
                "tracker_id":        tid,
                "team":              team,
                "avg_speed_cm_s":    round(_safe_mean(speeds), 2),
                "max_speed_cm_s":    round(_safe_max(speeds), 2),
                "distance_covered_cm": dist,
                "frames_active":     len(pts),
                "color":             TEAM_COLORS.get(team, "#9CA3AF"),
            }
            team_speeds[team].extend(speeds)
            team_distances[team] += dist

        # Conteo de eventos
        events_by_type: dict[str, int] = defaultdict(int)
        goals_by_team:  dict[str, int] = {"azul": 0, "rojo": 0}
        passes_by_team: dict[str, int] = {"azul": 0, "rojo": 0}

        for ev in events:
            etype = ev.get("event_type", "unknown")
            events_by_type[etype] += 1
            meta  = ev.get("metadata", {})
            team  = meta.get("team", meta.get("scorer_team", ""))
            if etype == "goal" and team in goals_by_team:
                goals_by_team[team] += 1
            if etype == "pass" and team in passes_by_team:
                passes_by_team[team] += 1

        total_events     = len(events)
        events_per_min   = round((total_events / duration_s) * 60, 2) if duration_s > 0 else 0.0
        intensity_index  = min(round(events_per_min / 10.0, 3), 1.0)  # normalizado a [0,1]

        # Control de zona promedio (Voronoi snapshots opcionales)
        zone_azul_avg = 50.0
        zone_rojo_avg = 50.0
        if voronoi_snapshots:
            az_vals = [s.get("azul_pct", 50) for s in voronoi_snapshots if s]
            ro_vals = [s.get("rojo_pct", 50) for s in voronoi_snapshots if s]
            if az_vals:
                zone_azul_avg = round(_safe_mean(az_vals), 2)
                zone_rojo_avg = round(_safe_mean(ro_vals), 2)

        # Timeline: velocidad promedio por ventana de tiempo (10 s)
        speed_timeline = self._build_speed_timeline(telemetry, fps, window_s=10)

        # Timeline: eventos por ventana de tiempo
        event_timeline = self._build_event_timeline(events, duration_s, window_s=10)

        return {
            "global": {
                "total_frames":      total_frames,
                "duration_s":        round(duration_s, 2),
                "fps":               fps,
                "total_events":      total_events,
                "events_per_min":    events_per_min,
                "intensity_index":   intensity_index,
                "possession_changes": events_by_type.get("possession_change", 0),
            },
            "azul": {
                "possession_pct":      round(poss_azul, 2),
                "avg_speed_cm_s":      round(_safe_mean(team_speeds.get("azul", [])), 2),
                "max_speed_cm_s":      round(_safe_max(team_speeds.get("azul", [])), 2),
                "distance_covered_cm": round(team_distances.get("azul", 0.0), 2),
                "goals":               goals_by_team["azul"],
                "passes":              events_by_type.get("pass", 0),
                "zone_control_pct":    zone_azul_avg,
                "color":               TEAM_COLORS["azul"],
            },
            "rojo": {
                "possession_pct":      round(poss_rojo, 2),
                "avg_speed_cm_s":      round(_safe_mean(team_speeds.get("rojo", [])), 2),
                "max_speed_cm_s":      round(_safe_max(team_speeds.get("rojo", [])), 2),
                "distance_covered_cm": round(team_distances.get("rojo", 0.0), 2),
                "goals":               goals_by_team["rojo"],
                "passes":              passes_by_team["rojo"],
                "zone_control_pct":    zone_rojo_avg,
                "color":               TEAM_COLORS["rojo"],
            },
            "robots":  robots_kpi,
            "events": {
                "by_type":        dict(events_by_type),
                "goals":          goals_by_team,
                "total":          total_events,
                "events_per_min": events_per_min,
            },
            "timeline": {
                "speed":  speed_timeline,
                "events": event_timeline,
            },
        }

    # ------------------------------------------------------------------
    # Series temporales
    # ------------------------------------------------------------------

    def _build_speed_timeline(
        self,
        telemetry: list[dict],
        fps: float,
        window_s: float = 10.0,
    ) -> list[dict]:
        """
        Velocidad media por equipo en ventanas de `window_s` segundos.
        Retorna lista de {t_s, azul_avg, rojo_avg}.
        """
        if not telemetry:
            return []

        window_frames = int(window_s * fps)
        max_frame = max((p.get("frame_idx", 0) for p in telemetry), default=0)
        result = []

        for start in range(0, max_frame + 1, window_frames):
            end = start + window_frames
            window_pts = [p for p in telemetry if start <= p.get("frame_idx", 0) < end]
            azul_speeds = [p.get("speed_cm_s", 0) or 0 for p in window_pts if p.get("team") == "azul"]
            rojo_speeds = [p.get("speed_cm_s", 0) or 0 for p in window_pts if p.get("team") == "rojo"]
            result.append({
                "t_s":      round(start / fps, 1),
                "azul_avg": round(_safe_mean(azul_speeds), 2),
                "rojo_avg": round(_safe_mean(rojo_speeds), 2),
            })

        return result

    def _build_event_timeline(
        self,
        events: list[dict],
        duration_s: float,
        window_s: float = 10.0,
    ) -> list[dict]:
        """
        Cantidad de eventos por ventana de `window_s` segundos.
        Retorna lista de {t_s, count}.
        """
        if not events or duration_s <= 0:
            return []

        result = []
        for start in np.arange(0, duration_s, window_s):
            end = start + window_s
            count = sum(
                1 for ev in events
                if start <= ev.get("timestamp_s", 0) < end
            )
            result.append({"t_s": round(float(start), 1), "count": count})

        return result
