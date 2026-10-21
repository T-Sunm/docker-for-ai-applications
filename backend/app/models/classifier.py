"""MODEL LAYER — classifier (Logistic Regression / Iris). Input: a table of numbers (JSON)."""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np


class IrisClassifier:
    name = "iris-classifier"
    algorithm = "LogisticRegression"
    dataset = "iris"

    def __init__(self, model_path: Path, meta_path: Path, device: str = "cpu"):
        self.device = "cpu"  # scikit-learn runs on CPU
        self._model_path = model_path
        self._meta_path = meta_path
        self._model = None
        self._target_names: list[str] = []

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        with open(self._model_path, "rb") as f:
            self._model = pickle.load(f)
        self._target_names = json.loads(self._meta_path.read_text(encoding="utf-8"))["target_names"]

    def unload(self) -> None:
        self._model = None
        self._target_names = []

    def predict(self, features: list[float]) -> dict:
        x = np.asarray(features, dtype=float).reshape(1, -1)
        index = int(self._model.predict(x)[0])
        scores = self._model.predict_proba(x)[0]
        return {
            "class_index": index,
            "class_name": self._target_names[index],
            "scores": {n: float(p) for n, p in zip(self._target_names, scores)},
        }

    @property
    def target_names(self) -> list[str]:
        return self._target_names
