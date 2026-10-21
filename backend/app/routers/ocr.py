"""ROUTER — /ocr: accept an uploaded image and return text / structured JSON."""

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from schemas.common import ErrorResponse
from schemas.ocr import OCRModelInfo, OCRResponse
from services.ocr_service import OCRService
from services.preprocess import load_image_from_bytes

router = APIRouter(prefix="/ocr", tags=["ocr"])


def get_service(request: Request) -> OCRService:
    return request.app.state.ocr_service


@router.get(
    "/models",
    response_model=list[OCRModelInfo],
    summary="List available OCR models",
    description="Returns every OCR model, the engine behind it, and the devices it can run on.",
)
def list_models(service: OCRService = Depends(get_service)):
    return service.list_models()


@router.post(
    "/upload",
    response_model=OCRResponse,
    summary="Run OCR on an uploaded image (multipart/form-data)",
    description=(
        "Upload an image and choose a model and device. "
        "RapidOCR runs on CPU; TrOCR models run on CPU or GPU (cuda)."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid device or undecodable image"},
        413: {"model": ErrorResponse, "description": "Image larger than the configured limit"},
        503: {"model": ErrorResponse, "description": "Model backend could not run"},
    },
)
async def ocr_upload(
    file: UploadFile = File(..., description="Invoice or document image"),
    model: str | None = Form(None, description="OCR model name (defaults to the server default)"),
    device: str | None = Form(None, description="Device to run on: cpu or cuda"),
    service: OCRService = Depends(get_service),
):
    image = load_image_from_bytes(await file.read())
    return service.extract(image, model_name=model, device=device)
