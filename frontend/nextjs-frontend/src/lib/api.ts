export type SessionStatus = "active" | "processing" | "completed" | "failed";

export type SessionRecord = {
  id: string;
  mode: "live" | "video";
  source_path: string | null;
  started_at: string;
  ended_at: string | null;
  homography_matrix: Record<string, unknown> | null;
  status: SessionStatus;
};

export type EventRecord = {
  id?: string;
  frame_idx: number;
  timestamp_s: number;
  event_type: string;
  narration_text?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type TrajectoryRecord = {
  frame_idx: number;
  object_id: number;
  object_class: string | null;
  x_cm: number | null;
  y_cm: number | null;
  area_px: number | null;
  predicted_x_cm: number | null;
  predicted_y_cm: number | null;
};

export type SessionSummary = {
  session: SessionRecord;
  pipeline: { stages: Array<Record<string, unknown>> };
  metrics_snapshot: Record<string, number | string>;
  pending_events: EventRecord[];
  media_info: Record<string, number | string>;
  progress_pct: number;
  stage: string;
  recent_trajectories: TrajectoryRecord[];
};

export type ReportDetail = {
  session: SessionRecord;
  report: {
    id: string;
    session_id: string;
    summary_text: string | null;
    pdf_path: string | null;
    stats: Record<string, number | string> | null;
    created_at: string;
  } | null;
  events: EventRecord[];
  trajectories: TrajectoryRecord[];
};

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getSessionSourceUrl(sessionId: string) {
  return `${API_BASE}/sessions/${sessionId}/source`;
}

export function getSessionAudioUrl(sessionId: string) {
  return `${API_BASE}/sessions/${sessionId}/audio`;
}

export function getEventAudioUrl(sessionId: string, eventId: string) {
  return `${API_BASE}/sessions/${sessionId}/events/${eventId}/audio`;
}

export function getReportArtifactUrl(sessionId: string) {
  return `${API_BASE}/sessions/${sessionId}/artifact`;
}

export function listSessions() {
  return request<SessionRecord[]>("/sessions");
}

export function listHistory() {
  return request<SessionRecord[]>("/sessions/history");
}

export function getSession(sessionId: string) {
  return request<SessionSummary>(`/sessions/${sessionId}`);
}

export function getReport(sessionId: string) {
  return request<ReportDetail>(`/sessions/${sessionId}/report`);
}

export function createLiveSession() {
  return request<SessionRecord>("/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "live", source_path: "live://manual" }),
  });
}

export async function uploadVideo(file: File) {
  const form = new FormData();
  form.append("file", file);
  form.append("mode", "video");
  return request<{ session: SessionRecord; upload_path: string }>("/sessions/upload", {
    method: "POST",
    body: form,
  });
}

export function finalizeSession(sessionId: string) {
  return request<SessionRecord>(`/sessions/${sessionId}/finalize`, {
    method: "POST",
  });
}
