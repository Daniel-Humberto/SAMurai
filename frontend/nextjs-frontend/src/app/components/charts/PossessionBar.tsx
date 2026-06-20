type Props = {
  blue: number;
  red: number;
  neutral?: number;
};

export function PossessionBar({ blue, red, neutral = 0 }: Props) {
  const total = blue + red + neutral || 100;
  const bPct = (blue / total) * 100;
  const rPct = (red / total) * 100;
  const nPct = (neutral / total) * 100;

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="font-medium text-sky-400">Azul {blue.toFixed(1)}%</span>
        {neutral > 0.5 && <span className="text-slate-500">Disputa {neutral.toFixed(1)}%</span>}
        <span className="font-medium text-red-400">Rojo {red.toFixed(1)}%</span>
      </div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-900">
        <div
          className="rounded-l-full bg-sky-500 transition-all duration-700"
          style={{ width: `${bPct}%` }}
        />
        {nPct > 0.5 && (
          <div className="bg-slate-600 transition-all duration-700" style={{ width: `${nPct}%` }} />
        )}
        <div
          className="rounded-r-full bg-red-500 transition-all duration-700"
          style={{ width: `${rPct}%` }}
        />
      </div>
    </div>
  );
}
