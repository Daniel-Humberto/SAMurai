import { getSessionAudioUrl, getEventAudioUrl, type SessionSummary } from "@/lib/api";

const sanitizeNarrationText = (text: string | null | undefined) =>
  text ? text.replace(/^\s*\[[^\]]+\]\s*/, "").trim() : "";

type NarrationPanelProps = {
  summary: SessionSummary | null;
};

export function NarrationPanel({ summary }: NarrationPanelProps) {
  const feed = summary?.pending_events ?? [];

  const playAudio = (url: string) => {
    const audio = new Audio(url);
    audio.play().catch((err) => {
      console.error("Error playing narration audio:", err);
    });
  };

  return (
    <section className="panel-shell">
      <div className="flex items-center justify-between">
        <div>
          <p className="panel-kicker">Narracion</p>
          <h2 className="panel-title">Ticker tactico + TTS local</h2>
        </div>
        <span className="badge-neutral">{feed.length} eventos</span>
      </div>
      <div className="mt-5 grid gap-4">
        <div className="rounded-[1.5rem] border border-slate-800 bg-slate-900/70 p-5">
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Feed de eventos</p>
          <div className="mt-4 space-y-3">
            {feed.length === 0 ? (
              <div className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-sm text-slate-200">
                Sin eventos todavia. El backend publicara pases, intercepciones, colisiones y goles cuando el procesamiento avance.
              </div>
            ) : null}
            {feed.map((item) => (
              <div
                key={`${item.event_type}-${item.frame_idx}-${item.timestamp_s}`}
                className="flex items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-sm text-slate-200"
              >
                <div className="flex-1">
                  <span className="font-semibold text-amber-400">{item.timestamp_s.toFixed(2)}s</span>
                  <span className="mx-2 text-slate-500">·</span>
                  <span className="capitalize font-medium text-slate-300">{item.event_type}</span>
                  <span className="mx-2 text-slate-500">·</span>
                  <span className="text-slate-100">{sanitizeNarrationText(item.narration_text) || "evento detectado"}</span>
                </div>
                {summary?.session?.id && item.id && (
                  <button
                    onClick={() => playAudio(getEventAudioUrl(summary.session.id, item.id!))}
                    title="Escuchar narración de evento"
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                      <path d="M13.5 4.06c0-1.336-1.616-2.005-2.56-1.06l-4.5 4.5H4.508c-1.141 0-2.063.922-2.063 2.063v4.875c0 1.141.922 2.062 2.063 2.062h1.932l4.5 4.5c.944.945 2.56.276 2.56-1.06V4.06zM18.57 17.47a.75.75 0 11-1.06 1.06 8.25 8.25 0 000-11.66.75.75 0 111.06 1.06 6.75 6.75 0 010 9.54zm-2.83-2.83a.75.75 0 11-1.06 1.06 3.75 3.75 0 000-5.3.75.75 0 111.06 1.06 2.25 2.25 0 010 3.18z" />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-[1.5rem] bg-slate-950 p-5 text-white">
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Audio local</p>
          <div className="mt-4 flex items-center justify-between rounded-2xl border border-white/10 bg-slate-900/60 px-4 py-3">
            <div className="flex flex-col">
              <span className="text-xs text-slate-400">Modelo</span>
              <span className="text-sm text-slate-200">Voz local MX</span>
            </div>
            {summary?.session?.id && (
              <button
                onClick={() => playAudio(getSessionAudioUrl(summary.session.id))}
                className="flex items-center gap-2 rounded-xl bg-amber-400 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-950 hover:bg-amber-300 transition-colors shadow-lg shadow-amber-400/20"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                  <path fillRule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.348c1.295.712 1.295 2.573 0 3.285L7.28 19.991c-1.25.687-2.779-.217-2.779-1.643V5.653z" clipRule="evenodd" />
                </svg>
                Escuchar Reporte
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

