import type { TrajectoryRecord } from "@/lib/api";

const FPS = 30;

type ObjSpeed = { id: number; cls: string | null; speed: number };

function derivespeeds(trajectories: TrajectoryRecord[]): ObjSpeed[] {
  const byObj = new Map<number, TrajectoryRecord[]>();
  for (const pt of trajectories) {
    if (pt.x_cm == null || pt.y_cm == null) continue;
    const list = byObj.get(pt.object_id) ?? [];
    list.push(pt);
    byObj.set(pt.object_id, list);
  }

  const results: ObjSpeed[] = [];
  for (const [oid, pts] of byObj.entries()) {
    pts.sort((a, b) => a.frame_idx - b.frame_idx);
    const last = pts.at(-1)!;
    const prev = pts.at(-2);
    if (!prev) {
      results.push({ id: oid, cls: last.object_class, speed: 0 });
      continue;
    }
    const dx = last.x_cm! - prev.x_cm!;
    const dy = last.y_cm! - prev.y_cm!;
    const dt = Math.max(1, last.frame_idx - prev.frame_idx) / FPS;
    results.push({
      id: oid,
      cls: last.object_class,
      speed: Math.hypot(dx, dy) / dt,
    });
  }

  return results.sort((a, b) => b.speed - a.speed);
}

type Props = { trajectories: TrajectoryRecord[] };

export function VelocityBars({ trajectories }: Props) {
  const objects = derivespeeds(trajectories);

  if (objects.length === 0) {
    return <p className="py-2 text-xs text-slate-500">Sin datos de velocidad todavia.</p>;
  }

  const maxSpeed = Math.max(...objects.map(o => o.speed), 1);

  return (
    <div className="space-y-2">
      {objects.map(obj => {
        const pct = (obj.speed / maxSpeed) * 100;
        const barColor =
          obj.cls === "azul" ? "bg-sky-500"
          : obj.cls === "rojo" ? "bg-red-500"
          : "bg-amber-400";
        const textColor =
          obj.cls === "azul" ? "text-sky-400"
          : obj.cls === "rojo" ? "text-red-400"
          : "text-amber-400";
        const label = obj.cls === "balon" ? "Balon" : `#${obj.id} ${obj.cls ?? "?"}`;

        return (
          <div key={obj.id} className="flex items-center gap-2 text-xs">
            <span className={`w-16 shrink-0 truncate font-medium ${textColor}`}>{label}</span>
            <div className="flex-1 h-2.5 rounded-full bg-slate-800 overflow-hidden">
              <div
                className={`h-full ${barColor} rounded-full transition-all duration-500`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="w-16 text-right text-slate-300">{obj.speed.toFixed(0)} cm/s</span>
          </div>
        );
      })}
    </div>
  );
}
