"""Generic file validation primitives for registry-core.

This module is domain-agnostic: callers supply a ``FileValidationProfile``.
Domain presets (icons, document buckets, etc.) live in
``file_validation_profiles``.
"""

from __future__ import annotations

import base64
import binascii
import io
import json
import re
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Literal, Mapping, Optional, Set, Tuple

import filetype
from PIL import Image, UnidentifiedImageError

from ..errors import G2PRegistryErrorCodes, G2PRegistryException

_DATA_URL_RE = re.compile(
    r"^data:(?P<mime>[\w/+.-]+);base64,(?P<data>.+)$",
    re.IGNORECASE | re.DOTALL,
)

# Used when content_mode="text" or as a fallback after filetype misses.
_EXTENSION_MIME_HINTS: Mapping[str, str] = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
    "pdf": "application/pdf",
    "csv": "text/csv",
    "tsv": "text/tab-separated-values",
    "json": "application/json",
    "jsonl": "application/x-ndjson",
    "xml": "application/xml",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "json.j2": "text/plain",
    "j2": "text/plain",
}

ContentMode = Literal["binary", "text", "image"]


@dataclass(frozen=True)
class FileValidationProfile:
    """Declarative rules for validating an uploaded or embedded file."""

    allowed_mime_types: FrozenSet[str]
    allowed_extensions: FrozenSet[str]
    max_bytes: int
    max_width: Optional[int] = None
    max_height: Optional[int] = None
    require_filename: bool = False
    max_bytes_by_mime: Mapping[str, int] = field(default_factory=dict)
    # binary: filetype (+ text heuristics if needed)
    # text: UTF-8 only; MIME from extension hints
    # image: binary sniff must be image; dimensions via Pillow when limits set
    content_mode: ContentMode = "binary"


@dataclass(frozen=True)
class FileValidationResult:
    mime_type: str
    size: int
    width: Optional[int] = None
    height: Optional[int] = None
    extension: Optional[str] = None


def _raise(code: G2PRegistryErrorCodes, message: str) -> None:
    raise G2PRegistryException(code=code.value[1], message=message)


def parse_csv_set(value: str) -> FrozenSet[str]:
    """Parse a comma-separated list into a lowercase frozenset."""
    return frozenset(part.strip().lower().lstrip(".") for part in value.split(",") if part.strip())


def parse_json_int_map(value: str | Mapping[str, int] | None) -> Dict[str, int]:
    """Parse a JSON object (or mapping) of string keys to ints."""
    if value is None or value == "" or value == {}:
        return {}
    if isinstance(value, Mapping):
        return {str(k).lower(): int(v) for k, v in value.items()}
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        _raise(
            G2PRegistryErrorCodes.INVALID_REQUEST,
            f"Invalid JSON int map: {exc}",
        )
        raise  # pragma: no cover
    if not isinstance(parsed, dict):
        _raise(
            G2PRegistryErrorCodes.INVALID_REQUEST,
            "Expected a JSON object mapping keys to integers.",
        )
    return {str(k).lower(): int(v) for k, v in parsed.items()}


def match_allowed_extension(basename: str, allowed_extensions: Set[str]) -> Optional[str]:
    """Return the longest allowlisted extension matching ``basename``'s suffix."""
    lower = basename.lower()
    allowed = {ext.lower().lstrip(".") for ext in allowed_extensions}
    for extension in sorted(allowed, key=len, reverse=True):
        suffix = f".{extension}"
        if lower.endswith(suffix) and len(basename) > len(suffix):
            return extension
    return None


def validate_filename(
    filename: str,
    allowed_extensions: Set[str],
    *,
    require_single_extension: bool = True,
) -> str:
    """
    Validate a filename against an extension allowlist.

    Supports compound extensions (e.g. ``json.j2``) via longest-suffix match.
    When ``require_single_extension`` is True, the stem must not contain ``.``
    (rejects ``evil.php.png`` / ``evil.php.json.j2``).
    """
    if not filename or not filename.strip():
        _raise(G2PRegistryErrorCodes.INVALID_FILE_NAME, "Filename is required.")

    name = filename.strip()
    if "\x00" in name or "/" in name or "\\" in name:
        _raise(
            G2PRegistryErrorCodes.INVALID_FILE_NAME,
            "Filename contains invalid characters.",
        )

    basename = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if basename.startswith(".") or basename.endswith("."):
        _raise(
            G2PRegistryErrorCodes.INVALID_FILE_NAME,
            "Filename must have a valid extension.",
        )

    extension = match_allowed_extension(basename, allowed_extensions)
    if extension is None:
        allowed = ", ".join(sorted({e.lstrip(".") for e in allowed_extensions}))
        _raise(
            G2PRegistryErrorCodes.INVALID_FILE_TYPE,
            f"File extension is not allowed for '{basename}'. Allowed: {allowed}.",
        )

    stem = basename[: -(len(extension) + 1)]
    if not stem:
        _raise(
            G2PRegistryErrorCodes.INVALID_FILE_NAME,
            "Filename must have a non-empty name before the extension.",
        )
    if require_single_extension and "." in stem:
        _raise(
            G2PRegistryErrorCodes.INVALID_FILE_NAME,
            "Filename must contain exactly one allowlisted extension "
            "(multiple extensions are not allowed).",
        )
    return extension


def enforce_size(
    size: int,
    *,
    max_bytes: int,
    mime_type: Optional[str] = None,
    max_bytes_by_mime: Optional[Mapping[str, int]] = None,
) -> None:
    """Enforce absolute and optional per-MIME size limits."""
    limit = max_bytes
    if mime_type and max_bytes_by_mime:
        limit = max_bytes_by_mime.get(mime_type.lower(), max_bytes)
    if size > limit:
        suffix = f" for MIME type '{mime_type}'" if mime_type else ""
        _raise(
            G2PRegistryErrorCodes.FILE_TOO_LARGE,
            f"File size ({size} bytes) exceeds maximum of {limit} bytes{suffix}.",
        )


def decode_base64_input(value: str) -> bytes:
    """Decode a data URL or raw base64 string into bytes."""
    if value is None:
        _raise(G2PRegistryErrorCodes.INVALID_FILE_CONTENT, "Value is required.")

    raw = value.strip()
    if not raw:
        _raise(G2PRegistryErrorCodes.INVALID_FILE_CONTENT, "Value is empty.")

    match = _DATA_URL_RE.match(raw)
    payload = "".join((match.group("data") if match else raw).split())
    try:
        return base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        _raise(G2PRegistryErrorCodes.INVALID_FILE_CONTENT, "Invalid base64 encoding.")
        raise  # pragma: no cover


def to_data_url(data: bytes, mime_type: str) -> str:
    """Encode bytes as a ``data:<mime>;base64,...`` URL."""
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def read_image_dimensions(data: bytes) -> Tuple[int, int, str]:
    """
    Open image bytes with Pillow and return ``(width, height, mime_type)``.

    MIME is derived from Pillow's detected format.
    """
    format_to_mime = {
        "PNG": "image/png",
        "JPEG": "image/jpeg",
        "WEBP": "image/webp",
        "GIF": "image/gif",
    }
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            pil_format = (image.format or "").upper()
            width, height = image.size
    except UnidentifiedImageError:
        _raise(
            G2PRegistryErrorCodes.INVALID_FILE_CONTENT,
            "File content could not be identified as a valid image.",
        )
        raise  # pragma: no cover
    except OSError as exc:
        _raise(
            G2PRegistryErrorCodes.INVALID_FILE_CONTENT,
            f"File content could not be decoded: {exc}",
        )
        raise  # pragma: no cover

    mime_type = format_to_mime.get(pil_format)
    if not mime_type:
        _raise(
            G2PRegistryErrorCodes.INVALID_FILE_TYPE,
            f"Detected image format '{pil_format or 'unknown'}' is not supported.",
        )
    return width, height, mime_type


def _is_json_line(line: str) -> bool:
    try:
        json.loads(line)
        return True
    except json.JSONDecodeError:
        return False


def _sniff_text_mime(data: bytes, extension: Optional[str] = None) -> Optional[str]:
    """Best-effort MIME for text-like payloads when filetype cannot classify."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None

    stripped = text.lstrip()
    if stripped.startswith("<"):
        return "application/xml"

    if stripped[:1] in "{[":
        try:
            json.loads(text)
            return "application/json"
        except json.JSONDecodeError:
            lines = [line for line in text.splitlines() if line.strip()]
            if lines and all(_is_json_line(line) for line in lines[:20]):
                return "application/x-ndjson"

    lines = [line for line in text.splitlines() if line.strip()]
    sample = lines[:10]
    if extension == "jsonl" and sample and all(_is_json_line(line) for line in sample):
        return "application/x-ndjson"
    if extension == "tsv" or (sample and any("\t" in line for line in sample) and not any("," in line for line in sample)):
        return "text/tab-separated-values"
    if extension == "csv" or (sample and any("," in line for line in sample)):
        return "text/csv"
    if extension and extension in _EXTENSION_MIME_HINTS:
        return _EXTENSION_MIME_HINTS[extension]
    return None


def sniff_mime_type(
    data: bytes,
    *,
    extension: Optional[str] = None,
    allow_text_fallback: bool = True,
) -> str:
    """
    Detect MIME type from content using ``filetype``, with optional text fallback.

    Never trusts a client-supplied Content-Type.
    """
    kind = filetype.guess(data)
    if kind is not None and kind.mime:
        return kind.mime.lower()

    if allow_text_fallback:
        guessed = _sniff_text_mime(data, extension)
        if guessed:
            return guessed

    _raise(
        G2PRegistryErrorCodes.INVALID_FILE_CONTENT,
        "File content could not be identified as an allowed type.",
    )
    raise  # pragma: no cover


def sniff_text_mime(data: bytes, extension: Optional[str] = None) -> str:
    """Require UTF-8 text and derive MIME from extension hints / content."""
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        _raise(
            G2PRegistryErrorCodes.INVALID_FILE_CONTENT,
            "Content must be valid UTF-8 text.",
        )
        raise  # pragma: no cover

    if extension and extension in _EXTENSION_MIME_HINTS:
        return _EXTENSION_MIME_HINTS[extension]
    return "text/plain"


def validate_file_bytes(
    data: bytes,
    profile: FileValidationProfile,
    filename: Optional[str] = None,
) -> FileValidationResult:
    """Validate bytes against a profile (filename, size, MIME, optional dimensions)."""
    if profile.require_filename and not filename:
        _raise(G2PRegistryErrorCodes.INVALID_FILE_NAME, "Filename is required.")

    matched_extension: Optional[str] = None
    if filename is not None:
        matched_extension = validate_filename(
            filename,
            set(profile.allowed_extensions),
        )

    if not data:
        _raise(G2PRegistryErrorCodes.INVALID_FILE_CONTENT, "File content is empty.")

    size = len(data)
    enforce_size(size, max_bytes=profile.max_bytes)

    width: Optional[int] = None
    height: Optional[int] = None

    if profile.content_mode == "text":
        mime_type = sniff_text_mime(data, matched_extension)
    elif profile.content_mode == "image":
        mime_type = sniff_mime_type(data, extension=matched_extension, allow_text_fallback=False)
        if not mime_type.startswith("image/"):
            _raise(
                G2PRegistryErrorCodes.INVALID_FILE_TYPE,
                f"Detected file type '{mime_type}' is not an image.",
            )
        if profile.max_width is not None or profile.max_height is not None:
            width, height, pillow_mime = read_image_dimensions(data)
            # Prefer Pillow MIME when available (normalized)
            mime_type = pillow_mime
    else:
        mime_type = sniff_mime_type(data, extension=matched_extension, allow_text_fallback=True)

    if mime_type not in profile.allowed_mime_types:
        allowed = ", ".join(sorted(profile.allowed_mime_types))
        _raise(
            G2PRegistryErrorCodes.INVALID_FILE_TYPE,
            f"Detected file type '{mime_type}' is not allowed. Allowed MIME types: {allowed}.",
        )

    enforce_size(
        size,
        max_bytes=profile.max_bytes,
        mime_type=mime_type,
        max_bytes_by_mime=profile.max_bytes_by_mime,
    )

    if profile.max_width is not None or profile.max_height is not None:
        if width is None or height is None:
            width, height, _ = read_image_dimensions(data)
        if profile.max_width is not None and width > profile.max_width:
            _raise(
                G2PRegistryErrorCodes.INVALID_IMAGE_DIMENSIONS,
                f"Image width ({width}px) exceeds maximum of {profile.max_width}px.",
            )
        if profile.max_height is not None and height > profile.max_height:
            _raise(
                G2PRegistryErrorCodes.INVALID_IMAGE_DIMENSIONS,
                f"Image height ({height}px) exceeds maximum of {profile.max_height}px.",
            )

    return FileValidationResult(
        mime_type=mime_type,
        size=size,
        width=width,
        height=height,
        extension=matched_extension,
    )


def validate_base64_file(
    value: str,
    profile: FileValidationProfile,
    filename: Optional[str] = None,
) -> str:
    """
    Validate a base64 / data-URL payload and return a normalized data URL
    whose MIME matches sniffed content.
    """
    data = decode_base64_input(value)
    result = validate_file_bytes(data, profile, filename=filename)
    return to_data_url(data, result.mime_type)
