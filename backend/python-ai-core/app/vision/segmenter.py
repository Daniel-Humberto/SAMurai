"""
SAM 3 segmenter — Segment Anything with Concepts (arXiv:2511.16719).

Hardware-aware model selection:
  auto  → detecta GPU/VRAM y elige el perfil más grande que quepa
  tiny  → ~40 MB,  sin GPU requerida  (CPU / GPU < 2 GB)
  small → ~185 MB, GPU >= 2 GB VRAM
  base  → ~375 MB, GPU >= 4 GB VRAM
  large → ~850 MB, GPU >= 8 GB VRAM

SAM 3 soporta prompts de texto (conceptos abiertos) además de bboxes.
Se usa detections.data["team"] como concepto guía cuando está disponible.
"""

import gc
import logging
import os

import cv2
import numpy as np
import torch
import supervision as sv

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Perfiles de modelo
# ---------------------------------------------------------------------------

_SAM3_ULTRALYTICS = {
    "tiny":  "sam3_t.pt",
    "small": "sam3_s.pt",
    "base":  "sam3_b.pt",
    "large": "sam3_l.pt",
}

_SAM3_HF = {
    "tiny":  "facebook/sam3-hiera-tiny",
    "small": "facebook/sam3-hiera-small",
    "base":  "facebook/sam3-hiera-base-plus",
    "large": "facebook/sam3-hiera-large",
}

# VRAM mínima (GB) para activar cada perfil en modo auto
_VRAM_THRESHOLDS = {
    "large": 8.0,
    "base":  4.0,
    "small": 2.0,
    "tiny":  0.0,
}

# Mapeo de etiqueta interna → concepto texto para SAM 3
_CONCEPT_MAP = {
    "azul":  "blue robot",
    "rojo":  "red robot",
    "balon": "soccer ball",
}

MEMORY_WINDOW = 15


# ---------------------------------------------------------------------------
# Detección de hardware
# ---------------------------------------------------------------------------

def _detect_device() -> tuple[str, float]:
    """Devuelve (device, vram_gb). vram_gb=0 para CPU/MPS."""
    if torch.cuda.is_available():
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        return "cuda", vram
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps", 0.0
    return "cpu", 0.0


def _auto_profile(vram_gb: float, device: str) -> str:
    """Elige el perfil más grande que el hardware puede sostener."""
    if device == "cpu":
        return "tiny"
    for profile, threshold in _VRAM_THRESHOLDS.items():
        if vram_gb >= threshold:
            return profile
    return "tiny"


# ---------------------------------------------------------------------------
# Backend ultralytics (principal)
# ---------------------------------------------------------------------------

def _load_ultralytics(checkpoint: str, device: str):
    from ultralytics import SAM
    model = SAM(checkpoint)
    logger.info(f"SAM 3 cargado via ultralytics: {checkpoint} en {device}")
    return ("ultralytics", model)


# ---------------------------------------------------------------------------
# Backend HuggingFace transformers (secundario)
# ---------------------------------------------------------------------------

def _load_hf(repo: str, device: str):
    from transformers import Sam3Processor, Sam3Model
    processor = Sam3Processor.from_pretrained(repo)
    model = Sam3Model.from_pretrained(repo).to(device)
    model.eval()
    logger.info(f"SAM 3 cargado via HuggingFace: {repo} en {device}")
    return ("hf", model, processor)


# ---------------------------------------------------------------------------
# Clase principal
# ---------------------------------------------------------------------------

class SAMSegmenter:
    """
    Segmentador SAM 3 con selección de hardware automática.

    Prioridad de backend:
      1. ultralytics  (SAM 3 nativo, bbox + text prompts)
      2. HuggingFace transformers (Sam3Processor / Sam3Model)
      3. Desactivado con advertencia (el pipeline continúa sin máscaras)

    El perfil se resuelve así:
      - size="auto"  → detecta hardware en tiempo de inicio
      - size="tiny|small|base|large" → fuerza ese perfil independiente del hardware
    """

    def __init__(self, size: str = "auto"):
        os.makedirs("/dev/shm/samurai", exist_ok=True)

        self.device, vram_gb = _detect_device()
        resolved = size if size != "auto" else _auto_profile(vram_gb, self.device)

        logger.info(
            f"SAM 3 | device={self.device} vram={vram_gb:.1f}GB "
            f"size_requested={size} size_resolved={resolved}"
        )

        self.profile = resolved
        self._frame_count = 0
        self._backend = None   # "ultralytics" | "hf" | None
        self._model = None
        self._processor = None  # solo HuggingFace

        self._init_model(resolved)

    # ------------------------------------------------------------------
    # Inicialización con fallback
    # ------------------------------------------------------------------

    def _init_model(self, profile: str):
        # 1. Intentar ultralytics SAM 3
        try:
            result = _load_ultralytics(_SAM3_ULTRALYTICS[profile], self.device)
            self._backend, self._model = result
            return
        except Exception as e:
            logger.warning(f"ultralytics SAM 3 ({profile}) no disponible: {e}")

        # 2. Intentar HuggingFace SAM 3
        try:
            result = _load_hf(_SAM3_HF[profile], self.device)
            self._backend, self._model, self._processor = result
            return
        except Exception as e:
            logger.warning(f"HuggingFace SAM 3 ({profile}) no disponible: {e}")

        logger.error(
            "SAM 3 no pudo cargarse en ningún backend. "
            "El pipeline continúa sin segmentación por píxel."
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def segment(
        self,
        frame_bgr: np.ndarray,
        detections: sv.Detections,
    ) -> sv.Detections:
        """
        Genera máscaras SAM 3 solo para robots (se omite el balón).

        Usa bboxes como prompt visual + etiquetas de equipo como
        prompts de concepto texto (característica exclusiva de SAM 3).
        Si SAM 3 no está disponible retorna detections sin modificar.
        """
        if self._model is None or len(detections) == 0:
            return detections

        # Segmentar solo robots; el balón se excluye (naranja, no necesita máscara)
        teams = detections.data.get("team")
        if teams is not None:
            robot_mask = np.array([t != "balon" for t in teams])
        else:
            robot_mask = np.ones(len(detections), dtype=bool)

        robot_detections = detections[robot_mask]
        if len(robot_detections) == 0:
            return detections

        concepts = self._extract_concepts(robot_detections)

        try:
            if self._backend == "ultralytics":
                robot_detections = self._segment_ultralytics(frame_bgr, robot_detections, concepts)
            elif self._backend == "hf":
                robot_detections = self._segment_hf(frame_bgr, robot_detections, concepts)
        except Exception as e:
            logger.warning(f"SAM 3 segmentación falló: {e}")
            return detections
        finally:
            self._frame_count += 1
            self._memory_guard()

        # Reinsertar máscaras de robots en el array completo de detecciones
        if robot_detections.mask is not None:
            h, w = frame_bgr.shape[:2]
            full_masks = np.zeros((len(detections), h, w), dtype=bool)
            robot_indices = np.where(robot_mask)[0]
            for local_i, global_i in enumerate(robot_indices):
                if local_i < len(robot_detections.mask):
                    full_masks[global_i] = robot_detections.mask[local_i]
            detections.mask = full_masks

        return detections

    # ------------------------------------------------------------------
    # Backends internos
    # ------------------------------------------------------------------

    def _segment_ultralytics(
        self,
        frame_bgr: np.ndarray,
        detections: sv.Detections,
        concepts: list[str],
    ) -> sv.Detections:
        half = self.device == "cuda"

        # SAM 3 acepta texts= para prompts de concepto abierto
        kwargs = dict(
            bboxes=detections.xyxy,
            device=self.device,
            half=half,
            verbose=False,
        )
        if concepts:
            kwargs["texts"] = concepts

        results = self._model(frame_bgr, **kwargs)

        if results and results[0].masks is not None:
            masks_np = results[0].masks.data.cpu().numpy().astype(bool)
            detections.mask = self._align_masks(masks_np, detections, frame_bgr.shape)

        return detections

    def _segment_hf(
        self,
        frame_bgr: np.ndarray,
        detections: sv.Detections,
        concepts: list[str],
    ) -> sv.Detections:
        import torch

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        boxes = detections.xyxy.tolist()

        inputs = self._processor(
            images=frame_rgb,
            input_boxes=[boxes],
            input_texts=concepts if concepts else None,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            outputs = self._model(**inputs)

        masks = self._processor.post_process_masks(
            outputs.pred_masks,
            inputs["original_sizes"],
            inputs["reshaped_input_sizes"],
        )[0].squeeze(1).cpu().numpy().astype(bool)

        detections.mask = self._align_masks(masks, detections, frame_bgr.shape)
        return detections

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _extract_concepts(self, detections: sv.Detections) -> list[str]:
        """Convierte etiquetas de equipo en conceptos texto para SAM 3."""
        teams = detections.data.get("team")
        if teams is None:
            return []
        return [_CONCEPT_MAP.get(str(t), str(t)) for t in teams]

    def _align_masks(
        self,
        masks_np: np.ndarray,
        detections: sv.Detections,
        frame_shape: tuple,
    ) -> np.ndarray:
        """Ajusta cantidad de máscaras al número de detecciones."""
        h, w = frame_shape[:2]
        n_det = len(detections)
        n_masks = len(masks_np)

        if n_masks == n_det:
            return masks_np

        aligned = np.zeros((n_det, h, w), dtype=bool)
        copy_n = min(n_masks, n_det)
        aligned[:copy_n] = masks_np[:copy_n]
        return aligned

    def _memory_guard(self):
        if self._frame_count % MEMORY_WINDOW == 0:
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    # ------------------------------------------------------------------
    # Info de estado
    # ------------------------------------------------------------------

    def info(self) -> dict:
        return {
            "backend": self._backend,
            "profile": self.profile,
            "device": self.device,
            "available": self._model is not None,
        }
