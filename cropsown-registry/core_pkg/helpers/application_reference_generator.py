"""
Configurable application reference generator.

Set the format via environment variable ``registry_core_application_reference_format``.

Supported tokens (literals outside braces are copied verbatim):

- ``{DATE:%Y%m%d}`` - ``datetime.strftime`` date segment
- ``{DATE:%d%b%Y|upper}`` - date with optional ``|upper`` modifier (e.g. ``01JAN2001``)
- ``{TIME:%H%M%S}`` - ``datetime.strftime`` time segment (optional ``|upper``)
- ``{SECONDS:5}`` - zero-padded seconds since midnight
- ``{EPOCH:10}`` - zero-padded Unix epoch seconds
- ``{RAND:5}`` - zero-padded numeric random digits
- ``{RAND_ALNUM:6}`` - random uppercase letters and digits
- ``{UUID8}`` - 8 hex characters

Example formats::

    registry_core_application_reference_format="{DATE:%Y%b%d|upper}-{SECONDS:5}{RAND:1}"
    registry_core_application_reference_format="{DATE:%Y%m%d}-{SECONDS:5}-{RAND:5}"
    registry_core_application_reference_format="{DATE:%d%m%Y}-{TIME:%H%M%S}-{RAND:4}"
    registry_core_application_reference_format="APP-{DATE:%d%b%Y|upper}-{RAND:6}"
"""

from __future__ import annotations

import re
import secrets
import string
import uuid
from dataclasses import dataclass
from datetime import datetime

from openg2p_fastapi_common.service import BaseService

TOKEN_PATTERN = re.compile(r"\{([^}]+)\}")
MAX_OUTPUT_LENGTH = 64
MAX_RAND_WIDTH = 12
_ALNUM_ALPHABET = string.ascii_uppercase + string.digits
_COMPILE_TEST_TIME = datetime(2001, 1, 1, 12, 30, 45)


class ApplicationReferenceFormatError(ValueError):
    """Raised when the configured application reference format is invalid."""


@dataclass(frozen=True)
class _LiteralSegment:
    value: str


@dataclass(frozen=True)
class _DateTimeSegment:
    strftime_pattern: str
    upper: bool


@dataclass(frozen=True)
class _SecondsSegment:
    width: int


@dataclass(frozen=True)
class _EpochSegment:
    width: int


@dataclass(frozen=True)
class _RandSegment:
    width: int


@dataclass(frozen=True)
class _RandAlnumSegment:
    width: int


@dataclass(frozen=True)
class _Uuid8Segment:
    pass


class CompiledApplicationReferenceFormat:
    def __init__(self, format_string: str, segments: list[object]):
        self.format_string = format_string
        self._segments = segments

    def render(self, reference_time: datetime) -> str:
        parts: list[str] = []
        for segment in self._segments:
            if isinstance(segment, _LiteralSegment):
                parts.append(segment.value)
            elif isinstance(segment, _DateTimeSegment):
                value = reference_time.strftime(segment.strftime_pattern)
                if segment.upper:
                    value = value.upper()
                parts.append(value)
            elif isinstance(segment, _SecondsSegment):
                seconds_since_midnight = (
                    reference_time.hour * 3600
                    + reference_time.minute * 60
                    + reference_time.second
                )
                parts.append(f"{seconds_since_midnight:0{segment.width}d}")
            elif isinstance(segment, _EpochSegment):
                parts.append(f"{int(reference_time.timestamp()):0{segment.width}d}")
            elif isinstance(segment, _RandSegment):
                parts.append(
                    f"{secrets.randbelow(10 ** segment.width):0{segment.width}d}"
                )
            elif isinstance(segment, _RandAlnumSegment):
                parts.append(
                    "".join(
                        secrets.choice(_ALNUM_ALPHABET)
                        for _ in range(segment.width)
                    )
                )
            elif isinstance(segment, _Uuid8Segment):
                parts.append(uuid.uuid4().hex[:8].upper())
            else:
                raise ApplicationReferenceFormatError(
                    f"Unsupported compiled segment type: {type(segment)!r}"
                )

        rendered = "".join(parts)
        if len(rendered) > MAX_OUTPUT_LENGTH:
            raise ApplicationReferenceFormatError(
                f"Rendered application reference exceeds {MAX_OUTPUT_LENGTH} characters"
            )
        return rendered


class ApplicationReferenceGenerator(BaseService):
    def __init__(self, format_string: str):
        super().__init__()
        self.format_string = format_string
        self._compiled = self.compile(format_string)

    def generate(self, now: datetime | None = None) -> str:
        return self._compiled.render(now or datetime.now())

    @classmethod
    def compile(cls, format_string: str) -> CompiledApplicationReferenceFormat:
        if not format_string or not format_string.strip():
            raise ApplicationReferenceFormatError(
                "application_reference_format must not be empty"
            )

        segments: list[object] = []
        cursor = 0
        estimated_max_length = 0

        for match in TOKEN_PATTERN.finditer(format_string):
            if match.start() > cursor:
                literal = format_string[cursor:match.start()]
                segments.append(_LiteralSegment(literal))
                estimated_max_length += len(literal)

            token_name, token_arg, modifier = _parse_token_body(match.group(1))
            segment, segment_max_length = _compile_token(token_name, token_arg, modifier)
            segments.append(segment)
            estimated_max_length += segment_max_length
            cursor = match.end()

        if cursor < len(format_string):
            literal = format_string[cursor:]
            segments.append(_LiteralSegment(literal))
            estimated_max_length += len(literal)

        if not segments:
            raise ApplicationReferenceFormatError(
                "application_reference_format must contain at least one segment"
            )

        if estimated_max_length > MAX_OUTPUT_LENGTH:
            raise ApplicationReferenceFormatError(
                f"application_reference_format may render up to {estimated_max_length} "
                f"characters, exceeding the limit of {MAX_OUTPUT_LENGTH}"
            )

        compiled = CompiledApplicationReferenceFormat(format_string, segments)
        compiled.render(_COMPILE_TEST_TIME)
        return compiled


def generate_application_reference(now: datetime | None = None) -> str:
    generator = ApplicationReferenceGenerator.get_component()
    if generator is not None:
        return generator.generate(now)

    from ..config import Settings

    compiled = ApplicationReferenceGenerator.compile(
        Settings.get_config(strict=False).application_reference_format
    )
    return compiled.render(now or datetime.now())


def _parse_token_body(body: str) -> tuple[str, str | None, str | None]:
    modifier: str | None = None
    if "|" in body:
        body, modifier = body.rsplit("|", 1)
        if modifier != "upper":
            raise ApplicationReferenceFormatError(
                f"Unsupported token modifier '{modifier}'. Only 'upper' is supported."
            )

    if ":" in body:
        token_name, token_arg = body.split(":", 1)
    else:
        token_name, token_arg = body, None

    token_name = token_name.strip().upper()
    if not token_name:
        raise ApplicationReferenceFormatError("Token name must not be empty")

    return token_name, token_arg, modifier


def _compile_token(
    token_name: str,
    token_arg: str | None,
    modifier: str | None,
) -> tuple[object, int]:
    upper = modifier == "upper"

    if token_name == "DATE":
        if not token_arg:
            raise ApplicationReferenceFormatError("DATE token requires a strftime pattern")
        _validate_strftime_pattern(token_arg)
        return (
            _DateTimeSegment(token_arg, upper),
            _estimate_strftime_max_length(token_arg, upper),
        )

    if token_name == "TIME":
        if not token_arg:
            raise ApplicationReferenceFormatError("TIME token requires a strftime pattern")
        _validate_strftime_pattern(token_arg)
        return (
            _DateTimeSegment(token_arg, upper),
            _estimate_strftime_max_length(token_arg, upper),
        )

    if token_name == "SECONDS":
        width = _parse_positive_width(token_arg, "SECONDS")
        if width > 5:
            raise ApplicationReferenceFormatError("SECONDS width must not exceed 5")
        return _SecondsSegment(width), width

    if token_name == "EPOCH":
        width = _parse_positive_width(token_arg, "EPOCH")
        if width > 12:
            raise ApplicationReferenceFormatError("EPOCH width must not exceed 12")
        return _EpochSegment(width), width

    if token_name == "RAND":
        width = _parse_positive_width(token_arg, "RAND")
        if width > MAX_RAND_WIDTH:
            raise ApplicationReferenceFormatError(
                f"RAND width must not exceed {MAX_RAND_WIDTH}"
            )
        return _RandSegment(width), width

    if token_name == "RAND_ALNUM":
        width = _parse_positive_width(token_arg, "RAND_ALNUM")
        if width > MAX_RAND_WIDTH:
            raise ApplicationReferenceFormatError(
                f"RAND_ALNUM width must not exceed {MAX_RAND_WIDTH}"
            )
        return _RandAlnumSegment(width), width

    if token_name == "UUID8":
        if token_arg is not None:
            raise ApplicationReferenceFormatError("UUID8 token does not take an argument")
        return _Uuid8Segment(), 8

    raise ApplicationReferenceFormatError(f"Unknown application reference token '{token_name}'")


def _parse_positive_width(token_arg: str | None, token_name: str) -> int:
    if token_arg is None:
        raise ApplicationReferenceFormatError(f"{token_name} token requires a width argument")
    try:
        width = int(token_arg)
    except ValueError as error:
        raise ApplicationReferenceFormatError(
            f"{token_name} width must be an integer"
        ) from error
    if width < 1:
        raise ApplicationReferenceFormatError(f"{token_name} width must be at least 1")
    return width


def _validate_strftime_pattern(pattern: str) -> None:
    try:
        _COMPILE_TEST_TIME.strftime(pattern)
    except ValueError as error:
        raise ApplicationReferenceFormatError(
            f"Invalid strftime pattern '{pattern}': {error}"
        ) from error


def _estimate_strftime_max_length(pattern: str, upper: bool) -> int:
    rendered = _COMPILE_TEST_TIME.strftime(pattern)
    if upper:
        rendered = rendered.upper()
    return len(rendered)
