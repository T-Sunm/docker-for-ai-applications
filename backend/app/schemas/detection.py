"""Schemas for the detection router (image input, boxes output)."""

from pydantic import BaseModel, Field


class Box(BaseModel):
    xmin: float
    ymin: float
    xmax: float
    ymax: float


class DetectionObject(BaseModel):
    label: str
    score: float = Field(..., ge=0, le=1)
    box: Box


class DetectionResponse(BaseModel):
    model: str
    device: str
    threshold: float
    count: int
    objects: list[DetectionObject]
    elapsed_ms: float
