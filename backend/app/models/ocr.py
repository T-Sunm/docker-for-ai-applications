"""
OCR model wrappers. Every wrapper follows the same contract: load() / predict() / unload(),
so the registry and the service never need to know implementation details.

Engines:
  - RapidOCREngine : ONNX Runtime, CPU only, detects + reads all text on the page.
  - TrOCRLineModel : PyTorch transformer, reads ONE printed text line.

Weights come from MODEL_DIR, filled by `scripts/prepare_models.py`.
"""

from __future__ import annotations

import gc
from typing import Any

import numpy as np

from core.config import OCRModelSpec, hf_token, model_dir, offline_only, resolve_hf_source


def _free_memory() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        pass


class RapidOCREngine:
    """RapidOCR (ONNX Runtime): full-page text detection + recognition, optimized for CPU."""

    def __init__(self, spec: OCRModelSpec, device: str):
        self.spec = spec
        self.device = "cpu"  # RapidOCR runs on CPU only
        self._engine: Any = None

    @property
    def is_loaded(self) -> bool:
        return self._engine is not None

    def load(self) -> None:
        from rapidocr_onnxruntime import RapidOCR

        path = model_dir("rapidocr")
        required = {
            "det_model_path": path / "ch_PP-OCRv4_det_infer.onnx",
            "cls_model_path": path / "ch_ppocr_mobile_v2.0_cls_infer.onnx",
            "rec_model_path": path / "ch_PP-OCRv4_rec_infer.onnx",
        }
        missing = [str(file) for file in required.values() if not file.exists()]
        if missing:
            raise FileNotFoundError(
                f"RapidOCR artifacts are missing: {missing}. Run scripts/prepare_models.py first."
            )
        self._engine = RapidOCR(**{name: str(file) for name, file in required.items()})

    def predict(self, image) -> dict:
        # RapidOCR expects a BGR numpy array (OpenCV convention).
        array = np.array(image.convert("RGB"))[:, :, ::-1]
        result, _elapsed = self._engine(array)

        items = []
        for box, text, score in result or []:
            items.append(
                {
                    "text": text,
                    "score": round(float(score), 4),
                    "box": [[round(float(x), 2), round(float(y), 2)] for x, y in box],
                }
            )
        items.sort(key=lambda item: (item["box"][0][1], item["box"][0][0]))
        return {"text": "\n".join(item["text"] for item in items), "items": items}

    def unload(self) -> None:
        self._engine = None
        _free_memory()


class TrOCRLineModel:
    """TrOCR: recognizes ONE text line. Uses Processor + Model directly (stable across versions)."""

    def __init__(self, spec: OCRModelSpec, device: str):
        self.spec = spec
        self.hf_id = spec.hf_id
        self.device = device
        self._processor: Any = None
        self._model: Any = None
        self._torch: Any = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        import torch
        from transformers import AutoImageProcessor, AutoTokenizer, VisionEncoderDecoderModel

        local_files_only = offline_only()
        token = hf_token()
        source = resolve_hf_source(self.spec.name)
        self._torch = torch
        self._processor = AutoImageProcessor.from_pretrained(
            source, local_files_only=local_files_only, token=token
        )
        self._tokenizer = AutoTokenizer.from_pretrained(
            source, local_files_only=local_files_only, token=token
        )
        self._model = VisionEncoderDecoderModel.from_pretrained(
            source, local_files_only=local_files_only, token=token
        ).to(self.device)
        self._model.eval()

    def predict(self, image, max_new_tokens: int = 64) -> str:
        torch = self._torch
        pixel_values = self._processor(images=image.convert("RGB"), return_tensors="pt").pixel_values.to(
            self.device
        )
        with torch.no_grad():
            generated = self._model.generate(pixel_values, max_new_tokens=max_new_tokens)
        return self._tokenizer.batch_decode(generated, skip_special_tokens=True)[0].strip()

    def unload(self) -> None:
        self._model = None
        self._processor = None
        self._tokenizer = None
        _free_memory()


def build_ocr_model(spec: OCRModelSpec, device: str):
    """Pick the wrapper that matches the spec's engine."""
    if spec.engine == "rapidocr":
        return RapidOCREngine(spec, device)
    return TrOCRLineModel(spec, device)
