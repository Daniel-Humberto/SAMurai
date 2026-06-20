"use client";

import { SamuraiBadge } from "./SamuraiBadge";

export function GlobalHeader() {
  return (
    <header className="flex flex-col sm:flex-row items-center sm:text-left text-center gap-4 sm:gap-6 w-full border-b border-white/5 pb-4 mb-4">
      <SamuraiBadge />
      <div className="space-y-1">
        <h1 className="font-display text-2xl md:text-3xl lg:text-4xl uppercase tracking-[0.22em] text-slate-100">
          SAMurAI FutBotMX
        </h1>
        <p className="max-w-2xl text-xs md:text-sm leading-relaxed text-slate-300">
          Analitica deportiva robotica unificada para demo, scouting y narrativa ejecutiva.
        </p>
      </div>
    </header>
  );
}
