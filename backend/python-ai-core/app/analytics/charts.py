"""
Charts — generadores de figuras Plotly para FutBotMX.

Cada función recibe datos ya procesados (KPIs, telemetría, eventos, heatmaps)
y retorna un dict serializable con fig.to_dict() listo para enviarse al
frontend vía API y renderizarse con Plotly.js / react-plotly.js.

Tema visual: oscuro, colores azul #2563EB / rojo #DC2626.
"""

from __future__ import annotations

import numpy as np
from typing import Optional

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    _PLOTLY_OK = True
except ImportError:
    _PLOTLY_OK = False

# ---------------------------------------------------------------------------
# Tema compartido
# ---------------------------------------------------------------------------

_DARK = dict(
    paper_bgcolor="#0F172A",
    plot_bgcolor="#1E293B",
    font=dict(color="#E2E8F0", family="Inter, sans-serif", size=12),
    margin=dict(l=40, r=20, t=50, b=40),
)

_TEAM_COLORS = {"azul": "#2563EB", "rojo": "#DC2626", "balon": "#F59E0B", "ninguno": "#6B7280"}
_EVENT_COLORS = {
    "goal":              "#FACC15",
    "pass":              "#34D399",
    "collision":         "#F87171",
    "interception":      "#A78BFA",
    "possession_change": "#60A5FA",
}


def _guard() -> Optional[dict]:
    if not _PLOTLY_OK:
        return {"error": "plotly no instalado"}
    return None


def _apply_theme(fig: "go.Figure") -> "go.Figure":
    fig.update_layout(**_DARK)
    return fig


# ---------------------------------------------------------------------------
# 1. Donut de posesión
# ---------------------------------------------------------------------------

def possession_donut(kpis: dict) -> dict:
    """Donut interactivo azul / rojo / ninguno."""
    err = _guard()
    if err:
        return err

    azul  = kpis.get("azul",  {}).get("possession_pct", 0)
    rojo  = kpis.get("rojo",  {}).get("possession_pct", 0)
    none_ = kpis.get("global", {}).get("possession_changes", 0)
    ninguno = max(0, 100 - azul - rojo)

    fig = go.Figure(go.Pie(
        labels=["Azul", "Rojo", "Ninguno"],
        values=[azul, rojo, ninguno],
        hole=0.55,
        marker_colors=[_TEAM_COLORS["azul"], _TEAM_COLORS["rojo"], _TEAM_COLORS["ninguno"]],
        textinfo="label+percent",
        hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title="Posesión de balón",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        **_DARK,
    )
    return fig.to_dict()


# ---------------------------------------------------------------------------
# 2. Timeline de velocidad por equipo
# ---------------------------------------------------------------------------

def speed_timeline(timeline_data: list[dict]) -> dict:
    """Línea de velocidad promedio (cm/s) por equipo a lo largo del partido."""
    err = _guard()
    if err:
        return err

    if not timeline_data:
        return go.Figure().to_dict()

    t   = [d["t_s"] for d in timeline_data]
    az  = [d.get("azul_avg", 0) for d in timeline_data]
    ro  = [d.get("rojo_avg", 0) for d in timeline_data]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t, y=az, name="Azul",
        line=dict(color=_TEAM_COLORS["azul"], width=2),
        fill="tozeroy", fillcolor="rgba(37,99,235,0.15)",
        hovertemplate="t=%{x}s  vel=%{y:.1f} cm/s<extra>Azul</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=t, y=ro, name="Rojo",
        line=dict(color=_TEAM_COLORS["rojo"], width=2),
        fill="tozeroy", fillcolor="rgba(220,38,38,0.15)",
        hovertemplate="t=%{x}s  vel=%{y:.1f} cm/s<extra>Rojo</extra>",
    ))
    fig.update_layout(
        title="Velocidad promedio por equipo",
        xaxis_title="Tiempo (s)",
        yaxis_title="Velocidad (cm/s)",
        **_DARK,
    )
    return fig.to_dict()


# ---------------------------------------------------------------------------
# 3. Scatter de eventos en línea de tiempo
# ---------------------------------------------------------------------------

def event_scatter(events: list[dict]) -> dict:
    """Scatter de eventos sobre eje temporal, color por tipo."""
    err = _guard()
    if err:
        return err

    if not events:
        return go.Figure().to_dict()

    by_type: dict[str, list] = {}
    for ev in events:
        etype = ev.get("event_type", "unknown")
        by_type.setdefault(etype, []).append(ev)

    fig = go.Figure()
    for etype, evs in by_type.items():
        ts   = [e.get("timestamp_s", 0) for e in evs]
        ys   = [etype] * len(evs)
        meta = [str(e.get("metadata", {})) for e in evs]
        fig.add_trace(go.Scatter(
            x=ts, y=ys, mode="markers",
            name=etype,
            marker=dict(
                color=_EVENT_COLORS.get(etype, "#94A3B8"),
                size=12,
                symbol="circle",
                line=dict(width=1, color="#1E293B"),
            ),
            hovertemplate="t=%{x:.1f}s<br>%{customdata}<extra>" + etype + "</extra>",
            customdata=meta,
        ))

    fig.update_layout(
        title="Línea de tiempo de eventos",
        xaxis_title="Tiempo (s)",
        yaxis_title="Tipo de evento",
        **_DARK,
    )
    return fig.to_dict()


# ---------------------------------------------------------------------------
# 4. Barras de control de zona (Voronoi)
# ---------------------------------------------------------------------------

def zone_control_bar(kpis: dict) -> dict:
    """Barras horizontales de control de zona por equipo."""
    err = _guard()
    if err:
        return err

    az = kpis.get("azul", {}).get("zone_control_pct", 50)
    ro = kpis.get("rojo", {}).get("zone_control_pct", 50)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Azul",
        x=[az], y=["Control de zona"],
        orientation="h",
        marker_color=_TEAM_COLORS["azul"],
        hovertemplate="Azul: %{x:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Rojo",
        x=[ro], y=["Control de zona"],
        orientation="h",
        marker_color=_TEAM_COLORS["rojo"],
        hovertemplate="Rojo: %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title="Control territorial (Voronoi promedio)",
        barmode="stack",
        xaxis=dict(range=[0, 100], ticksuffix="%"),
        **_DARK,
    )
    return fig.to_dict()


# ---------------------------------------------------------------------------
# 5. Distancia recorrida por robot
# ---------------------------------------------------------------------------

def distance_bars(robots_kpi: dict) -> dict:
    """Barras de distancia recorrida (cm) por robot, agrupadas por equipo."""
    err = _guard()
    if err:
        return err

    if not robots_kpi:
        return go.Figure().to_dict()

    labels, values, colors = [], [], []
    for tid, r in sorted(robots_kpi.items()):
        if r.get("team") == "balon":
            continue
        labels.append(f"#{tid} ({r.get('team','?')})")
        values.append(r.get("distance_covered_cm", 0))
        colors.append(r.get("color", "#94A3B8"))

    fig = go.Figure(go.Bar(
        x=values, y=labels,
        orientation="h",
        marker_color=colors,
        hovertemplate="%{y}: %{x:.0f} cm<extra></extra>",
    ))
    fig.update_layout(
        title="Distancia recorrida por robot",
        xaxis_title="Distancia (cm)",
        **_DARK,
    )
    return fig.to_dict()


# ---------------------------------------------------------------------------
# 6. Heatmap de campo (por equipo)
# ---------------------------------------------------------------------------

def field_heatmap(heatmap_data: dict, team: str = "azul") -> dict:
    """
    Heatmap de ocupación espacial sobre el campo canónico.
    heatmap_data: salida de HeatmapAccumulator.to_json()  →  {azul: [[...]], rojo: [...], balon: [...]}
    """
    err = _guard()
    if err:
        return err

    matrix = heatmap_data.get(team)
    if matrix is None:
        return go.Figure().to_dict()

    arr = np.array(matrix, dtype=np.float32)
    color = "Blues" if team == "azul" else "Reds" if team == "rojo" else "YlOrBr"

    fig = go.Figure(go.Heatmap(
        z=arr,
        colorscale=color,
        showscale=True,
        hovertemplate="x=%{x}  y=%{y}  val=%{z:.3f}<extra></extra>",
    ))
    fig.update_layout(
        title=f"Mapa de calor — {team.capitalize()}",
        xaxis=dict(showticklabels=False, title="Campo (x)"),
        yaxis=dict(showticklabels=False, title="Campo (y)", autorange="reversed"),
        **_DARK,
    )
    return fig.to_dict()


# ---------------------------------------------------------------------------
# 7. Radarchart de KPIs por equipo
# ---------------------------------------------------------------------------

def team_radar(kpis: dict) -> dict:
    """Radar comparativo de KPIs normalizados entre azul y rojo."""
    err = _guard()
    if err:
        return err

    categories = [
        "Posesión %",
        "Vel. máx (cm/s)",
        "Vel. media (cm/s)",
        "Distancia (m)",
        "Control de zona %",
        "Goles",
    ]

    def _norm(val, max_val):
        return round(min(val / max_val * 100, 100), 1) if max_val else 0

    az = kpis.get("azul", {})
    ro = kpis.get("rojo", {})

    max_speed = max(az.get("max_speed_cm_s", 1), ro.get("max_speed_cm_s", 1), 1)
    max_avg   = max(az.get("avg_speed_cm_s", 1), ro.get("avg_speed_cm_s", 1), 1)
    max_dist  = max(az.get("distance_covered_cm", 1), ro.get("distance_covered_cm", 1), 1)
    max_goals = max(az.get("goals", 0), ro.get("goals", 0), 1)

    def _values(team: dict) -> list:
        return [
            team.get("possession_pct", 0),
            _norm(team.get("max_speed_cm_s", 0), max_speed),
            _norm(team.get("avg_speed_cm_s", 0), max_avg),
            _norm(team.get("distance_covered_cm", 0) / 100, max_dist / 100),
            team.get("zone_control_pct", 50),
            _norm(team.get("goals", 0), max_goals),
        ]

    fig = go.Figure()
    for team_key, color in [("azul", _TEAM_COLORS["azul"]), ("rojo", _TEAM_COLORS["rojo"])]:
        vals = _values(kpis.get(team_key, {}))
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=categories + [categories[0]],
            fill="toself",
            fillcolor=color.replace("#", "rgba(") + ",0.2)".replace("rgba(", "rgba("),
            line=dict(color=color, width=2),
            name=team_key.capitalize(),
        ))

    fig.update_layout(
        title="Radar comparativo de equipos",
        polar=dict(
            bgcolor="#1E293B",
            radialaxis=dict(
                visible=True, range=[0, 100],
                gridcolor="#334155", linecolor="#475569",
                tickfont=dict(color="#94A3B8", size=10),
            ),
            angularaxis=dict(gridcolor="#334155", linecolor="#475569"),
        ),
        paper_bgcolor="#0F172A",
        font=dict(color="#E2E8F0"),
        showlegend=True,
        legend=dict(orientation="h", y=-0.15),
        margin=dict(l=60, r=60, t=60, b=60),
    )
    return fig.to_dict()


# ---------------------------------------------------------------------------
# 8. Indicadores KPI (tarjetas tipo gauge)
# ---------------------------------------------------------------------------

def kpi_indicators(kpis: dict) -> dict:
    """Grid de indicadores: posesión, velocidad máx, goles, intensidad."""
    err = _guard()
    if err:
        return err

    az = kpis.get("azul",  {})
    ro = kpis.get("rojo",  {})
    gl = kpis.get("global", {})

    fig = make_subplots(
        rows=2, cols=3,
        specs=[[{"type": "indicator"}] * 3] * 2,
    )

    indicators = [
        (f"Posesión Azul", az.get("possession_pct", 0), "%", 1, 1),
        (f"Posesión Rojo",  ro.get("possession_pct", 0), "%", 1, 2),
        ("Intensidad táctica", gl.get("intensity_index", 0) * 100, "%", 1, 3),
        ("Vel. máx Azul", az.get("max_speed_cm_s", 0), " cm/s", 2, 1),
        ("Vel. máx Rojo",  ro.get("max_speed_cm_s", 0), " cm/s", 2, 2),
        ("Eventos / min",  gl.get("events_per_min", 0), "", 2, 3),
    ]

    colors_map = {
        "Posesión Azul":       _TEAM_COLORS["azul"],
        "Posesión Rojo":       _TEAM_COLORS["rojo"],
        "Intensidad táctica":  "#A78BFA",
        "Vel. máx Azul":       _TEAM_COLORS["azul"],
        "Vel. máx Rojo":       _TEAM_COLORS["rojo"],
        "Eventos / min":       "#34D399",
    }

    for title, value, suffix, row, col in indicators:
        fig.add_trace(go.Indicator(
            mode="number+delta" if "Vel" in title else "number",
            value=round(float(value), 1),
            title=dict(text=title, font=dict(size=13, color="#CBD5E1")),
            number=dict(
                suffix=suffix,
                font=dict(size=28, color=colors_map.get(title, "#E2E8F0")),
            ),
        ), row=row, col=col)

    fig.update_layout(
        height=280,
        paper_bgcolor="#0F172A",
        font=dict(color="#E2E8F0"),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    return fig.to_dict()


# ---------------------------------------------------------------------------
# 9. Trayectorias de robots
# ---------------------------------------------------------------------------

def trajectory_chart(
    telemetry: list[dict],
    predictions: Optional[dict] = None,
    field_w: float = 182.0,
    field_h: float = 243.0,
) -> dict:
    """
    Scatter de trayectorias históricas + línea punteada de predicción Kalman.
    """
    err = _guard()
    if err:
        return err

    from collections import defaultdict
    by_robot: dict[int, list] = defaultdict(list)
    for pt in telemetry:
        tid = pt.get("tracker_id", -1)
        if tid >= 0:
            by_robot[tid].append(pt)

    fig = go.Figure()

    # Contorno del campo
    fig.add_shape(type="rect", x0=0, y0=0, x1=field_w, y1=field_h,
                  line=dict(color="#475569", width=2))
    fig.add_shape(type="line", x0=0, y0=field_h / 2, x1=field_w, y1=field_h / 2,
                  line=dict(color="#475569", width=1, dash="dot"))

    for tid, pts in by_robot.items():
        pts_sorted = sorted(pts, key=lambda p: p.get("frame_idx", 0))
        team  = pts_sorted[-1].get("team", "ninguno")
        color = _TEAM_COLORS.get(team, "#94A3B8")
        xs = [p.get("x_cm", 0) for p in pts_sorted]
        ys = [p.get("y_cm", 0) for p in pts_sorted]

        # Trayectoria histórica
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers",
            name=f"#{tid} {team}",
            line=dict(color=color, width=1.5),
            marker=dict(size=4, color=color),
            opacity=0.7,
            hovertemplate=f"Robot #{tid} ({team})<br>x=%{{x:.0f}} y=%{{y:.0f}}<extra></extra>",
        ))

        # Predicción Kalman
        if predictions and tid in predictions and predictions[tid]:
            pred = predictions[tid]
            px_vals = [p[0] for p in pred]
            py_vals = [p[1] for p in pred]
            fig.add_trace(go.Scatter(
                x=[xs[-1]] + px_vals,
                y=[ys[-1]] + py_vals,
                mode="lines",
                name=f"#{tid} pred.",
                line=dict(color=color, width=1, dash="dash"),
                opacity=0.4,
                showlegend=False,
                hoverinfo="skip",
            ))

    fig.update_layout(
        title="Trayectorias y predicciones (Kalman)",
        xaxis=dict(range=[-5, field_w + 5], title="x (cm)", gridcolor="#1E293B"),
        yaxis=dict(range=[-5, field_h + 5], title="y (cm)", gridcolor="#1E293B",
                   scaleanchor="x", scaleratio=1),
        **_DARK,
    )
    return fig.to_dict()


# ---------------------------------------------------------------------------
# 10. Dashboard consolidado (subplots)
# ---------------------------------------------------------------------------

def dashboard(
    kpis: dict,
    telemetry: list[dict],
    events: list[dict],
    heatmap_data: Optional[dict] = None,
    predictions: Optional[dict] = None,
) -> dict:
    """
    Figura única con 6 subplots:
      [Donut posesión] [Radar equipos  ] [KPI indicators  ]
      [Speed timeline] [Event scatter  ] [Zone control bar]
    """
    err = _guard()
    if err:
        return err

    charts = {
        "possession_donut": possession_donut(kpis),
        "team_radar":       team_radar(kpis),
        "kpi_indicators":   kpi_indicators(kpis),
        "speed_timeline":   speed_timeline(kpis.get("timeline", {}).get("speed", [])),
        "event_scatter":    event_scatter(events),
        "zone_control":     zone_control_bar(kpis),
        "distance_bars":    distance_bars(kpis.get("robots", {})),
        "trajectory":       trajectory_chart(telemetry, predictions),
    }

    if heatmap_data:
        charts["heatmap_azul"] = field_heatmap(heatmap_data, "azul")
        charts["heatmap_rojo"] = field_heatmap(heatmap_data, "rojo")

    return charts
