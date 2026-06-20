"use client";

import { useEffect, useRef, useState } from "react";

type LiveCameraPreviewProps = {
  className?: string;
  description?: string;
  shouldRequestOnMount?: boolean;
};

export function LiveCameraPreview({
  className,
  description = "Preview local de la camara activa en este navegador.",
  shouldRequestOnMount = true,
}: LiveCameraPreviewProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">(
    shouldRequestOnMount ? "loading" : "idle",
  );
  const [error, setError] = useState<string | null>(null);

  const bindStreamToVideo = () => {
    if (!videoRef.current || !streamRef.current) return;
    if (videoRef.current.srcObject !== streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
    void videoRef.current.play().catch(() => {});
  };

  const setVideoNode = (node: HTMLVideoElement | null) => {
    videoRef.current = node;
    bindStreamToVideo();
  };

  const stopStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  };

  const requestCamera = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus("error");
      setError("Este navegador no soporta acceso a camara.");
      return;
    }

    stopStream();
    setStatus("loading");
    setError(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: "environment",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      });

      streamRef.current = stream;
      bindStreamToVideo();
      sessionStorage.setItem("samurai-live-camera-enabled", "true");
      setStatus("ready");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "No se pudo abrir la camara.");
    }
  };

  useEffect(() => {
    if (!shouldRequestOnMount) return;
    requestCamera();

    return () => {
      stopStream();
    };
  }, [shouldRequestOnMount]);

  useEffect(() => {
    if (status === "ready") {
      bindStreamToVideo();
    }
  }, [status]);

  return (
    <div className={className}>
      <div className="grid aspect-video overflow-hidden rounded-[1.25rem] border border-cyan-300/15 bg-[radial-gradient(circle_at_center,_rgba(56,189,248,0.16),_rgba(3,7,18,0.94))]">
        {status === "ready" ? (
          <video ref={setVideoNode} className="h-full w-full bg-black object-cover" autoPlay muted playsInline />
        ) : (
          <div className="grid place-items-center px-6 text-center">
            <div>
              <p className="text-sm uppercase tracking-[0.5em] text-cyan-100/70">
                {status === "loading" ? "Abriendo camara" : "Camara no disponible"}
              </p>
              <p className="mt-4 text-sm leading-7 text-cyan-50/90">{error ?? description}</p>
              <button type="button" onClick={requestCamera} className="button-secondary mt-5">
                {status === "loading" ? "solicitando" : "reintentar camara"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
