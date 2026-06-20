export const SESSION_PANELS = ["analytics", "forecast", "narracion"] as const;
export const SESSION_MODES = ["live", "history", "video"] as const;

export type SessionPanel = (typeof SESSION_PANELS)[number];
export type SessionModeView = (typeof SESSION_MODES)[number];

export const SESSION_PANEL_META: Record<SessionPanel, { label: string; title: string; description: string }> = {
  analytics: {
    label: "Analytics",
    title: "Overlay + control espacial",
    description: "Vista dedicada a telemetria, overlay y lectura operativa del partido.",
  },
  forecast: {
    label: "Forecast",
    title: "Trayectorias proyectadas",
    description: "Vista dedicada a proyecciones de movimiento y evolucion esperada del juego.",
  },
  narracion: {
    label: "Narracion",
    title: "Ticker tactico + TTS local",
    description: "Vista dedicada a eventos narrados, playback de audio y salida ejecutiva.",
  },
};

export const SESSION_MODE_META: Record<SessionModeView, { label: string; description: string }> = {
  live: {
    label: "Live",
    description: "Operacion en vivo con monitoreo continuo desde camara o stream.",
  },
  history: {
    label: "History",
    description: "Revision de casos persistidos y sesiones ya cerradas.",
  },
  video: {
    label: "Video",
    description: "Analisis batch de material grabado con procesamiento asincrono.",
  },
};

export function isSessionPanel(value: string): value is SessionPanel {
  return SESSION_PANELS.includes(value as SessionPanel);
}

export function isSessionModeView(value: string): value is SessionModeView {
  return SESSION_MODES.includes(value as SessionModeView);
}

export function buildSessionRoute(panel: SessionPanel, mode: SessionModeView, sessionId?: string | null) {
  const base = `/session/${panel}/${mode}`;
  return sessionId ? `${base}?sessionId=${sessionId}` : base;
}
