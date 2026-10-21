"""Domain errors that already know their HTTP status code, so clients get meaningful errors."""


class ServiceError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class UnknownModelError(ServiceError):
    status_code = 404
    code = "UNKNOWN_MODEL"


class InvalidDeviceError(ServiceError):
    status_code = 400
    code = "INVALID_DEVICE"


class ImageDecodeError(ServiceError):
    status_code = 400
    code = "INVALID_IMAGE"


class ImageTooLargeError(ServiceError):
    status_code = 413
    code = "IMAGE_TOO_LARGE"


class ModelBackendError(ServiceError):
    """Library missing / weights not downloadable / inference failed."""

    status_code = 503
    code = "MODEL_BACKEND_ERROR"
