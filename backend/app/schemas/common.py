"""Shared schemas: the error contract and system status models."""

from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Every error is returned with this exact structure."""

    error: ErrorDetail

    model_config = ConfigDict(
        json_schema_extra={"example": {"error": {"code": "INVALID_IMAGE", "message": "Could not decode image"}}}
    )


class DeviceInfo(BaseModel):
    default: str
    devices: list[str]


class ModelEntry(BaseModel):
    name: str
    task: str
    loaded: bool
    loaded_on: list[str]
    hf_id: str | None = None


class ModelsStatusResponse(BaseModel):
    device: str
    mock: bool
    models: list[ModelEntry]
