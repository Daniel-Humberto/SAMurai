from mimetypes import guess_type
from pathlib import Path
from uuid import UUID

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import EventModel
from app.narrative.tts_engine import PiperTTSEngine
from app.core.session_manager import SessionManager
from app.db.database import get_db
from app.db.repository import SessionRepository
from app.schemas import (
    EventCreate,
    EventRead,
    ReportDetail,
    SessionCreate,
    SessionRead,
    SessionSummary,
    UploadSessionResponse,
)


router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])
manager = SessionManager()
settings = get_settings()


def _sanitize_narration_text(text: str | None) -> str | None:
    if not text:
        return text
    return __import__("re").sub(r"^\s*\[[^\]]+\]\s*", "", text).strip()


def _serialize_event_models(events):
    return [
        {
            "id": str(event.id),
            "session_id": str(event.session_id),
            "frame_idx": event.frame_idx,
            "timestamp_s": event.timestamp_s,
            "event_type": event.event_type,
            "metadata": event.event_metadata,
            "narration_text": _sanitize_narration_text(event.narration_text),
            "created_at": event.created_at,
        }
        for event in events
    ]


async def _persist_upload(upload: UploadFile, destination: Path) -> int:
    total_bytes = 0
    chunk_size = settings.upload_chunk_size_bytes
    max_bytes = settings.max_upload_size_bytes

    async with aiofiles.open(destination, "wb") as buffer:
        while True:
            chunk = await upload.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"El archivo excede el limite de {settings.max_upload_size_mb} MB",
                )
            await buffer.write(chunk)

    await upload.close()
    return total_bytes


@router.get("", response_model=list[SessionRead])
def list_sessions(db: Session = Depends(get_db)):
    repo = SessionRepository(db)
    return repo.list_sessions()


@router.get("/history", response_model=list[SessionRead])
def list_history(db: Session = Depends(get_db)):
    repo = SessionRepository(db)
    return repo.list_completed_sessions()


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    return manager.start_session(db, payload)


@router.post("/upload", response_model=UploadSessionResponse, status_code=status.HTTP_201_CREATED)
async def upload_video_session(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    mode: str = Form("video"),
    db: Session = Depends(get_db),
):
    if mode != "video":
        raise HTTPException(status_code=400, detail="Solo se admite upload en modo video")
    suffix = Path(file.filename or "upload.mp4").suffix.lower()
    if suffix not in {".mp4", ".mov", ".avi", ".mkv"}:
        raise HTTPException(status_code=400, detail="Formato de video no soportado")

    provisional = manager.start_session(db, SessionCreate(mode="video", source_path=file.filename), status="processing")
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    upload_path = settings.uploads_dir / f"{provisional.id}{suffix}"
    try:
        total_bytes = await _persist_upload(file, upload_path)
    except Exception:
        if upload_path.exists():
            upload_path.unlink()
        raise

    provisional.source_path = str(upload_path)
    db.add(provisional)
    db.commit()
    db.refresh(provisional)

    manager.attach_media_info(
        provisional.id,
        {"filename": file.filename or upload_path.name, "bytes": total_bytes, "path": str(upload_path)},
    )
    background_tasks.add_task(manager.process_video_session, provisional.id, str(upload_path))
    return UploadSessionResponse(session=provisional, upload_path=str(upload_path))


@router.get("/{session_id}", response_model=SessionSummary)
def get_session(session_id: UUID, db: Session = Depends(get_db)):
    repo = SessionRepository(db)
    session = repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    summary = manager.get_session_summary(db, session_id)
    pending_events = summary["pending_events"]
    if pending_events and not isinstance(pending_events[0], dict):
        pending_events = _serialize_event_models(pending_events)

    return SessionSummary(
        session=session,
        pipeline=summary["pipeline"],
        metrics_snapshot=summary["metrics_snapshot"],
        pending_events=pending_events,
        media_info=summary["media_info"],
        progress_pct=summary["progress_pct"],
        stage=summary["stage"],
        recent_trajectories=summary["recent_trajectories"],
    )


@router.get("/{session_id}/source")
def get_session_source(session_id: UUID, db: Session = Depends(get_db)):
    repo = SessionRepository(db)
    session = repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.mode != "video" or not session.source_path:
        raise HTTPException(status_code=404, detail="Session source not available")

    source = Path(session.source_path)
    if not source.exists():
        raise HTTPException(status_code=404, detail="Source file missing")

    media_type = guess_type(source.name)[0] or "application/octet-stream"
    return FileResponse(source, media_type=media_type, filename=source.name)


@router.get("/{session_id}/report", response_model=ReportDetail)
def get_report(session_id: UUID, db: Session = Depends(get_db)):
    detail = manager.get_report_detail(db, session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if detail.get("report") and detail["report"].summary_text:
        detail["report"].summary_text = _sanitize_narration_text(detail["report"].summary_text)
    if "events" in detail:
        detail["events"] = _serialize_event_models(detail["events"])
    return ReportDetail(**detail)


@router.get("/{session_id}/artifact")
def get_report_artifact(session_id: UUID, db: Session = Depends(get_db)):
    artifact = manager.ensure_report_pdf_artifact(db, session_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if not artifact.exists():
        raise HTTPException(status_code=404, detail="Artifact file missing")
    return FileResponse(artifact, media_type="application/pdf", filename=artifact.name)


@router.post("/{session_id}/events", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def register_event(session_id: UUID, payload: EventCreate, db: Session = Depends(get_db)):
    repo = SessionRepository(db)
    if repo.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    event = manager.register_event(db, session_id, payload)
    return {
        "id": event.id,
        "session_id": event.session_id,
        "frame_idx": event.frame_idx,
        "timestamp_s": event.timestamp_s,
        "event_type": event.event_type,
        "metadata": event.event_metadata,
        "narration_text": _sanitize_narration_text(event.narration_text),
        "created_at": event.created_at,
    }


@router.post("/{session_id}/finalize", response_model=SessionRead)
def finalize_session(session_id: UUID, db: Session = Depends(get_db)):
    try:
        session = manager.finalize_session(db, session_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/{session_id}/audio")
def get_session_audio(session_id: UUID, db: Session = Depends(get_db)):
    repo = SessionRepository(db)
    session = repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    audio_path = Path(settings.reports_dir) / f"{session_id}.wav"
    if audio_path.exists():
        return FileResponse(audio_path, media_type="audio/wav", filename=f"{session_id}.wav")

    report = repo.get_report(session_id)
    text_to_synthesize = ""
    if report and report.summary_text:
        text_to_synthesize = _sanitize_narration_text(report.summary_text)
    else:
        events = repo.list_events(session_id)
        narrations = [_sanitize_narration_text(e.narration_text) for e in events if e.narration_text]
        if narrations:
            text_to_synthesize = " ".join(narrations)
        else:
            text_to_synthesize = "No hay eventos narrados para esta sesión."

    tts = PiperTTSEngine()
    result = tts.synthesize(text_to_synthesize, audio_path)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error", "Error sintetizando audio"))

    return FileResponse(audio_path, media_type="audio/wav", filename=f"{session_id}.wav")


@router.get("/{session_id}/events/{event_id}/audio")
def get_event_audio(session_id: UUID, event_id: UUID, db: Session = Depends(get_db)):
    repo = SessionRepository(db)
    if repo.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")

    event = db.get(EventModel, event_id)
    if event is None or event.session_id != session_id:
        raise HTTPException(status_code=404, detail="Event not found in this session")

    audio_path = Path(settings.reports_dir) / f"event_{event_id}.wav"
    if audio_path.exists():
        return FileResponse(audio_path, media_type="audio/wav", filename=f"event_{event_id}.wav")

    text_to_synthesize = event.narration_text or "Evento detectado."
    tts = PiperTTSEngine()
    result = tts.synthesize(text_to_synthesize, audio_path)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error", "Error sintetizando audio"))

    return FileResponse(audio_path, media_type="audio/wav", filename=f"event_{event_id}.wav")
