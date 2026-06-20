import { LiveCameraPreview } from "@/app/components/LiveCameraPreview";
import { getSessionSourceUrl, type SessionSummary } from "@/lib/api";
import { PossessionBar } from "@/app/components/charts/PossessionBar";
import { HeatmapGrid } from "@/app/components/charts/HeatmapGrid";
import { SpeedGauge } from "@/app/components/charts/SpeedGauge";

type Props = { summary: SessionSummary | null };

export function AnalyticsPanel({ summary }: Props) {
  const metrics = summary?.metrics_snapshot ?? {};
  const trajectories = summary?.recent_trajectories ?? [];
  const events = summary?.pending_events ?? [];

  const blue = Number(metrics.possession_blue ?? 0);
  const red = Number(metrics.possession_red ?? 0);
  const neutral = Number(metrics.possession_neutral ?? 0);
  const avgSpeed = Number(metrics.avg_speed_cm_s ?? 0);
  const maxSpeed = Number(metrics.max_speed_cm_s ?? 0);
  const frames = Number(metrics.telemetry_frames ?? metrics.processed_points ?? 0);

  const sessionId = summary?.session.id;
  const isVideo = Boolean(summary?.session.mode === "video" && sessionId);
  const isLive = Boolean(summary?.session.mode === "live");

  return (
    <section className="panel-shell">
      <div className="flex items-center justify-between">
        <div>
          <p className="panel-kicker">Analytics</p>
          <h2 className="panel-title">Control espacial</h2>
        </div>
        <span className="badge-neutral">{summary?.stage ?? "idle"}</span>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1.4fr_0.9fr]">
        {/* Video / camera preview */}
        <div className="rounded-[1.5rem] border border-white/10 bg-[linear-gradient(135deg,_rgba(11,18,32,0.95),_rgba(18,74,110,0.72))] p-5">
          <div className="grid aspect-video overflow-hidden rounded-[1.25rem] border border-cyan-300/15 bg-[radial-gradient(circle_at_center,_rgba(34,197,94,0.18),_rgba(3,7,18,0.92))]">
            {isVideo ? (
              <video
                key={sessionId}
                className="h-full w-full bg-black object-contain"
                src={getSessionSourceUrl(sessionId!)}
                controls
                playsInline
                preload="metadata"
              />
            ) : isLive ? (
              <LiveCameraPreview description="Sesion live — camara local del navegador. Concede permiso si no aparece." />
            ) : (
              <div className="grid place-items-center px-6 text-center">
                <div>
                  <p className="text-sm uppercase tracking-[0.5em] text-cyan-100/70">Sin sesion activa</p>
                  <p className="mt-4 text-sm leading-7 text-cyan-50/90">
                    Carga un video o inicia una sesion live para ver analitica en tiempo real.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right column */}
        <div className="grid gap-4">
          {/* Possession bar */}
          <div className="rounded-[1.5rem] border border-slate-800 bg-slate-900/70 p-4">
            <p className="mb-3 text-xs uppercase tracking-[0.35em] text-slate-400">Posesion de balon</p>
            <PossessionBar blue={blue} red={red} neutral={neutral} />
          </div>

          {/* Heatmap */}
          <div className="rounded-[1.5rem] border border-slate-800 bg-slate-900/70 p-4">
            <p className="mb-3 text-xs uppercase tracking-[0.35em] text-slate-400">
              Mapa de calor — ocupacion espacial
            </p>
            <HeatmapGrid trajectories={trajectories} />
          </div>

          {/* Speed gauge + metric counters */}
          <div className="rounded-[1.25rem] bg-slate-950 p-4">
            <div className="flex items-center gap-4">
              <SpeedGauge avg={avgSpeed} max={maxSpeed} />
              <div className="grid flex-1 grid-cols-2 gap-2">
                {[
                  { label: "Frames", value: frames },
                  { label: "Eventos", value: events.length },
                  { label: "Puntos tray.", value: trajectories.length },
                  {
                    label: "Progreso",
                    value: summary ? `${summary.progress_pct.toFixed(0)}%` : "—",
                  },
                ].map(({ label, value }) => (
                  <div key={label} className="rounded-xl bg-slate-900 p-2.5">
                    <p className="text-xs uppercase tracking-[0.25em] text-slate-400">{label}</p>
                    <p className="mt-1 font-display text-2xl text-white">{value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent events pills */}
      {events.length > 0 && (
        <div className="mt-5 rounded-[1.5rem] border border-slate-800 bg-slate-900/50 p-4">
          <p className="mb-3 text-xs uppercase tracking-[0.35em] text-slate-400">
            Eventos recientes ({events.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {events.slice(-12).map((ev, i) => (
              <span
                key={i}
                className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-300"
              >
                {ev.timestamp_s.toFixed(1)}s · {ev.event_type}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
