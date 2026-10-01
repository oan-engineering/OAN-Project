"""Domain-specific file validation profiles built on the generic helper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .file_validation import (
    FileValidationProfile,
    parse_csv_set,
    parse_json_int_map,
)

if TYPE_CHECKING:
    from ..config import Settings
    from ..models.enum import DocumentBucket

IMAGE_ICON_PROFILE = FileValidationProfile(
    allowed_mime_types=frozenset({"image/png", "image/jpeg", "image/webp"}),
    allowed_extensions=frozenset({"png", "jpg", "jpeg", "webp"}),
    max_bytes=1 * 1024 * 1024,
    max_width=1024,
    max_height=1024,
    require_filename=False,
    content_mode="image",
)

# Language flags reuse IMAGE_ICON_PROFILE (same rules as register icons).
# Dashboard images allow the UI-documented 1200x600 bound.
DASHBOARD_IMAGE_PROFILE = FileValidationProfile(
    allowed_mime_types=frozenset({"image/png", "image/jpeg", "image/webp"}),
    allowed_extensions=frozenset({"png", "jpg", "jpeg", "webp"}),
    max_bytes=1 * 1024 * 1024,
    max_width=1200,
    max_height=600,
    require_filename=False,
    content_mode="image",
)


def get_upload_validation_profile(
    bucket: "DocumentBucket",
    settings: "Settings",
) -> Optional[FileValidationProfile]:
    """
    Build a bucket-specific upload profile from registry-core Settings.

    Returns ``None`` when the bucket does not require upload validation
    (currently ``data_import_files``).
    """
    from ..models.enum import DocumentBucket

    if bucket == DocumentBucket.DATA_IMPORT_FILES:
        return None

    if bucket == DocumentBucket.TEMPLATES:
        return FileValidationProfile(
            allowed_mime_types=parse_csv_set(settings.template_upload_allowed_mime_types),
            allowed_extensions=parse_csv_set(settings.template_upload_allowed_extensions),
            max_bytes=settings.template_upload_max_bytes,
            max_bytes_by_mime=parse_json_int_map(settings.template_upload_max_bytes_by_mime),
            require_filename=True,
            content_mode="text",
        )

    # DOCUMENTS and DEFAULT
    return FileValidationProfile(
        allowed_mime_types=parse_csv_set(settings.document_upload_allowed_mime_types),
        allowed_extensions=parse_csv_set(settings.document_upload_allowed_extensions),
        max_bytes=settings.document_upload_max_bytes,
        max_bytes_by_mime=parse_json_int_map(settings.document_upload_max_bytes_by_mime),
        require_filename=True,
        content_mode="binary",
    )
