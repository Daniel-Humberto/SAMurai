"use client";

import Link from "next/link";

export function SamuraiBadge() {
  return (
    <Link
      href="/"
      className="group relative flex items-center justify-center w-14 h-14 md:w-16 md:h-16 flex-shrink-0 transition-transform duration-300 hover:scale-105 active:scale-95"
      title="SAMurAI FutBotMX Home"
    >
      {/* Outer ambient glow */}
      <div className="absolute inset-0 rounded-full bg-amber-400/10 blur-xl transition-all duration-300 group-hover:bg-amber-400/20 group-hover:blur-2xl" />

      {/* Outer thin rings */}
      <div className="absolute inset-1.5 rounded-full border border-cyan-300/10 transition-colors duration-300 group-hover:border-cyan-300/30" />
      <div className="absolute -inset-0.5 rounded-full border border-white/5" />

      {/* Main badge container */}
      <div className="relative grid w-full h-full place-items-center rounded-full border border-white/10 bg-slate-950/80 shadow-[inset_0_2px_8px_rgba(34,211,238,0.1),0_10px_35px_rgba(0,0,0,0.5)] transition-all duration-300 group-hover:border-amber-400/20 group-hover:shadow-[inset_0_2px_12px_rgba(245,158,11,0.2),0_15px_40px_rgba(0,0,0,0.6)]">
        {/* Rotating dash ring - spins slow by default, a bit faster on hover */}
        <div className="absolute inset-1 rounded-full border border-dashed border-amber-400/30 animate-spin-slow group-hover:border-amber-400/60" style={{ animationDuration: "16s" }} />
        
        {/* Inner solid ring */}
        <div className="absolute inset-2.5 rounded-full border border-cyan-400/20 group-hover:border-cyan-400/40" />

        {/* Center content */}
        <div className="text-center flex flex-col items-center justify-center z-10 px-2">
          <p className="font-display text-xl md:text-2xl leading-none text-white select-none drop-shadow-[0_2px_6px_rgba(255,255,255,0.25)] transition-all duration-300 group-hover:text-amber-300 group-hover:drop-shadow-[0_2px_10px_rgba(245,158,11,0.4)]">
            侍
          </p>
          <span className="text-[5px] md:text-[6px] uppercase tracking-[0.18em] text-slate-400 leading-none mt-0.5 font-bold transition-colors duration-300 group-hover:text-cyan-300">
            field intel
          </span>
        </div>
      </div>
    </Link>
  );
}
