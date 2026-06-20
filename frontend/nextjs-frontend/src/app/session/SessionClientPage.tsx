"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { buildSessionRoute } from "./sessionNavigation";

export default function SessionClientPage() {
  const router = useRouter();
  const params = useSearchParams();
  const sessionId = params.get("sessionId");

  useEffect(() => {
    router.replace(buildSessionRoute("analytics", "history", sessionId));
  }, [router, sessionId]);

  return (
    <main className="min-h-screen w-full px-6 py-8 text-sm text-slate-300 md:px-10">
      Redirigiendo dashboard...
    </main>
  );
}
