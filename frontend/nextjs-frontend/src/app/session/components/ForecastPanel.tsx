import type { SessionSummary } from "@/lib/api";
import { FieldMap } from "@/app/components/charts/FieldMap";
import { VelocityBars } from "@/app/components/charts/VelocityBars";

type Props = { summary: SessionSummary | null };

export function ForecastPanel({ summary }: Props) {
  const trajectories = summary?.recent_trajectories ?? [];
  const progress = summary ? `${summary.progress_pct.toFixed(0)}%` : "idle";

  const byClass: Record<string, Set<number>> = {};
  for (const pt of trajectories) {
    const cls = pt.object_class ?? "desconocido";
    if (!byClass[cls]) byClass[cls] = new Set();
    byClass[cls].add(pt.object_id);
  }

  const totalObjects = new Set(trajectories.map(p => p.object_id)).size;
  const withPrediction = trajectories.filter(
    p => p.predicted_x_cm != null && p.predicted_y_cm != null
  ).length;

  return (
    <section className="panel-shell">
      <div className="flex items-center justify-between">
        <div>
          <p className="panel-kicker">Forecast</p>
          <h2 className="panel-title">Trayectorias y prediccion Kalman</h2>
        </div>
        <span className="badge-neutral">{progress}</span>
      </div>

      {/* Field map */}
      <div className="mt-5 rounded-[1.5rem] border border-slate-800 bg-slate-950/60 p-4">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">
            Campo — posicion en tiempo real
          </p>
          <span className="text-xs text-slate-500">
            {totalObjects} objetos · {withPrediction} con prediccion
          </span>
        </div>
        {trajectories.length > 0 ? (
          <FieldMap trajectories={trajectories} />
        ) : (
          <div className="flex aspect-[16/10] items-center justify-center rounded-xl bg-emerald-950/30 text-sm text-slate-500">
            Sin datos de trayectoria todavia. Inicia una sesion para ver el campo.
          </div>
        )}
      </div>

      {/* Velocity bars */}
      <div className="mt-4 rounded-[1.5rem] border border-slate-800 bg-slate-900/70 p-4">
        <p className="mb-3 text-xs uppercase tracking-[0.35em] text-slate-400">
          Velocidad instantanea por objeto (ultimos frames)
        </p>
        <VelocityBars trajectories={trajectories} />
      </div>

      {/* Object count summary */}
      <div className="mt-4 grid grid-cols-3 gap-3">
        {(["azul", "rojo", "balon"] as const).map(cls => {
          const colorClass =
            cls === "azul" ? "text-sky-400"
            : cls === "rojo" ? "text-red-400"
            : "text-amber-400";
          const count = byClass[cls]?.size ?? 0;
          return (
            <div key={cls} className="rounded-[1.25rem] bg-slate-950 p-3 text-center">
              <p className={`text-xs uppercase tracking-widest ${colorClass}`}>{cls}</p>
              <p className="mt-1 font-display text-3xl text-white">{count}</p>
              <p className="text-xs text-slate-500">objetos</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
