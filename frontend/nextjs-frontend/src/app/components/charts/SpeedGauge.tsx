type Props = {
  avg: number;
  max: number;
  maxScale?: number;
};

export function SpeedGauge({ avg, max, maxScale = 200 }: Props) {
  const R = 38;
  const CX = 52;
  const CY = 48;
  const pct = Math.min(1, avg / maxScale);

  // Semicircle arc: from 180° (left) sweeping clockwise to 0° (right)
  const arcPath = (fraction: number) => {
    if (fraction <= 0) return "";
    if (fraction >= 1) fraction = 0.9999;
    const startRad = Math.PI;
    const endRad = Math.PI - fraction * Math.PI;
    const sx = CX + R * Math.cos(startRad);
    const sy = CY - R * Math.sin(startRad);
    const ex = CX + R * Math.cos(endRad);
    const ey = CY - R * Math.sin(endRad);
    return `M ${sx} ${sy} A ${R} ${R} 0 0 1 ${ex} ${ey}`;
  };

  // Color transition: cyan → amber → red based on pct
  const strokeColor =
    pct < 0.5 ? "#38bdf8" : pct < 0.75 ? "#fb923c" : "#f87171";

  return (
    <div className="flex flex-col items-center gap-0.5">
      <svg viewBox="0 0 104 58" className="w-28">
        {/* Track */}
        <path
          d={arcPath(1)}
          fill="none"
          stroke="#1e293b"
          strokeWidth={10}
          strokeLinecap="round"
        />
        {/* Fill */}
        <path
          d={arcPath(pct)}
          fill="none"
          stroke={strokeColor}
          strokeWidth={10}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.7s, d 0.7s" }}
        />
        {/* Value */}
        <text x={CX} y={CY - 3} textAnchor="middle" fontSize={14} fill="white" fontWeight="bold">
          {avg.toFixed(0)}
        </text>
        <text x={CX} y={CY + 10} textAnchor="middle" fontSize={7.5} fill="#94a3b8">
          cm/s
        </text>
      </svg>
      <p className="text-xs text-slate-400">Vel. media</p>
      <p className="text-xs text-slate-500">Máx {max.toFixed(0)} cm/s</p>
    </div>
  );
}
