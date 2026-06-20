import type { TrajectoryRecord } from "@/lib/api";

const OBJ_COLOR: Record<string, string> = {
  azul:  "#38bdf8",
  rojo:  "#f87171",
  balon: "#fbbf24",
};

function objColor(cls: string | null) {
  return OBJ_COLOR[cls ?? ""] ?? "#94a3b8";
}

type Props = {
  trajectories: TrajectoryRecord[];
};

export function FieldMap({ trajectories }: Props) {
  const W = 640;
  const H = 400;
  const PAD = 16;

  const pts = trajectories.filter(p => p.x_cm != null && p.y_cm != null);

  // Auto-bound from data with padding
  const xs = pts.map(p => p.x_cm!);
  const ys = pts.map(p => p.y_cm!);
  const minX = xs.length ? Math.min(...xs) - 10 : 0;
  const maxX = xs.length ? Math.max(...xs) + 10 : 182;
  const minY = ys.length ? Math.min(...ys) - 10 : 0;
  const maxY = ys.length ? Math.max(...ys) + 10 : 243;
  const rangeX = maxX - minX || 1;
  const rangeY = maxY - minY || 1;

  const toX = (x: number) => PAD + ((x - minX) / rangeX) * (W - PAD * 2);
  const toY = (y: number) => PAD + ((y - minY) / rangeY) * (H - PAD * 2);

  // Group by object_id, sorted by frame_idx
  const byObj = new Map<number, TrajectoryRecord[]>();
  for (const pt of pts) {
    const list = byObj.get(pt.object_id) ?? [];
    list.push(pt);
    byObj.set(pt.object_id, list);
  }
  for (const list of byObj.values()) {
    list.sort((a, b) => a.frame_idx - b.frame_idx);
  }

  const midX = W / 2;
  const midY = H / 2;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full rounded-xl overflow-hidden">
      {/* Field background */}
      <rect width={W} height={H} fill="#064e3b" />
      {/* Alternating stripes */}
      {Array.from({ length: 8 }).map((_, i) => (
        <rect
          key={i}
          x={0} y={(i / 8) * H}
          width={W} height={H / 8}
          fill={i % 2 === 0 ? "rgba(0,0,0,0.08)" : "transparent"}
        />
      ))}
      {/* Border */}
      <rect x={PAD} y={PAD} width={W - PAD * 2} height={H - PAD * 2} rx={4} fill="none" stroke="#065f46" strokeWidth={1.5} />
      {/* Center line */}
      <line x1={midX} y1={PAD} x2={midX} y2={H - PAD} stroke="#065f46" strokeWidth={1.5} />
      {/* Center circle */}
      <circle cx={midX} cy={midY} r={H * 0.11} fill="none" stroke="#065f46" strokeWidth={1.5} />
      {/* Center dot */}
      <circle cx={midX} cy={midY} r={3} fill="#065f46" />
      {/* Goal areas */}
      <rect x={PAD} y={midY - H * 0.15} width={W * 0.1} height={H * 0.3} fill="none" stroke="#065f46" strokeWidth={1} />
      <rect x={W - PAD - W * 0.1} y={midY - H * 0.15} width={W * 0.1} height={H * 0.3} fill="none" stroke="#065f46" strokeWidth={1} />

      {/* Trajectories */}
      {Array.from(byObj.entries()).map(([oid, objPts]) => {
        const cls = objPts.at(-1)?.object_class ?? null;
        const c = objColor(cls);
        const isball = cls === "balon";
        const pathStr = objPts.map(p => `${toX(p.x_cm!)},${toY(p.y_cm!)}`).join(" ");
        const last = objPts.at(-1)!;
        const lx = toX(last.x_cm!);
        const ly = toY(last.y_cm!);
        const hasPred = last.predicted_x_cm != null && last.predicted_y_cm != null;
        const px = hasPred ? toX(last.predicted_x_cm!) : lx;
        const py = hasPred ? toY(last.predicted_y_cm!) : ly;

        return (
          <g key={oid}>
            {/* Trail */}
            {objPts.length > 1 && (
              <polyline
                points={pathStr}
                fill="none"
                stroke={c}
                strokeWidth={isball ? 1.5 : 1}
                strokeOpacity={0.38}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}
            {/* Kalman prediction dashed line */}
            {hasPred && (
              <line
                x1={lx} y1={ly} x2={px} y2={py}
                stroke={c}
                strokeWidth={1.5}
                strokeOpacity={0.7}
                strokeDasharray="4 3"
              />
            )}
            {/* Current position */}
            <circle cx={lx} cy={ly} r={isball ? 5 : 7} fill={c} opacity={0.92} />
            {!isball && (
              <text x={lx + 9} y={ly + 4} fontSize={8} fill={c} opacity={0.9}>{oid}</text>
            )}
          </g>
        );
      })}

      {/* Legend */}
      <g transform={`translate(${PAD + 4}, ${H - PAD - 4})`}>
        {(["azul", "rojo", "balon"] as const).map((lbl, i) => (
          <g key={lbl} transform={`translate(${i * 68}, 0)`}>
            <circle r={4} fill={OBJ_COLOR[lbl]} />
            <text x={8} y={4} fontSize={8.5} fill={OBJ_COLOR[lbl]}>{lbl}</text>
          </g>
        ))}
        <text x={240} y={4} fontSize={7.5} fill="#475569">— historial  - - prediccion Kalman</text>
      </g>
    </svg>
  );
}
