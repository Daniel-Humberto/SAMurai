import gc


class MemoryGuard:
    def __init__(self, max_telemetry_points: int = 10000):
        self.max_telemetry_points = max_telemetry_points

    def prune_state(self, runtime_state) -> None:
        with runtime_state.lock:
            if len(runtime_state.telemetry) > self.max_telemetry_points:
                runtime_state.telemetry = runtime_state.telemetry[-self.max_telemetry_points :]
            if len(runtime_state.events) > 1000:
                runtime_state.events = runtime_state.events[-1000:]

    def release(self) -> None:
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
