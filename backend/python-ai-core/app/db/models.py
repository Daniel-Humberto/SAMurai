import uuid
from datetime import datetime

from sqlalchemy import BIGINT, FLOAT, JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    source_path: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    homography_matrix: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    events: Mapped[list["EventModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    trajectories: Mapped[list["TrajectoryModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    report: Mapped["ReportModel | None"] = relationship(back_populates="session", uselist=False)


class EventModel(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    frame_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp_s: Mapped[float] = mapped_column(FLOAT, nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSON)
    narration_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)

    session: Mapped["SessionModel"] = relationship(back_populates="events")


class TrajectoryModel(Base):
    __tablename__ = "trajectories"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    frame_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    object_id: Mapped[int] = mapped_column(Integer, nullable=False)
    object_class: Mapped[str | None] = mapped_column(String(20))
    x_cm: Mapped[float | None] = mapped_column(FLOAT)
    y_cm: Mapped[float | None] = mapped_column(FLOAT)
    area_px: Mapped[int | None] = mapped_column(Integer)
    predicted_x_cm: Mapped[float | None] = mapped_column(FLOAT)
    predicted_y_cm: Mapped[float | None] = mapped_column(FLOAT)

    session: Mapped["SessionModel"] = relationship(back_populates="trajectories")


class ReportModel(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id"),
        nullable=False,
        unique=True,
    )
    summary_text: Mapped[str | None] = mapped_column(Text)
    pdf_path: Mapped[str | None] = mapped_column(Text)
    stats: Mapped[dict | None] = mapped_column(JSON)
    dashboard_snapshot: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)

    session: Mapped["SessionModel"] = relationship(back_populates="report")
