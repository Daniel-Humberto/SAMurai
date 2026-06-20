from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.analytics.metrics import MetricsEngine
from app.core.memory_guard import MemoryGuard
from app.core.runtime_store import RuntimeStore
from app.core.state import SessionRuntimeState
from app.db.database import SessionLocal
from app.db.repository import SessionRepository
from app.reports.executive_report import ExecutiveReportService
from app.schemas import EventCreate, ReportCreate, SessionCreate


class SessionManager:
    def __init__(self):
        self._states: dict[UUID, SessionRuntimeState] = {}
        self._memory_guard = MemoryGuard()
        self._runtime_store = RuntimeStore()
        self._metrics = MetricsEngine()
        self._video_processor = None
        self._reports = ExecutiveReportService()

    def _describe_pipeline(self) -> dict:
        return {
            "stages": [
                {"component": "detector", "task": "bbox detection"},
                {"component": "tracker", "task": "ByteTrack tracking"},
                {"component": "segmenter", "task": "SAM segmentation"},
                {"component": "homography", "task": "field projection"},
            ]
        }

    def _get_video_processor(self):
        if self._video_processor is None:
            from app.ingestion.video_processor import VideoProcessor

            self._video_processor = VideoProcessor()
        return self._video_processor

    def start_session(self, db: Session, payload: SessionCreate, status: str = "active"):
        repo = SessionRepository(db)
        session = repo.create_session(payload, status=status)
        state = SessionRuntimeState(session_id=session.id, stage=status, progress_pct=0.0)
        self._states[session.id] = state
        self._persist_runtime(session.id)
        return session

    def attach_media_info(self, session_id: UUID, media_info: dict) -> None:
        state = self._states.get(session_id)
        if state is None:
            return
        state.set_media_info(media_info)
        self._persist_runtime(session_id)

    def list_active_states(self) -> list[dict]:
        return [state.snapshot() for state in self._states.values()]

    def get_runtime_state(self, session_id: UUID) -> SessionRuntimeState | None:
        return self._states.get(session_id)

    def get_session_summary(self, db: Session, session_id: UUID) -> dict:
        repo = SessionRepository(db)
        pipeline = self._describe_pipeline()
        state = self._states.get(session_id)
        if state is None:
            cached = self._runtime_store.load_snapshot(session_id) or {}
            report = repo.get_report(session_id)
            report_snapshot = report.dashboard_snapshot if report and report.dashboard_snapshot else {}
            trajectories = repo.list_trajectories(session_id, limit=120)
            session = repo.get_session(session_id)
            metrics_snapshot = (
                cached.get("metrics")
                or report_snapshot.get("metrics_snapshot")
                or (report.stats if report and report.stats else None)
                or self._metrics.bootstrap_metrics()
            )
            media_info = cached.get("media_info") or report_snapshot.get("media_info") or {}
            progress_pct = cached.get("progress_pct")
            if progress_pct is None:
                progress_pct = report_snapshot.get("progress_pct")
            if progress_pct is None:
                progress_pct = 100.0 if session and session.status == "completed" else 0.0
            stage = cached.get("stage") or report_snapshot.get("stage") or (session.status if session else "unknown")

            if report and not report.dashboard_snapshot:
                repo.upsert_report(
                    session_id,
                    ReportCreate(
                        summary_text=report.summary_text,
                        pdf_path=report.pdf_path,
                        stats=report.stats,
                        dashboard_snapshot={
                            "metrics_snapshot": metrics_snapshot,
                            "media_info": media_info,
                            "progress_pct": progress_pct,
                            "stage": stage,
                        },
                    ),
                )

            return {
                "pipeline": pipeline,
                "metrics_snapshot": metrics_snapshot,
                "pending_events": repo.list_events(session_id)[-10:],
                "media_info": media_info,
                "progress_pct": progress_pct,
                "stage": stage,
                "recent_trajectories": trajectories,
            }

        self._memory_guard.prune_state(state)
        state.set_metrics(self._metrics.compute_snapshot(state.telemetry))
        self._persist_runtime(session_id)
        return {
            "pipeline": pipeline,
            "metrics_snapshot": state.metrics,
            "pending_events": state.events[-10:],
            "media_info": state.media_info,
            "progress_pct": state.progress_pct,
            "stage": state.stage,
            "recent_trajectories": repo.list_trajectories(session_id, limit=120),
        }

    def register_event(self, db: Session, session_id: UUID, payload: EventCreate):
        repo = SessionRepository(db)
        event = repo.create_event(session_id, payload)
        state = self._states.get(session_id)
        if state is not None:
            state.push_event(
                {
                    "id": str(event.id),
                    "frame_idx": event.frame_idx,
                    "event_type": event.event_type,
                    "timestamp_s": event.timestamp_s,
                    "narration_text": event.narration_text,
                    "metadata": event.event_metadata,
                }
            )
            self._persist_runtime(session_id)
        return event

    def finalize_session(self, db: Session, session_id: UUID):
        repo = SessionRepository(db)
        session = repo.get_session(session_id)
        if session is None:
            return None
        if session.status == "processing":
            raise RuntimeError("Session is still processing")

        self._ensure_report_persisted(db, session_id)
        session = repo.complete_session(session_id)
        state = self._states.get(session_id)
        if state is not None:
            state.is_active = False
            state.set_stage("completed", 100.0)
            self._persist_runtime(session_id)
            self._memory_guard.release()
        return session

    def process_video_session(self, session_id: UUID, video_path: str) -> None:
        db = SessionLocal()
        repo = SessionRepository(db)
        state = self._states.setdefault(session_id, SessionRuntimeState(session_id=session_id))
        try:
            repo.update_session_status(session_id, "processing")
            state.set_stage("processing", 1.0)
            self._persist_runtime(session_id)

            def on_progress(frame_idx: int, progress_pct: float, telemetry: list[dict]) -> None:
                state.frame_idx = frame_idx
                state.progress_pct = progress_pct
                state.telemetry = telemetry[-200:]
                state.set_metrics(self._metrics.compute_snapshot(state.telemetry))
                self._persist_runtime(session_id)

            result = self._get_video_processor().process(Path(video_path), progress_callback=on_progress)

            state.telemetry = result["telemetry"][-500:]
            state.events = result["events"][-100:]
            state.set_media_info(result["media_info"])
            state.set_metrics(result["stats"])
            state.set_stage("completed", 100.0)
            state.is_active = False
            self._persist_runtime(session_id)

            trajectories = []
            for row in result["trajectories"]:
                row["session_id"] = session_id
                trajectories.append(row)
            repo.replace_trajectories(session_id, trajectories)
            repo.create_events_bulk(session_id, result["events"])

            summary = self._reports.build_summary(result["stats"], result["events"])
            artifact_path = self._reports.write_report_artifact(session_id, summary, result["stats"], result["events"])
            repo.upsert_report(
                session_id,
                ReportCreate(
                    summary_text=summary,
                    pdf_path=artifact_path,
                    stats=result["stats"],
                    dashboard_snapshot={
                        "metrics_snapshot": result["stats"],
                        "media_info": result["media_info"],
                        "progress_pct": 100.0,
                        "stage": "completed",
                    },
                ),
            )
            repo.complete_session(session_id)
            self._memory_guard.release()
        except Exception as exc:
            repo.fail_session(session_id)
            state.set_stage("failed", state.progress_pct)
            state.push_event(
                {
                    "id": f"error-{session_id}",
                    "frame_idx": state.frame_idx,
                    "event_type": "processing_error",
                    "timestamp_s": 0.0,
                    "narration_text": str(exc),
                    "metadata": {"error": str(exc)},
                }
            )
            self._persist_runtime(session_id)
        finally:
            db.close()

    def get_report_detail(self, db: Session, session_id: UUID) -> dict | None:
        repo = SessionRepository(db)
        session = repo.get_session(session_id)
        if session is None:
            return None
        return {
            "session": session,
            "report": repo.get_report(session_id),
            "events": repo.list_events(session_id),
            "trajectories": repo.list_trajectories(session_id, limit=400),
        }

    def ensure_report_pdf_artifact(self, db: Session, session_id: UUID) -> Path | None:
        repo = SessionRepository(db)
        report = repo.get_report(session_id)
        if report is None:
            return None

        artifact = Path(report.pdf_path) if report.pdf_path else None
        if artifact and artifact.exists() and artifact.suffix.lower() == ".pdf":
            return artifact

        events = repo.list_events(session_id)
        event_payloads = [
            {
                "frame_idx": event.frame_idx,
                "timestamp_s": event.timestamp_s,
                "event_type": event.event_type,
                "metadata": event.event_metadata,
                "narration_text": event.narration_text,
            }
            for event in events
        ]
        stats = report.stats or self._metrics.bootstrap_metrics()
        summary = report.summary_text or self._reports.build_summary(stats, event_payloads)
        artifact_path = self._reports.write_report_artifact(session_id, summary, stats, event_payloads)
        repo.upsert_report(
            session_id,
            ReportCreate(
                summary_text=summary,
                pdf_path=artifact_path,
                stats=stats,
                dashboard_snapshot=report.dashboard_snapshot,
            ),
        )
        return Path(artifact_path)

    def _ensure_report_persisted(self, db: Session, session_id: UUID) -> None:
        repo = SessionRepository(db)
        if repo.get_report(session_id) is not None:
            return

        events = repo.list_events(session_id)
        trajectories = repo.list_trajectories(session_id, limit=1000)
        state = self._states.get(session_id)
        cached = self._runtime_store.load_snapshot(session_id)

        if state is not None:
            metrics = state.metrics or self._metrics.compute_snapshot(state.telemetry)
            media_info = state.media_info
            runtime_events = state.events
        else:
            metrics = cached.get("metrics", {}) if cached else {}
            media_info = cached.get("media_info", {}) if cached else {}
            runtime_events = []

        if not metrics and trajectories:
            metrics = self._metrics.compute_snapshot(
                [
                    {
                        "x_cm": row.x_cm,
                        "y_cm": row.y_cm,
                        "speed_cm_s": 0.0,
                    }
                    for row in trajectories
                ]
            )

        if media_info:
            metrics = {**media_info, **metrics}

        if not metrics:
            metrics = self._metrics.bootstrap_metrics()

        if not events and runtime_events:
            for event in runtime_events:
                repo.create_event(
                    session_id,
                    EventCreate(
                        frame_idx=event.get("frame_idx", 0),
                        timestamp_s=event.get("timestamp_s", 0.0),
                        event_type=event.get("event_type", "manual_event"),
                        metadata=event.get("metadata"),
                        narration_text=event.get("narration_text"),
                    ),
                )
            events = repo.list_events(session_id)

        event_payloads = [
            {
                "frame_idx": event.frame_idx,
                "timestamp_s": event.timestamp_s,
                "event_type": event.event_type,
                "metadata": event.event_metadata,
                "narration_text": event.narration_text,
            }
            for event in events
        ]
        summary = self._reports.build_summary(metrics, event_payloads)
        artifact_path = self._reports.write_report_artifact(session_id, summary, metrics, event_payloads)
        repo.upsert_report(
            session_id,
            ReportCreate(
                summary_text=summary,
                pdf_path=artifact_path,
                stats=metrics,
                dashboard_snapshot={
                    "metrics_snapshot": metrics,
                    "media_info": media_info,
                    "progress_pct": 100.0,
                    "stage": "completed",
                },
            ),
        )

    def _persist_runtime(self, session_id: UUID) -> None:
        state = self._states.get(session_id)
        if state is None:
            return
        self._runtime_store.save_snapshot(session_id, state.snapshot())
