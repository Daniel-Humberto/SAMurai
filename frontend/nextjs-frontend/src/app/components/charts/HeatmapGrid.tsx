import type { TrajectoryRecord } from "@/lib/api";

const COLS = 12;
const ROWS = 8;

type Props = {
  trajectories: TrajectoryRecord[];
  team?: "azul" | "rojo" | null;
};

export function HeatmapGrid({ trajectories, team }: Props) {
  const grid = new Array<number>(ROWS * COLS).fill(0);

  const pts = trajectories.filter(p => p.x_cm != null && p.y_cm != null);
  const xs = pts.map(p => p.x_cm!);
  const ys = pts.map(p => p.y_cm!);
  const minX = xs.length ? Math.min(...xs) : 0;
  const maxX = xs.length ? Math.max(...xs) : 182;
  const minY = ys.length ? Math.min(...ys) : 0;
  const maxY = ys.length ? Math.max(...ys) : 243;
  const rangeX = maxX - minX || 1;
  const rangeY = maxY - minY || 1;

  for (const pt of pts) {
    if (team && pt.object_class !== team) continue;
    const col = Math.min(COLS - 1, Math.floor(((pt.x_cm! - minX) / rangeX) * COLS));
    const row = Math.min(ROWS - 1, Math.floor(((pt.y_cm! - minY) / rangeY) * ROWS));
    grid[row * COLS + col]++;
  }

  const maxVal = Math.max(...grid, 1);
  const rgb = team === "rojo" ? "248,113,113" : team === "azul" ? "56,189,248" : "245,158,11";

  return (
    <div className="grid gap-0.5" style={{ gridTemplateColumns: `repeat(${COLS}, 1fr)` }}>
      {grid.map((val, i) => (
        <div
          key={i}
          className="aspect-square rounded-sm transition-all duration-700"
          style={{ background: `rgba(${rgb}, ${0.04 + (val / maxVal) * 0.92})` }}
        />
      ))}
    </div>
  );
}
