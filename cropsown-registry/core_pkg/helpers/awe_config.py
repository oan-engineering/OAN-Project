"""Resolve AWE-related settings for registry-core and staff-portal processes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import Settings as CoreSettingsType


def normalize_awe_base_url(url: str) -> str:
    """Host root only — paths like ``/v1/awe`` are appended by ``AweHelper``."""
    normalized = (url or "").strip().rstrip("/")
    if normalized.endswith("/v1/awe"):
        normalized = normalized[: -len("/v1/awe")]
    return normalized.rstrip("/")


def get_awe_settings() -> "CoreSettingsType":
    """Merge ``registry_core_*`` and ``registry_staff_portal_api_*`` AWE env vars."""
    from ..config import Settings as CoreSettings

    core = CoreSettings.get_config(strict=False)
    try:
        from openg2p_registry_staff_api.config import Settings as StaffSettings
    except ImportError:
        return core

    staff = StaffSettings.get_config(strict=False)
    base_url = normalize_awe_base_url(staff.awe_base_url or core.awe_base_url)
    return core.model_copy(
        update={
            "awe_enabled": bool(staff.awe_enabled or core.awe_enabled),
            "awe_base_url": base_url,
            "awe_http_timeout_seconds": staff.awe_http_timeout_seconds,
            "awe_default_callback_url": staff.awe_default_callback_url
            or core.awe_default_callback_url,
            "awe_callback_secret_id": staff.awe_callback_secret_id
            or core.awe_callback_secret_id,
            "awe_callback_hmac_secret": staff.awe_callback_hmac_secret
            or core.awe_callback_hmac_secret,
            "awe_webhook_timestamp_tolerance_seconds": (
                staff.awe_webhook_timestamp_tolerance_seconds
            ),
        }
    )
