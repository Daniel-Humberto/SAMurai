"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { GlobalHeader } from "@/app/components/GlobalHeader";
import { buildSessionRoute } from "@/app/session/sessionNavigation";
import { listHistory, type SessionRecord } from "@/lib/api";

export default function HistoryPage() {
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listHistory().then(setSessions).catch((err) => setError(err instanceof Error ? err.message : "No se pudo cargar historial"));
  }, []);

  return (
    <main className="flex min-h-screen w-full flex-col gap-6 px-6 py-8 md:px-10">
      <GlobalHeader />
      <header className="mt-2 flex items-end justify-between gap-4">
        <div>
          <p className="panel-kicker">Historial</p>
          <h1 className="panel-title">Sesiones guardadas</h1>
        </div>
      </header>
      {error ? <p className="text-sm text-rose-600">{error}</p> : null}
      <section className="grid gap-5 md:grid-cols-2">
        {sessions.length === 0 ? (
          <div className="rounded-[1.75rem] border border-slate-800 bg-slate-950/70 p-6 text-sm text-slate-300 shadow-[0_18px_60px_rgba(2,6,23,0.35)]">
            No hay sesiones completadas todavia.
          </div>
        ) : null}
        {sessions.map((session) => (
          <Link
            key={session.id}
            href={buildSessionRoute("analytics", "history", session.id)}
            className="rounded-[1.75rem] border border-slate-800 bg-slate-950/70 p-6 shadow-[0_18px_60px_rgba(2,6,23,0.35)] transition hover:-translate-y-1"
          >
            <div className="flex items-center justify-between">
              <h2 className="font-display text-4xl uppercase text-slate-100">{session.mode}</h2>
              <span className="badge-neutral">{session.status}</span>
            </div>
            <p className="mt-4 text-lg font-semibold text-slate-100">{session.source_path ?? session.id}</p>
            <p className="mt-3 text-sm leading-7 text-slate-300">Inicio: {new Date(session.started_at).toLocaleString()}</p>
          </Link>
        ))}
      </section>
    </main>
  );
}
