"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { buildSessionRoute, type SessionModeView } from "@/app/session/sessionNavigation";
import { finalizeSession, getReportArtifactUrl } from "@/lib/api";

type SessionControlsProps = {
  sessionId: string | null;
  sessionStatus?: string;
  sessionMode: SessionModeView;
};

export function SessionControls({ sessionId, sessionStatus, sessionMode }: SessionControlsProps) {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isProcessing = sessionStatus === "processing";
  const isCompleted = sessionStatus === "completed";
  const artifactUrl = sessionId ? getReportArtifactUrl(sessionId) : null;

  const handleFinalize = async () => {
    if (!sessionId || isProcessing) return;
    setIsSubmitting(true);
    try {
      await finalizeSession(sessionId);
      router.push(buildSessionRoute("analytics", sessionMode, sessionId));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-[1.75rem] border border-slate-800 bg-slate-950/70 p-5 shadow-[0_18px_60px_rgba(2,6,23,0.35)]">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Session Controls</p>
        <p className="mt-2 text-sm text-slate-300">
          Estado actual: {sessionStatus ?? "sin sesion"}. {isCompleted
            ? "Estas viendo el dashboard final persistido de la sesion y ya puedes exportar el artefacto PDF desde la web."
            : isProcessing
              ? "Espera a que termine el procesamiento para congelar un dashboard consistente."
              : "Finaliza para congelar el dashboard y consolidar la telemetria."}
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        {isCompleted && sessionId ? (
          <>
            <Link href={buildSessionRoute("analytics", sessionMode, sessionId)} className="button-primary">
              dashboard final
            </Link>
            <Link href={`/report/${sessionId}`} className="button-secondary">
              ver reporte
            </Link>
            {artifactUrl ? (
              <a href={artifactUrl} className="button-secondary" target="_blank" rel="noreferrer" download>
                exportar PDF
              </a>
            ) : null}
          </>
        ) : (
          <button
            type="button"
            disabled={!sessionId || isSubmitting || isProcessing}
            onClick={handleFinalize}
            className="button-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? "cerrando" : isProcessing ? "procesando" : "finalizar sesion"}
          </button>
        )}
        <Link href="/" className="button-secondary">
          Volver
        </Link>
      </div>
    </div>
  );
}
