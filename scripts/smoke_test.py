"""Run a small end-to-end check against a running backend."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
import uuid


def request(url: str, *, data: bytes | None = None, content_type: str | None = None, timeout: int) -> dict:
    headers = {"Content-Type": content_type} if content_type else {}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{exc.code} {exc.reason}: {detail}") from exc


def multipart_image(fields: dict[str, str]) -> tuple[bytes, str]:
    boundary = f"smoke-{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )

    # A valid PPM image keeps the smoke test dependency-free.
    width, height = 320, 120
    pixels = bytearray(b"\xff" * width * height * 3)
    for top, bottom in ((25, 40), (65, 80)):
        for y in range(top, bottom):
            for x in range(30, 290):
                offset = (y * width + x) * 3
                pixels[offset : offset + 3] = b"\x00\x00\x00"
    image = f"P6\n{width} {height}\n255\n".encode() + pixels
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="smoke.ppm"\r\n'
        "Content-Type: image/x-portable-pixmap\r\n\r\n".encode()
        + image
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    health = request(f"{base_url}/health", timeout=args.timeout)
    check(health.get("status") == "ok", "health endpoint did not return status=ok")
    check(health.get("mock") is False, "backend is running in mock mode")
    print("[ok] health")

    classification_body = json.dumps(
        {"sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4, "petal_width": 0.2}
    ).encode()
    classification = request(
        f"{base_url}/classification/predict",
        data=classification_body,
        content_type="application/json",
        timeout=args.timeout,
    )
    check(classification.get("model") == "iris-classifier", "classification used an unexpected model")
    check(classification.get("predicted_label") in {"setosa", "versicolor", "virginica"}, "invalid classification result")
    print("[ok] classification")

    ocr_body, ocr_type = multipart_image({"model": "rapidocr", "device": "cpu"})
    ocr = request(
        f"{base_url}/ocr/upload",
        data=ocr_body,
        content_type=ocr_type,
        timeout=args.timeout,
    )
    check(ocr.get("model") == "rapidocr" and ocr.get("mock") is False, "RapidOCR inference did not run")
    print("[ok] ocr")

    detection_body, detection_type = multipart_image({"threshold": "0.5", "device": "cpu"})
    detection = request(
        f"{base_url}/detection/upload",
        data=detection_body,
        content_type=detection_type,
        timeout=args.timeout,
    )
    check(detection.get("model") == "yolos-tiny", "YOLOS inference did not run")
    print("[ok] detection")

    print("Smoke test passed.")


if __name__ == "__main__":
    main()
