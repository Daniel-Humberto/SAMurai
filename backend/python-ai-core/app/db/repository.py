from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from app.db.models import EventModel, ReportModel, SessionModel, TrajectoryModel
from app.schemas import EventCreate, ReportCreate, SessionCreate


class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, payload: SessionCreate, status: str = "active") -> SessionModel:
        session = SessionModel(
            mode=payload.mode,
            source_path=payload.source_path,
            homography_matrix=payload.homography_matrix,
            status=status,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def list_sessions(self) -> list[SessionModel]:
        stmt = select(SessionModel).order_by(desc(SessionModel.started_at))
        return list(self.db.scalars(stmt).all())

    def list_completed_sessions(self) -> list[SessionModel]:
        stmt = (
            select(SessionModel)
            .where(SessionModel.status == "completed")
            .order_by(desc(SessionModel.ended_at), desc(SessionModel.started_at))
        )
        return list(self.db.scalars(stmt).all())

    def get_session(self, session_id: UUID) -> SessionModel | None:
        return self.db.get(SessionModel, session_id)

    def update_session_status(self, session_id: UUID, status: str, ended: bool = False) -> SessionModel | None:
        session = self.get_session(session_id)
        if session is None:
            return None
        session.status = status
        if ended:
            session.ended_at = datetime.now(timezone.utc)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def complete_session(self, session_id: UUID) -> SessionModel | None:
        return self.update_session_status(session_id, "completed", ended=True)

    def fail_session(self, session_id: UUID) -> SessionModel | None:
        return self.update_session_status(session_id, "failed", ended=True)

    def create_event(self, session_id: UUID, payload: EventCreate) -> EventModel:
        data = payload.model_dump()
        data["event_metadata"] = data.pop("metadata", None)
        event = EventModel(session_id=session_id, **data)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def create_events_bulk(self, session_id: UUID, events: list[dict]) -> None:
        rows = []
        for event in events:
            row = dict(event)
            row["event_metadata"] = row.pop("metadata", None)
            rows.append(EventModel(session_id=session_id, **row))
        self.db.add_all(rows)
        self.db.commit()

    def list_events(self, session_id: UUID) -> list[EventModel]:
        stmt = select(EventModel).where(EventModel.session_id == session_id).order_by(EventModel.timestamp_s)
        return list(self.db.scalars(stmt).all())

    def replace_trajectories(self, session_id: UUID, trajectories: list[dict]) -> None:
        self.db.execute(delete(TrajectoryModel).where(TrajectoryModel.session_id == session_id))
        if trajectories:
            self.db.bulk_insert_mappings(TrajectoryModel, trajectories)
        self.db.commit()

    def list_trajectories(self, session_id: UUID, limit: int = 200) -> list[TrajectoryModel]:
        stmt = (
            select(TrajectoryModel)
            .where(TrajectoryModel.session_id == session_id)
            .order_by(TrajectoryModel.frame_idx)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def create_report(self, session_id: UUID, payload: ReportCreate) -> ReportModel:
        report = ReportModel(session_id=session_id, **payload.model_dump())
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def upsert_report(self, session_id: UUID, payload: ReportCreate) -> ReportModel:
        report = self.get_report(session_id)
        if report is None:
            return self.create_report(session_id, payload)
        report.summary_text = payload.summary_text
        report.pdf_path = payload.pdf_path
        report.stats = payload.stats
        report.dashboard_snapshot = payload.dashboard_snapshot
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_report(self, session_id: UUID) -> ReportModel | None:
        stmt = select(ReportModel).where(ReportModel.session_id == session_id)
        return self.db.scalars(stmt).first()
