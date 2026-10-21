"""ROUTER — /detection: image input, boxes output."""

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from schemas.common import ErrorResponse
from schemas.detection import DetectionResponse
from services.detection_service import DetectionService
from services.preprocess import load_image_from_bytes

router = APIRouter(prefix="/detection", tags=["detection"])


def get_service(request: Request) -> DetectionService:
    return request.app.state.detection_service


@router.post(
    "/upload",
    response_model=DetectionResponse,
    summary="Detect objects in an uploaded image",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid device or undecodable image"},
        503: {"model": ErrorResponse, "description": "Model backend could not run"},
    },
)
async def detect_upload(
    file: UploadFile = File(..., description="Image to analyze"),
    threshold: float = Form(0.5, description="Minimum confidence score (0-1)"),
    device: str | None = Form(None, description="Device to run on: cpu or cuda"),
    service: DetectionService = Depends(get_service),
):
    image = load_image_from_bytes(await file.read())
    return service.detect(image, threshold=threshold, device=device)
