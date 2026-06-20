from collections import Counter

from app.config import get_settings


class LLMAdapter:
    def __init__(self):
        settings = get_settings()
        self.provider = settings.llm_provider

    def generate_narration(self, event: dict, context: dict) -> str:
        event_type = event.get("event_type", "play")
        frame_idx = event.get("frame_idx", 0)
        speed = event.get("metadata", {}).get("speed_cm_s", 0)
        return (
            f"{event_type} detectado en frame {frame_idx}. "
            f"Velocidad estimada {round(speed, 1)} cm/s."
        )

    def generate_executive_report(self, session_stats: dict, events: list) -> str:
        counts = Counter(event.get("event_type", "unknown") for event in events)
        top_event = counts.most_common(1)[0][0] if counts else "sin eventos tacticos"
        return (
            f"La sesion procesada en modo {session_stats.get('mode', 'video')} "
            f"acumulo {len(events)} eventos relevantes. El patron dominante fue {top_event}. "
            f"La posesion estimada del sector azul fue {session_stats.get('possession_blue', 0)}% "
            f"con una velocidad maxima observada de {session_stats.get('max_speed_cm_s', 0)} cm/s."
        )
