"""ROUTER — /classification: JSON table input."""

from fastapi import APIRouter, Depends, Request

from schemas.classification import ClassificationResponse, ClassifierInfo, IrisFeatures
from schemas.common import ErrorResponse
from services.classification_service import ClassificationService

router = APIRouter(prefix="/classification", tags=["classification"])


def get_service(request: Request) -> ClassificationService:
    return request.app.state.classification_service


@router.get("/info", response_model=ClassifierInfo, summary="Describe the classifier")
def info(service: ClassificationService = Depends(get_service)):
    return service.info()


@router.post(
    "/predict",
    response_model=ClassificationResponse,
    summary="Predict the Iris species",
    responses={
        422: {"model": ErrorResponse, "description": "Request body does not match the schema"},
        503: {"model": ErrorResponse, "description": "Model backend could not run"},
    },
)
def predict(payload: IrisFeatures, service: ClassificationService = Depends(get_service)):
    return service.predict(payload)
