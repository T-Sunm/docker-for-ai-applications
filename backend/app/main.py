"""
Part 6 — Multi-model AI server
==============================
Problem: a real AI server serves MANY tasks, some models are heavy, inputs can be images,
and compute needs differ. How do we manage many models without turning the API into a mess?

How it is organized:
  - One ROUTER per task: /ocr, /classification, /detection
  - One WRAPPER per model in models/, all sharing the same load/predict/unload contract
  - A REGISTRY that manages the MODEL LIFECYCLE (lazy load per device, release on demand)
  - A SERVICE that orchestrates: preprocess image -> call model -> shape the result

OCR is the main use case:
  input image -> [image encoder] -> [text decoder] -> text / structured JSON

All models run LOCALLY in this process (loaded with torch / onnxruntime / scikit-learn).
No remote inference API is used.

Run from backend/:
  python scripts/prepare_models.py
  cd app && uvicorn main:app --reload --port 8000
Open:
  http://127.0.0.1:8000/docs

Demo without model inference:
  set MOCK_MODE=1 && uvicorn main:app --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import MODEL_DIR, OCR_MODELS, settings
from core.errors import ServiceError
from models.classifier import IrisClassifier
from models.detector import ObjectDetector
from models.ocr import build_ocr_model
from models.registry import ModelRegistry
from routers import classification, detection, ocr, system
from services.classification_service import ClassificationService
from services.detection_service import DetectionService
from services.ocr_service import OCRService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # REGISTRY: register a factory per model (keyed by name). Models are NOT loaded here.
    registry = ModelRegistry()
    for spec in OCR_MODELS.values():
        registry.register(spec.name, lambda device, spec=spec: build_ocr_model(spec, device))
    registry.register(
        "iris-classifier",
        lambda device: IrisClassifier(
            MODEL_DIR / "iris-classifier" / "model.pkl",
            MODEL_DIR / "iris-classifier" / "metadata.json",
            device,
        ),
    )
    registry.register("yolos-tiny", lambda device: ObjectDetector(device))

    # SERVICES: one per task, all sharing the registry.
    app.state.registry = registry
    app.state.ocr_service = OCRService(registry)
    app.state.classification_service = ClassificationService(registry)
    app.state.detection_service = DetectionService(registry)

    print(f"[startup] device={settings.device} mock={settings.mock} - models load lazily on demand")
    yield

    # SHUTDOWN: release all models.
    registry.unload_all()
    print("[shutdown] released all models")


app = FastAPI(
    title="Multi-model AI Server",
    description=(
        "A FastAPI server exposing OCR, classification and detection models that run locally. "
        "Choose the device (CPU or GPU) per request where the model supports it. "
        "The Streamlit UI is OCR-only; the classification and detection endpoints are meant to be "
        "called directly through the API."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["System"])
async def root():
    return {"message": "AI inference API is running", "docs": "/docs"}


# ---------------------------------------------------------------------------
# ERROR HANDLERS - every error uses the same contract {"error": {"code", "message"}}
# ---------------------------------------------------------------------------
@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": str(exc)}})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": "Invalid request", "details": exc.errors()}},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}
    )


# ---------------------------------------------------------------------------
# ROUTERS - one per task
# ---------------------------------------------------------------------------
app.include_router(system.router)
app.include_router(ocr.router)
app.include_router(classification.router)
app.include_router(detection.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000)
