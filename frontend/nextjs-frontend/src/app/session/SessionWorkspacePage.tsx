"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { GlobalHeader } from "@/app/components/GlobalHeader";
import { getSession, listHistory, type SessionRecord, type SessionSummary } from "@/lib/api";

import { AnalyticsPanel } from "./components/AnalyticsPanel";
import { ForecastPanel } from "./components/ForecastPanel";
import { NarrationPanel } from "./components/NarrationPanel";
import { SessionControls } from "./components/SessionControls";
import {
  buildSessionRoute,
  SESSION_MODE_META,
  SESSION_PANEL_META,
  SESSION_PANELS,
  type SessionModeView,
  type SessionPanel,
} from "./sessionNavigation";

type SessionWorkspacePageProps = {
  panel: SessionPanel;
  mode: SessionModeView;
};

export function SessionWorkspacePage({ panel, mode }: SessionWorkspacePageProps) {
  const params = useSearchParams();
  const sessionId = params.get("sessionId");
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [historySessions, setHistorySessions] = useState<SessionRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== "history") return;

    let cancelled = false;
    listHistory()
      .then((data) => {
        if (!cancelled) {
          setHistorySessions(data);
          setHistoryError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setHistoryError(err instanceof Error ? err.message : "No se pudo cargar historial");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [mode]);

  useEffect(() => {
    if (!sessionId) {
      setSummary(null);
      return;
    }

    let cancelled = false;
    let timer: number | undefined;

    const load = async () => {
      try {
        const data = await getSession(sessionId);
        if (!cancelled) {
          setSummary(data);
          setError(null);
          if (mode !== "history" && data.session.status !== "completed") {
            timer = window.setTimeout(load, 2500);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "No se pudo cargar la sesion");
          if (mode !== "history") {
            timer = window.setTimeout(load, 4000);
          }
        }
      }
    };

    load();

    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [mode, sessionId]);

  const sessionStatus = summary?.session.status;
  const panelMeta = SESSION_PANEL_META[panel];
  const modeMeta = SESSION_MODE_META[mode];
  const dashboardLabel = `${panelMeta.label} · ${modeMeta.label}`;
  const dashboardDescription = `${panelMeta.description} ${modeMeta.description}`;

  const renderPanel = () => {
    if (panel === "analytics") return <AnalyticsPanel summary={summary} />;
    if (panel === "forecast") return <ForecastPanel summary={summary} />;
    return <NarrationPanel summary={summary} />;
  };

  return (
    <main className="flex min-h-screen w-full flex-col gap-6 px-6 py-8 md:px-10">
      <GlobalHeader />

      <header className="rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,_rgba(15,23,42,0.96),_rgba(30,41,59,0.92))] p-7 text-white shadow-[0_25px_90px_rgba(15,23,42,0.28)]">
        <p className="text-xs uppercase tracking-[0.45em] text-amber-300">{dashboardLabel}</p>
        <h1 className="mt-3 font-display text-6xl uppercase">FutBotMX Match Ops</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300">{dashboardDescription}</p>
        <p className="mt-4 text-sm text-slate-300">
          {sessionId
            ? `Sesion: ${sessionId}`
            : mode === "history"
              ? "Selecciona una sesion guardada para abrir esta vista."
              : `Abre una sesion ${modeMeta.label.toLowerCase()} para activar este tablero.`}
        </p>
        {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}
      </header>

      <nav className="flex flex-wrap gap-3 rounded-[1.5rem] border border-slate-800 bg-slate-950/60 p-4">
        {SESSION_PANELS.map((item) => {
          const meta = SESSION_PANEL_META[item];
          const active = item === panel;
          return (
            <Link
              key={item}
              href={buildSessionRoute(item, mode, sessionId)}
              className={active ? "button-primary" : "button-secondary"}
            >
              {meta.label}
            </Link>
          );
        })}
      </nav>

      {mode === "history" ? (
        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="panel-shell">
            <div className="flex items-center justify-between">
              <div>
                <p className="panel-kicker">History</p>
                <h2 className="panel-title">Casos disponibles</h2>
              </div>
              <span className="badge-neutral">{historySessions.length} sesiones</span>
            </div>
            {historyError ? <p className="mt-4 text-sm text-rose-300">{historyError}</p> : null}
            <div className="mt-5 grid gap-4">
              {historySessions.length === 0 ? (
                <div className="rounded-[1.5rem] border border-slate-800 bg-slate-950/70 p-5 text-sm text-slate-300">
                  No hay sesiones completadas todavia.
                </div>
              ) : null}
              {historySessions.map((session) => (
                <Link
                  key={session.id}
                  href={buildSessionRoute(panel, "history", session.id)}
                  className={`rounded-[1.5rem] border p-5 transition hover:-translate-y-1 ${
                    session.id === sessionId
                      ? "border-amber-300 bg-amber-300/10"
                      : "border-slate-800 bg-slate-950/70"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="font-display text-3xl uppercase text-slate-100">{session.mode}</h3>
                    <span className="badge-neutral">{session.status}</span>
                  </div>
                  <p className="mt-3 text-sm font-semibold text-slate-100">{session.source_path ?? session.id}</p>
                  <p className="mt-2 text-sm leading-7 text-slate-300">
                    Inicio: {new Date(session.started_at).toLocaleString()}
                  </p>
                </Link>
              ))}
            </div>
          </div>
          <div className="grid gap-6">
            {renderPanel()}
            <SessionControls sessionId={sessionId} sessionStatus={sessionStatus} sessionMode={mode} />
          </div>
        </section>
      ) : (
        <>
          {renderPanel()}
          <SessionControls sessionId={sessionId} sessionStatus={sessionStatus} sessionMode={mode} />
        </>
      )}
    </main>
  );
}
