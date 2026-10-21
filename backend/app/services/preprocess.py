"""Image preprocessing: decode uploaded bytes and split an image into text lines."""

from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image

from core.config import settings
from core.errors import ImageDecodeError, ImageTooLargeError


def load_image_from_bytes(data: bytes) -> Image.Image:
    """Decode raw bytes into an RGB image, with size/shape validation."""
    if not data:
        raise ImageDecodeError("Empty file.")
    if len(data) > settings.max_upload_bytes:
        raise ImageTooLargeError(f"Image exceeds the {settings.max_upload_mb} MB limit.")
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except Exception as exc:  # noqa: BLE001
        raise ImageDecodeError(f"Could not decode image: {exc}") from exc
    return image.convert("RGB")


def segment_lines(
    image: Image.Image, max_lines: int = 20, min_height: int = 8, pad: int = 4
) -> list[Image.Image]:
    """
    Split an image into text lines using horizontal projection.

    Idea: dark pixels = text.
      1. Sum dark pixels per row -> mark rows that contain text.
      2. Consecutive text rows form one line.
      3. Crop tightly to the text bounding box (not the full width) so TrOCR only
         "sees" the text — this improves results a lot.
      4. Upscale very short lines so they are easier to read.
    """
    grayscale = np.array(image.convert("L"))
    is_text = grayscale < 200

    row_has_text = is_text.sum(axis=1) > 0
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for i, has_text in enumerate(row_has_text):
        if has_text and start is None:
            start = i
        elif not has_text and start is not None:
            if i - start >= min_height:
                spans.append((start, i))
            start = None
    if start is not None and len(row_has_text) - start >= min_height:
        spans.append((start, len(row_has_text)))

    crops: list[Image.Image] = []
    for top, bottom in spans:
        band = is_text[top:bottom]
        col_has_text = band.sum(axis=0) > 0
        if not col_has_text.any():
            continue
        cols = np.where(col_has_text)[0]
        left, right = int(cols[0]), int(cols[-1])

        box = (
            max(0, left - pad),
            max(0, top - pad),
            min(image.width, right + pad + 1),
            min(image.height, bottom + pad + 1),
        )
        crop = image.crop(box)

        if 0 < crop.height < 32:
            scale = 32 / crop.height
            crop = crop.resize((max(1, int(crop.width * scale)), 32))

        crops.append(crop)
        if len(crops) >= max_lines:
            break

    return crops
