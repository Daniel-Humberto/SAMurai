import json
from uuid import UUID

import redis

from app.config import get_settings


class RuntimeStore:
    def __init__(self):
        settings = get_settings()
        self.namespace = settings.runtime_namespace
        self._client = None
        try:
            self._client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            self._client.ping()
        except Exception:
            self._client = None

    def _key(self, session_id: UUID) -> str:
        return f"{self.namespace}:{session_id}"

    def save_snapshot(self, session_id: UUID, snapshot: dict) -> None:
        if self._client is None:
            return
        self._client.set(self._key(session_id), json.dumps(snapshot))

    def load_snapshot(self, session_id: UUID) -> dict | None:
        if self._client is None:
            return None
        payload = self._client.get(self._key(session_id))
        return json.loads(payload) if payload else None

    def delete_snapshot(self, session_id: UUID) -> None:
        if self._client is None:
            return
        self._client.delete(self._key(session_id))
