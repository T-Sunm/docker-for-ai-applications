"""Prepare every external model artifact under MODEL_DIR."""

from __future__ import annotations

import json
import os
import pickle
import shutil
import sys
from importlib.resources import as_file, files
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_DIR / ("src" if (PROJECT_DIR / "src").is_dir() else "app")
sys.path.insert(0, str(APP_DIR))

from core.config import HF_MODELS, MODEL_DIR, hf_token, model_dir  # noqa: E402

IGNORE_PATTERNS = ["*.bin", "*.h5", "*.msgpack", "*.ot", "*.tflite"]
RAPIDOCR_MODELS = (
    "ch_PP-OCRv4_det_infer.onnx",
    "ch_ppocr_mobile_v2.0_cls_infer.onnx",
    "ch_PP-OCRv4_rec_infer.onnx",
)


def prepare_rapidocr() -> None:
    target = model_dir("rapidocr")
    target.mkdir(parents=True, exist_ok=True)
    package_models = files("rapidocr_onnxruntime") / "models"
    for filename in RAPIDOCR_MODELS:
        destination = target / filename
        if destination.exists():
            continue
        with as_file(package_models / filename) as source:
            temporary = target / f"{filename}.tmp"
            shutil.copyfile(source, temporary)
            os.replace(temporary, destination)
    print(f"[ok] RapidOCR ONNX weights -> {target}")


def prepare_hugging_face_models() -> None:
    # Preparation is the one container role that must contact the Hub.
    os.environ["HF_HUB_OFFLINE"] = "0"
    from huggingface_hub import snapshot_download

    for name, (model_id, revision) in HF_MODELS.items():
        target = model_dir(name)
        snapshot_download(
            repo_id=model_id,
            revision=revision,
            local_dir=target,
            token=hf_token(),
            ignore_patterns=IGNORE_PATTERNS,
        )
        print(f"[ok] {model_id}@{revision[:12]} -> {target}")


def prepare_classifier() -> None:
    from sklearn.datasets import load_iris
    from sklearn.linear_model import LogisticRegression

    target = MODEL_DIR / "iris-classifier"
    model_file = target / "model.pkl"
    metadata_file = target / "metadata.json"
    if model_file.exists() and metadata_file.exists():
        print(f"[ok] iris classifier already exists -> {target}")
        return

    target.mkdir(parents=True, exist_ok=True)
    iris = load_iris()
    model = LogisticRegression(max_iter=200, random_state=0).fit(iris.data, iris.target)

    model_tmp = target / "model.pkl.tmp"
    metadata_tmp = target / "metadata.json.tmp"
    with model_tmp.open("wb") as file:
        pickle.dump(model, file)
    metadata_tmp.write_text(
        json.dumps(
            {
                "feature_names": list(iris.feature_names),
                "target_names": list(iris.target_names),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    os.replace(model_tmp, model_file)
    os.replace(metadata_tmp, metadata_file)
    print(f"[ok] iris classifier -> {target}")


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Preparing model artifacts in {MODEL_DIR}")
    prepare_rapidocr()
    prepare_hugging_face_models()
    prepare_classifier()
    print("All model artifacts are ready.")


if __name__ == "__main__":
    main()
