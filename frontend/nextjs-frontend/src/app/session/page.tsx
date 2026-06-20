import { Suspense } from "react";

import SessionClientPage from "./SessionClientPage";

export default function SessionPage() {
  return (
    <Suspense fallback={<main className="min-h-screen w-full px-6 py-8 text-sm text-slate-300 md:px-10">Cargando dashboard...</main>}>
      <SessionClientPage />
    </Suspense>
  );
}
