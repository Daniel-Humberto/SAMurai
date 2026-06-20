from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


SessionMode = Literal["live", "video"]
SessionStatus = Literal["active", "processing", "completed", "failed"]


class SessionCreate(BaseModel):
    mode: SessionMode
    source_path: str | None = None
    homography_matrix: dict | None = None


class SessionRead(BaseModel):
    id: UUID
    mode: SessionMode
    source_path: str | None
    started_at: datetime
    ended_at: datetime | None
    homography_matrix: dict | None
    status: SessionStatus

    model_config = {"from_attributes": True}


class EventCreate(BaseModel):
    frame_idx: int
    timestamp_s: float
    event_type: str
    metadata: dict[str, Any] | None = None
    narration_text: str | None = None


class EventRead(EventCreate):
    id: UUID
    session_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class TrajectoryRead(BaseModel):
    frame_idx: int
    object_id: int
    object_class: str | None
    x_cm: float | None
    y_cm: float | None
    area_px: int | None
    predicted_x_cm: float | None
    predicted_y_cm: float | None

    model_config = {"from_attributes": True}


class ReportCreate(BaseModel):
    summary_text: str | None = None
    pdf_path: str | None = None
    stats: dict[str, Any] | None = None
    dashboard_snapshot: dict[str, Any] | None = None


class ReportRead(ReportCreate):
    id: UUID
    session_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionSummary(BaseModel):
    session: SessionRead
    pipeline: dict
    metrics_snapshot: dict[str, Any]
    pending_events: list[dict[str, Any]] = Field(default_factory=list)
    media_info: dict[str, Any] = Field(default_factory=dict)
    progress_pct: float = 0.0
    stage: str = "queued"
    recent_trajectories: list[TrajectoryRead] = Field(default_factory=list)


class ReportDetail(BaseModel):
    session: SessionRead
    report: ReportRead | None = None
    events: list[EventRead] = Field(default_factory=list)
    trajectories: list[TrajectoryRead] = Field(default_factory=list)


class UploadSessionResponse(BaseModel):
    session: SessionRead
    upload_path: str
