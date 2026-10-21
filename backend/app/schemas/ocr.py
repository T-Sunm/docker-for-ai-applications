"""Schemas for the OCR router."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OCRModelInfo(BaseModel):
    name: str = Field(..., description="Model identifier used by the API")
    engine: str = Field(..., description="Underlying engine: rapidocr | trocr")
    hf_id: str | None = Field(None, description="HuggingFace id, if any")
    kind: Literal["line", "document"] = Field(..., description="Whether it reads a line or a whole page")
    description: str
    devices: list[str] = Field(..., description="Devices this model can run on")
    loaded_on: list[str] = Field(default_factory=list, description="Devices where it is currently loaded")


class OCRItem(BaseModel):
    text: str
    score: float = Field(..., ge=0, le=1)
    box: list[list[float]] = Field(..., description="Four [x, y] points around the text")


class OCRResponse(BaseModel):
    model: str
    engine: str
    mode: Literal["line", "document"]
    device: str = Field(..., description="Device that actually ran the model")
    mock: bool
    elapsed_ms: float
    text: str = Field(..., description="All recognized text, joined by newlines")
    lines: list[str] | None = Field(None, description="Recognized text per line (line models)")
    items: list[OCRItem] | None = Field(None, description="Text with boxes (detection-based models)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model": "rapidocr",
                "engine": "rapidocr",
                "mode": "document",
                "device": "cpu",
                "mock": False,
                "elapsed_ms": 4200.5,
                "text": "INVOICE\nTotal: 750000 VND",
                "lines": None,
                "items": [{"text": "INVOICE", "score": 0.98, "box": [[10, 10], [120, 10], [120, 30], [10, 30]]}],
            }
        }
    )
