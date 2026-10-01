from .document_handlers import DocumentHandler
from .minio_client import MinioClient


def get_document_handler() -> DocumentHandler:
    """
    Return the active DocumentHandler.

    The handler is looked up from the component registry; if none is
    registered yet, one is created (and auto-registered) based on the
    `document_storage_backend` config value.
    """
    handler = DocumentHandler.get_component()
    if handler is None:
        handler = _create_document_handler()
    return handler


def _create_document_handler() -> DocumentHandler:
    from ...config import Settings

    _config = Settings.get_config(strict=False)
    backend = (getattr(_config, "document_storage_backend", None) or "minio").lower()

    if backend == "minio":
        return MinioClient(
            endpoint=_config.minio_endpoint,
            access_key=_config.minio_access_key,
            secret_key=_config.minio_secret_key,
            secure=_config.minio_secure,
        )

    raise ValueError(f"Unsupported document storage backend: {backend}")
