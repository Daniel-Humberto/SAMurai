import os
import subprocess
from pathlib import Path

from app.config import get_settings


class PiperTTSEngine:
    def __init__(self):
        settings = get_settings()
        self.voice = settings.tts_voice
        self.binary_path = Path("/app/models/piper/piper/piper")
        self.model_path = Path(f"/app/models/piper/{self.voice}.onnx")
        self.lib_path = Path("/app/models/piper/piper")

    def synthesize(self, text: str, output_path: Path) -> dict:
        if not self.binary_path.exists():
            return {
                "status": "error",
                "error": f"Piper binary not found at {self.binary_path}",
            }
        
        # Fallback to any .onnx model if settings.tts_voice doesn't match perfectly
        if not self.model_path.exists():
            onnx_files = list(self.model_path.parent.glob("*.onnx"))
            if onnx_files:
                # Filter out symlinks or prefer the actual model
                self.model_path = onnx_files[0]
            else:
                return {
                    "status": "error",
                    "error": f"No Piper voice model (.onnx) found in {self.model_path.parent}",
                }

        # Make sure parent directory of output file exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = str(self.lib_path)

        try:
            process = subprocess.Popen(
                [
                    str(self.binary_path),
                    "--model", str(self.model_path),
                    "--output_file", str(output_path)
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )
            stdout, stderr = process.communicate(input=text)

            if process.returncode == 0 and output_path.exists():
                return {
                    "voice": self.voice,
                    "text": text,
                    "path": str(output_path),
                    "status": "completed",
                }
            else:
                return {
                    "status": "error",
                    "error": f"Piper execution failed (code {process.returncode}). Stderr: {stderr}",
                }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Exception occurred during synthesis: {str(e)}",
            }

