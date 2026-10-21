"""SERVICE LAYER — object detection (image input, boxes output)."""

from __future__ import annotations

import time

from PIL import Image

from core.config import available_devices, settings
from core.env_check import check_vision_backend
from core.errors import InvalidDeviceError, ModelBackendError
from models.registry import ModelRegistry

_MOCK_OBJECTS = [
    {"label": "car", "score": 0.97, "box": {"xmin": 42.0, "ymin": 130.0, "xmax": 410.0, "ymax": 320.0}},
    {"label": "person", "score": 0.88, "box": {"xmin": 300.0, "ymin": 90.0, "xmax": 360.0, "ymax": 300.0}},
]


class DetectionService:
    def __init__(self, registry: ModelRegistry):
        self._registry = registry

    def detect(self, image: Image.Image, threshold: float | None = None, device: str | None = None) -> dict:
        threshold = settings.detection_threshold if threshold is None else threshold
        device = (device or settings.device).lower()
        if device not in available_devices():
            raise InvalidDeviceError(f"Device '{device}' is not available on this machine.")

        started = time.perf_counter()
        if settings.mock:
            objects = _MOCK_OBJECTS
            model_name = "yolos-tiny (mock)"
        else:
            check_vision_backend()
            try:
                model = self._registry.ensure_loaded("yolos-tiny", device)
                objects = model.predict(image, threshold=threshold)
                model_name = model.name
            except ModelBackendError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise ModelBackendError(f"Detection failed: {exc}") from exc

        return {
            "model": model_name,
            "device": "cpu" if settings.mock else device,
            "threshold": threshold,
            "count": len(objects),
            "objects": objects,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        }
