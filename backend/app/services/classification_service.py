"""SERVICE LAYER — classification (JSON table input)."""

from __future__ import annotations

import time

from core.errors import ModelBackendError
from models.registry import ModelRegistry
from schemas.classification import IrisFeatures


class ClassificationService:
    def __init__(self, registry: ModelRegistry):
        self._registry = registry

    def info(self) -> dict:
        model = self._registry.ensure_loaded("iris-classifier", "cpu")
        return {
            "model": model.name,
            "algorithm": model.algorithm,
            "dataset": model.dataset,
            "classes": model.target_names or ["setosa", "versicolor", "virginica"],
        }

    def predict(self, payload: IrisFeatures) -> dict:
        started = time.perf_counter()
        try:
            model = self._registry.ensure_loaded("iris-classifier", "cpu")
        except Exception as exc:  # noqa: BLE001
            raise ModelBackendError(f"Could not load the classifier: {exc}") from exc

        raw = model.predict(payload.to_vector())
        scores: dict[str, float] = raw["scores"]
        best_label = max(scores, key=scores.get)
        return {
            "model": model.name,
            "device": "cpu",
            "predicted_label": raw["class_name"],
            "predicted_class": raw["class_index"],
            "confidence": round(float(scores[best_label]), 4),
            "probabilities": [
                {"label": label, "probability": round(score, 4)} for label, score in scores.items()
            ],
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        }
