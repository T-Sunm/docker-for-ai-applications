"""MODEL LAYER — object detection (YOLOS-tiny). Input: an image, output: boxes."""

from __future__ import annotations

import gc
from typing import Any

from core.config import DETECTION_HF_ID, hf_token, offline_only, resolve_hf_source


class ObjectDetector:
    name = "yolos-tiny"
    hf_id = DETECTION_HF_ID

    def __init__(self, device: str):
        self.device = device
        self._pipe: Any = None

    @property
    def is_loaded(self) -> bool:
        return self._pipe is not None

    def load(self) -> None:
        from transformers import pipeline

        device_index = 0 if self.device == "cuda" else -1
        self._pipe = pipeline(
            "object-detection",
            model=resolve_hf_source(self.name),
            device=device_index,
            local_files_only=offline_only(),
            token=hf_token(),
        )

    def predict(self, image, threshold: float = 0.5) -> list[dict]:
        results = self._pipe(image, threshold=threshold)
        return [
            {
                "label": r["label"],
                "score": round(float(r["score"]), 4),
                "box": {k: float(v) for k, v in r["box"].items()},
            }
            for r in results
        ]

    def unload(self) -> None:
        self._pipe = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:  # noqa: BLE001
            pass
