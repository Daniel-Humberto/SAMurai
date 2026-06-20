import { notFound } from "next/navigation";
import { Suspense } from "react";

import { SessionWorkspacePage } from "../../SessionWorkspacePage";
import { isSessionModeView, isSessionPanel } from "../../sessionNavigation";

type SessionWorkspaceRouteProps = {
  params: Promise<{
    panel: string;
    mode: string;
  }>;
};

export default async function SessionWorkspaceRoute({ params }: SessionWorkspaceRouteProps) {
  const { panel, mode } = await params;

  if (!isSessionPanel(panel) || !isSessionModeView(mode)) {
    notFound();
  }

  return (
    <Suspense fallback={<main className="min-h-screen w-full px-6 py-8 text-sm text-slate-300 md:px-10">Cargando dashboard...</main>}>
      <SessionWorkspacePage panel={panel} mode={mode} />
    </Suspense>
  );
}
