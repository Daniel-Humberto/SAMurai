"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { GlobalHeader } from "@/app/components/GlobalHeader";
import { LiveCameraPreview } from "@/app/components/LiveCameraPreview";
import { buildSessionRoute } from "@/app/session/sessionNavigation";
import { createLiveSession } from "@/lib/api";

export default function LiveSetupPage() {
  const router = useRouter();
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStart = async () => {
    setIsStarting(true);
    setError(null);
    try {
      const session = await createLiveSession();
      router.push(buildSessionRoute("analytics", "live", session.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo iniciar la sesion live");
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <main className="flex min-h-screen w-full flex-col gap-6 px-6 py-10">
      <GlobalHeader />
      <div className="panel-shell">
        <p className="panel-kicker">Live Setup</p>
        <h1 className="panel-title">Fuente de camara o RTSP</h1>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-300">
          Esta vista ahora solicita acceso real a la camara del navegador antes de arrancar la sesion live.
        </p>
        <div className="mt-6">
          <LiveCameraPreview description="Permite acceso a la camara para validar el feed local antes de entrar al dashboard live." />
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div className="rounded-[1.5rem] border border-slate-800 bg-slate-900/70 p-5">
            <p className="text-sm font-semibold text-slate-100">Camara USB</p>
            <p className="mt-2 text-sm leading-7 text-slate-300">
              Se abre un preview local con `getUserMedia()` para validar permisos y disponibilidad del dispositivo.
            </p>
          </div>
          <div className="rounded-[1.5rem] border border-slate-800 bg-slate-900/70 p-5">
            <p className="text-sm font-semibold text-slate-100">Stream RTSP</p>
            <p className="mt-2 text-sm leading-7 text-slate-300">
              Sigue pendiente conectar ingest real RTSP al backend. Esta correccion cubre el caso de camara del navegador.
            </p>
          </div>
        </div>
        {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}
        <div className="mt-6 flex gap-3">
          <button type="button" onClick={handleStart} disabled={isStarting} className="button-primary disabled:opacity-50">
            {isStarting ? "iniciando" : "iniciar sesion live"}
          </button>
          <Link href="/" className="button-secondary">
            Cancelar
          </Link>
        </div>
      </div>
    </main>
  );
}
