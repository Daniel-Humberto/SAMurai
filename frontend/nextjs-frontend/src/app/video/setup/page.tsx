"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { GlobalHeader } from "@/app/components/GlobalHeader";
import { buildSessionRoute } from "@/app/session/sessionNavigation";
import { uploadVideo } from "@/lib/api";

export default function VideoSetupPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!file) {
      setError("Selecciona un archivo de video primero.");
      return;
    }
    setIsUploading(true);
    setError(null);
    try {
      const result = await uploadVideo(file);
      router.push(buildSessionRoute("analytics", "video", result.session.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo subir el video");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <main className="flex min-h-screen w-full flex-col gap-6 px-6 py-10">
      <GlobalHeader />
      <div className="panel-shell">
        <p className="panel-kicker">Video Setup</p>
        <h1 className="panel-title">Analisis batch de partido</h1>
        <div className="mt-6 rounded-[1.5rem] border border-dashed border-slate-700 bg-slate-900/70 p-8 text-center">
          <p className="text-sm uppercase tracking-[0.35em] text-slate-400">Subida real</p>
          <p className="mt-3 text-sm leading-7 text-slate-300">
            El backend recibira el video, lo persistira en disco y disparara procesamiento real en background.
          </p>
          <input
            type="file"
            accept="video/*"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="mt-6 block w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-3 text-sm text-slate-200"
          />
          {file ? <p className="mt-3 text-sm text-slate-300">Archivo: {file.name}</p> : null}
          {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
        </div>
        <div className="mt-6 flex gap-3">
          <button type="button" onClick={handleSubmit} disabled={isUploading} className="button-primary disabled:opacity-50">
            {isUploading ? "subiendo" : "procesar video"}
          </button>
          <Link href="/" className="button-secondary">
            Cancelar
          </Link>
        </div>
      </div>
    </main>
  );
}
