"""ROUTER — system: /health, /devices, /models (status and manual unload)."""

from fastapi import APIRouter, Request

from core.config import DETECTION_HF_ID, OCR_MODELS, available_devices, settings
from core.errors import UnknownModelError
from schemas.common import DeviceInfo, ModelEntry, ModelsStatusResponse

router = APIRouter(tags=["system"])


def _task_and_hf_id(key: str) -> tuple[str, str | None]:
    if key in OCR_MODELS:
        return "ocr", OCR_MODELS[key].hf_id
    if key == "iris-classifier":
        return "classification", None
    if key == "yolos-tiny":
        return "detection", DETECTION_HF_ID
    return "unknown", None


def _models_payload(request: Request) -> dict:
    registry = request.app.state.registry
    entries = []
    for item in registry.status():
        task, hf_id = _task_and_hf_id(item["name"])
        entries.append(
            ModelEntry(
                name=item["name"],
                task=task,
                loaded=item["loaded"],
                loaded_on=item["loaded_on"],
                hf_id=hf_id,
            )
        )
    return {"device": settings.device, "mock": settings.mock, "models": entries}


@router.get("/health", summary="Liveness check")
def health():
    return {"status": "ok", "device": settings.device, "mock": settings.mock}


@router.get("/devices", response_model=DeviceInfo, summary="List available devices")
def devices():
    return {"default": settings.device, "devices": available_devices()}


@router.get("/models", response_model=ModelsStatusResponse, summary="Status of every model")
def models(request: Request):
    return _models_payload(request)


@router.post(
    "/models/{name}/unload",
    response_model=ModelsStatusResponse,
    summary="Release a model from memory",
)
def unload(name: str, request: Request):
    registry = request.app.state.registry
    if not registry.has(name):
        raise UnknownModelError(f"There is no model named '{name}'")
    registry.unload(name)
    return _models_payload(request)
