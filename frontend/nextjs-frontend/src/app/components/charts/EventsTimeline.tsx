import type { EventRecord } from "@/lib/api";

const EVENT_COLOR: Record<string, string> = {
  pase:          "#38bdf8",
  pass:          "#38bdf8",
  tiro:          "#f87171",
  gol:           "#facc15",
  goal:          "#facc15",
  intercepcion:  "#a78bfa",
  interception:  "#a78bfa",
  colision:      "#fb923c",
  collision:     "#fb923c",
};

function evColor(type: string) {
  return EVENT_COLOR[type.toLowerCase()] ?? "#94a3b8";
}

type Props = {
  events: EventRecord[];
  duration?: number;
};

export function EventsTimeline({ events, duration }: Props) {
  const maxT = Math.max(duration ?? 0, ...events.map(e => e.timestamp_s), 1);
  const W = 560;
  const H = 72;
  const PAD = 20;
  const trackY = H / 2;
  const trackW = W - PAD * 2;
  const toX = (t: number) => PAD + (t / maxT) * trackW;

  const byType: Record<string, number> = {};
  for (const ev of events) {
    byType[ev.event_type] = (byType[ev.event_type] ?? 0) + 1;
  }

  return (
    <div className="space-y-3">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        {/* Track */}
        <line
          x1={PAD} y1={trackY} x2={W - PAD} y2={trackY}
          stroke="#1e293b" strokeWidth={3} strokeLinecap="round"
        />

        {/* Time ticks */}
        {[0, 0.25, 0.5, 0.75, 1].map(t => {
          const x = toX(t * maxT);
          return (
            <g key={t}>
              <line x1={x} y1={trackY - 5} x2={x} y2={trackY + 5} stroke="#334155" strokeWidth={1} />
              <text x={x} y={H - 3} textAnchor="middle" fontSize={7.5} fill="#475569">
                {(t * maxT).toFixed(0)}s
              </text>
            </g>
          );
        })}

        {/* Events */}
        {events.map((ev, i) => {
          const x = toX(ev.timestamp_s);
          const c = evColor(ev.event_type);
          const above = i % 2 === 0;
          return (
            <g key={i}>
              <line
                x1={x} y1={above ? trackY - 16 : trackY}
                x2={x} y2={above ? trackY : trackY + 16}
                stroke={c} strokeWidth={1.5}
              />
              <circle cx={x} cy={trackY} r={4.5} fill={c} />
              <text
                x={x}
                y={above ? trackY - 19 : trackY + 24}
                textAnchor="middle"
                fontSize={7}
                fill={c}
              >
                {ev.event_type}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Legend pills */}
      {Object.entries(byType).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(byType).map(([type, count]) => (
            <span
              key={type}
              className="rounded-full px-2.5 py-0.5 text-xs font-medium"
              style={{
                background: `${evColor(type)}22`,
                color: evColor(type),
                border: `1px solid ${evColor(type)}44`,
              }}
            >
              {type} × {count}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
