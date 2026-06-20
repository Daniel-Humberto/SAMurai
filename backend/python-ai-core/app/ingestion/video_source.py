class VideoSourceService:
    def describe(self) -> dict:
        return {
            "component": "ingestion",
            "supported_modes": ["live", "video", "history"],
        }
