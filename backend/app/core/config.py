"""Runtime configuration and model locations."""

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = Path(os.environ.get("MODEL_DIR", BASE_DIR / "model-data"))
HF_MODELS = {
    "trocr-small-printed": (
        "microsoft/trocr-small-printed",
        "04e994ab854b0089d4929f48c2b4dbe2ce78a340",
    ),
    "yolos-tiny": (
        "hustvl/yolos-tiny",
        "95a90f3c189fbfca3bcfc6d7315b9e84d95dc2de",
    ),
}


def model_dir(name: str) -> Path:
    return MODEL_DIR / name


def resolve_hf_source(name: str) -> str:
    """Return only a prepared local artifact; inference never downloads models."""
    path = model_dir(name)
    if not (path / "config.json").exists() or not any(path.glob("*.safetensors")):
        raise FileNotFoundError(
            f"Model '{name}' is missing from {MODEL_DIR}. Run scripts/prepare_models.py first."
        )
    return str(path)


def hf_token() -> str | None:
    token = os.environ.get("HF_TOKEN")
    return token.strip() if token else None


def _flag(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def offline_only() -> bool:
    return _flag("HF_HUB_OFFLINE", False)


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:  # noqa: BLE001
        return False


def available_devices() -> list[str]:
    devices = ["cpu"]
    if cuda_available():
        devices.append("cuda")
    return devices


def resolve_device() -> str:
    requested = os.environ.get("INFERENCE_DEVICE", "cpu").strip().lower()
    return requested if requested in ("cpu", "cuda", "mps") else "cpu"


@dataclass(frozen=True)
class OCRModelSpec:
    name: str
    engine: str
    hf_id: str | None
    kind: str
    description: str
    devices: tuple[str, ...]


OCR_MODELS: dict[str, OCRModelSpec] = {
    "rapidocr": OCRModelSpec(
        name="rapidocr",
        engine="rapidocr",
        hf_id=None,
        kind="document",
        description="RapidOCR (ONNX Runtime) - full-page OCR on CPU",
        devices=("cpu",),
    ),
    "trocr-small-printed": OCRModelSpec(
        name="trocr-small-printed",
        engine="trocr",
        hf_id=HF_MODELS["trocr-small-printed"][0],
        kind="line",
        description="TrOCR small (printed) - printed text per line",
        devices=("cpu", "cuda"),
    ),
}

DETECTION_HF_ID = HF_MODELS["yolos-tiny"][0]


@dataclass(frozen=True)
class Settings:
    device: str = field(default_factory=resolve_device)
    mock: bool = field(default_factory=lambda: _flag("MOCK_MODE", False))
    default_ocr_model: str = field(
        default_factory=lambda: os.environ.get("DEFAULT_OCR_MODEL", "rapidocr")
    )
    max_ocr_lines: int = field(default_factory=lambda: _int("MAX_OCR_LINES", 20))
    detection_threshold: float = 0.5
    max_upload_mb: int = field(default_factory=lambda: _int("MAX_UPLOAD_MB", 10))

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
