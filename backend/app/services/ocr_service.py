"""SERVICE LAYER — OCR: pick engine/device, preprocess, run the model, shape the result."""

from __future__ import annotations

import time

from PIL import Image

from core.config import OCR_MODELS, available_devices, settings
from core.env_check import check_vision_backend
from core.errors import InvalidDeviceError, ModelBackendError, UnknownModelError
from models.registry import ModelRegistry
from services.preprocess import segment_lines

# Canned output when MOCK_MODE=1.
_MOCK_LINES = [
    "ABC CO., LTD",
    "INVOICE",
    "Date: 2026-10-14   No: INV-0001",
    "Item          Qty   Price     Amount",
    "T-Shirt         2   150000     300000",
    "Jeans           1   450000     450000",
    "Total: 750000 VND",
]


class OCRService:
    def __init__(self, registry: ModelRegistry):
        self._registry = registry

    def list_models(self) -> list[dict]:
        """Describe every OCR model and where each one is currently loaded."""
        out = []
        for spec in OCR_MODELS.values():
            out.append(
                {
                    "name": spec.name,
                    "engine": spec.engine,
                    "hf_id": spec.hf_id,
                    "kind": spec.kind,
                    "description": spec.description,
                    "devices": list(spec.devices),
                    "loaded_on": [
                        d for d in spec.devices if self._registry.is_loaded(spec.name, d)
                    ],
                }
            )
        return out

    def extract(
        self,
        image: Image.Image,
        model_name: str | None = None,
        device: str | None = None,
        max_lines: int | None = None,
    ) -> dict:
        model_name = model_name or settings.default_ocr_model
        spec = OCR_MODELS.get(model_name)
        if spec is None:
            raise UnknownModelError(
                f"OCR model '{model_name}' does not exist. Available: {list(OCR_MODELS)}"
            )

        device = (device or settings.device).lower()
        if device not in spec.devices:
            raise InvalidDeviceError(
                f"Model '{spec.name}' supports {list(spec.devices)}, not '{device}'."
            )
        if device not in available_devices():
            raise InvalidDeviceError(f"Device '{device}' is not available on this machine.")

        # RapidOCR is CPU-only; everything else runs on the requested device.
        effective_device = "cpu" if spec.engine == "rapidocr" else device
        started = time.perf_counter()

        if settings.mock:
            result = self._mock_result(spec)
            return self._finalize(spec, effective_device, result, started)

        if spec.engine == "trocr":
            check_vision_backend()

        try:
            model = self._registry.ensure_loaded(spec.name, effective_device)
        except KeyError as exc:
            raise UnknownModelError(str(exc)) from exc
        except ModelBackendError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ModelBackendError(
                f"Could not load model '{spec.name}' ({spec.hf_id}): {exc}"
            ) from exc

        try:
            if spec.engine == "rapidocr":
                raw = model.predict(image)
                result = {"text": raw["text"], "items": raw["items"]}
            else:  # trocr: read the page line by line
                lines = segment_lines(image, max_lines=max_lines or settings.max_ocr_lines)
                texts = [model.predict(crop) for crop in lines]
                result = {"text": "\n".join(t for t in texts if t), "lines": texts}
        except Exception as exc:  # noqa: BLE001
            raise ModelBackendError(f"OCR inference failed: {exc}") from exc

        return self._finalize(spec, effective_device, result, started)

    @staticmethod
    def _mock_result(spec) -> dict:
        if spec.engine == "rapidocr":
            items = [
                {
                    "text": line,
                    "score": 0.99,
                    "box": [[10.0, 10 + 30 * i], [320.0, 10 + 30 * i], [320.0, 32 + 30 * i], [10.0, 32 + 30 * i]],
                }
                for i, line in enumerate(_MOCK_LINES)
            ]
            return {"text": "\n".join(_MOCK_LINES), "items": items}
        return {"text": "\n".join(_MOCK_LINES), "lines": _MOCK_LINES}

    @staticmethod
    def _finalize(spec, device: str, result: dict, started: float) -> dict:
        return {
            "model": spec.name,
            "engine": spec.engine,
            "mode": spec.kind,
            "device": device,
            "mock": settings.mock,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            "text": result.get("text", ""),
            "lines": result.get("lines"),
            "items": result.get("items"),
        }
