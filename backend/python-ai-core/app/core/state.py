from dataclasses import dataclass, field
from threading import RLock
import threading
from typing import Any, Optional
from uuid import UUID
import numpy as np

@dataclass
class SessionRuntimeState:
    """Runtime state for video processing sessions stored in-memory."""
    session_id: UUID
    frame_idx: int = 0
    is_active: bool = True
    stage: str = "queued"
    progress_pct: float = 0.0
    telemetry: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    media_info: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "session_id": str(self.session_id),
                "frame_idx": self.frame_idx,
                "is_active": self.is_active,
                "stage": self.stage,
                "progress_pct": self.progress_pct,
                "telemetry_count": len(self.telemetry),
                "event_count": len(self.events),
                "media_info": self.media_info,
                "metrics": self.metrics,
            }

    def set_stage(self, stage: str, progress_pct: float | None = None) -> None:
        with self.lock:
            self.stage = stage
            if progress_pct is not None:
                self.progress_pct = progress_pct

    def set_media_info(self, media_info: dict[str, Any]) -> None:
        with self.lock:
            self.media_info = media_info

    def set_metrics(self, metrics: dict[str, Any]) -> None:
        with self.lock:
            self.metrics = metrics

    def push_event(self, event: dict[str, Any]) -> None:
        with self.lock:
            self.events.append(event)

    def push_telemetry(self, telemetry: dict[str, Any]) -> None:
        with self.lock:
            self.frame_idx = telemetry.get("frame_idx", self.frame_idx)
            self.telemetry.append(telemetry)


@dataclass
class SessionState:
    """Thread-safe state manager for live/video processing sessions."""
    session_id: str
    status: str = "idle"      # idle | calibrating | processing | completed | error
    frame_idx: int = 0
    fps_actual: float = 0.0
    last_frame_result: Optional[dict] = None
    homography_points: Optional[list] = None  # 4 puntos pendientes de calibrar
    error_msg: Optional[str] = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def update(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, v)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "session_id": self.session_id,
                "status": self.status,
                "frame_idx": self.frame_idx,
                "fps_actual": self.fps_actual,
                "last_result": self.last_frame_result,
                "calibrated": self.homography_points is not None,
                "error": self.error_msg,
            }

# Registry global thread-safe de sesiones activas
_registry: dict[str, SessionState] = {}
_registry_lock = threading.Lock()

def get_session_state(session_id: str) -> Optional[SessionState]:
    with _registry_lock:
        return _registry.get(session_id)

def create_session_state(session_id: str) -> SessionState:
    state = SessionState(session_id=session_id)
    with _registry_lock:
        _registry[session_id] = state
    return state

def remove_session_state(session_id: str):
    with _registry_lock:
        _registry.pop(session_id, None)
