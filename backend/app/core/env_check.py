"""
Sanity check for the vision backend (torch + torchvision) before loading image models.

`transformers` uses `torchvision` for image pipelines. If torch and torchvision versions
do not match, `import torchvision` fails (e.g. "operator torchvision::nms does not exist").
We turn that cryptic failure into a clear, actionable message.
"""

from core.errors import ModelBackendError


def check_vision_backend() -> None:
    try:
        import torch  # noqa: F401
        import torchvision  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        raise ModelBackendError(
            "Vision backend (torch/torchvision) could not be loaded. This usually means torch "
            "and torchvision versions do not match. Fix it by installing a matching torchvision, "
            "e.g. `pip install --upgrade torchvision`, then try again. You can also run in mock "
            f"mode to demo the UI: MOCK_MODE=1. Details: {exc}"
        ) from exc
