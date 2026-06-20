import { ExoticFieldExperience } from "./ExoticFieldExperience";

export function SamuraiHero() {
  return (
    <section className="relative overflow-hidden rounded-t-[2rem] border-t border-x border-white/10 bg-[radial-gradient(circle_at_top,_rgba(245,158,11,0.18),_transparent_36%),linear-gradient(135deg,_rgba(17,24,39,0.96),_rgba(4,11,24,0.98))] p-8 pb-14 md:pb-20 shadow-[0_30px_100px_rgba(0,0,0,0.35)] flex-grow flex flex-col justify-center min-h-[450px] lg:min-h-[520px]">
      <div className="absolute inset-y-0 right-0 w-1/2 bg-[linear-gradient(180deg,transparent,rgba(245,158,11,0.08),transparent)]" />
      <div className="relative grid gap-8 lg:grid-cols-[1.2fr_1fr] items-center h-full">
        <div className="space-y-6">
          <span className="inline-flex rounded-full border border-amber-400/30 bg-amber-300/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.35em] text-amber-200">
            Vision + Tactica + LLM
          </span>
          <div className="space-y-4">
            <p className="font-display text-6xl uppercase leading-none text-white md:text-8xl">
              SAMurAI
            </p>
            <p className="font-display text-4xl uppercase leading-none text-amber-300 md:text-6xl">
              FutBotMX
            </p>
          </div>
          <p className="max-w-2xl text-base leading-7 text-slate-300 md:text-lg">
            Plataforma unificada para segmentacion SAM, tracking persistente,
            homografia, heatmaps, forecasting y narracion tactica en vivo para
            futbol robotico.
          </p>
          <div className="flex flex-wrap gap-3 text-sm text-slate-200">
            <span className="rounded-full border border-cyan-400/20 bg-cyan-300/10 px-3 py-1">
              YOLOv8n + SAM2.1
            </span>
            <span className="rounded-full border border-sky-400/20 bg-sky-300/10 px-3 py-1">
              ByteTrack
            </span>
            <span className="rounded-full border border-emerald-400/20 bg-emerald-300/10 px-3 py-1">
              FastAPI + Next.js
            </span>
          </div>
        </div>
        <div className="w-full flex items-center justify-center">
          <ExoticFieldExperience />
        </div>
      </div>
    </section>
  );
}

