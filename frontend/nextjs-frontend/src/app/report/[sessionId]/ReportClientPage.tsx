"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getReport, getReportArtifactUrl, type ReportDetail } from "@/lib/api";
import { GlobalHeader } from "@/app/components/GlobalHeader";
import { buildSessionRoute } from "@/app/session/sessionNavigation";

const sanitizeNarrationText = (text: string | null | undefined) =>
  text ? text.replace(/^\s*\[[^\]]+\]\s*/, "").trim() : "";

type ReportClientPageProps = {
  sessionId: string;
};

export default function ReportClientPage({ sessionId }: ReportClientPageProps) {
  const [detail, setDetail] = useState<ReportDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    getReport(sessionId).then(setDetail).catch((err) => setError(err instanceof Error ? err.message : "No se pudo cargar el reporte"));
  }, [sessionId]);

  const statsEntries = Object.entries(detail?.report?.stats ?? {});
  const artifactUrl = getReportArtifactUrl(sessionId);

  return (
    <main className="flex min-h-screen w-full flex-col gap-6 px-6 py-8 md:px-10">
      <GlobalHeader />
      <header className="rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,_rgba(15,23,42,0.96),_rgba(3,105,161,0.9))] p-7 text-white">
        <p className="text-xs uppercase tracking-[0.45em] text-cyan-200">Informe ejecutivo</p>
        <h1 className="mt-3 font-display text-6xl uppercase">{sessionId}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-200">
          Resumen persistido de eventos, trayectorias y metricas finales de la sesion con exportacion de artefacto en PDF.
        </p>
      </header>

      {error ? <p className="text-sm text-rose-600">{error}</p> : null}

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="panel-shell">
          <p className="panel-kicker">Summary</p>
          <h2 className="panel-title">Lectura tactica final</h2>
          <p className="mt-5 text-sm leading-8 text-slate-200">
            {sanitizeNarrationText(detail?.report?.summary_text) || "El reporte aparecera aqui cuando termine el procesamiento."}
          </p>
          <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3">
            {statsEntries.slice(0, 6).map(([key, value]) => (
              <div key={key} className="rounded-2xl bg-slate-950 p-4 text-white">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">{key}</p>
                <p className="mt-3 font-display text-3xl uppercase">{String(value)}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="panel-shell">
          <p className="panel-kicker">Timeline</p>
          <h2 className="panel-title">Cronologia de eventos</h2>
          <div className="mt-5 space-y-3">
            {(detail?.events ?? []).length === 0 ? (
              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-200">
                Todavia no hay eventos persistidos para esta sesion.
              </div>
            ) : null}
            {(detail?.events ?? []).map((item) => (
              <div
                key={`${item.event_type}-${item.frame_idx}-${item.timestamp_s}`}
                className="rounded-2xl border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-200"
              >
                {item.timestamp_s.toFixed(2)}s · {item.event_type} · {sanitizeNarrationText(item.narration_text) || "evento detectado"}
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="flex flex-wrap gap-3">
        <Link href="/history" className="button-secondary">Volver al historial</Link>
        <Link href={buildSessionRoute("analytics", "history", sessionId)} className="button-secondary">Abrir dashboard final</Link>
        {detail?.report ? (
          <a href={artifactUrl} className="button-primary" target="_blank" rel="noreferrer" download>
            Exportar artefacto PDF
          </a>
        ) : null}
      </div>
    </main>
  );
}
