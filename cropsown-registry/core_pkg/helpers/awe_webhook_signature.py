from __future__ import annotations

import hashlib
import hmac
import time


class AweWebhookSignatureError(Exception):
    pass


def verify_awe_webhook_signature(
    *,
    secret: str,
    body: bytes,
    signature_header: str | None,
    timestamp_header: str | None,
    tolerance_seconds: int = 300,
) -> None:
    if not secret:
        return
    if not signature_header or not signature_header.startswith("sha256="):
        raise AweWebhookSignatureError("Missing or invalid X-Approval-Signature header")
    if not timestamp_header:
        raise AweWebhookSignatureError("Missing X-Approval-Timestamp header")

    try:
        timestamp = int(timestamp_header)
    except ValueError as exc:
        raise AweWebhookSignatureError("Invalid X-Approval-Timestamp header") from exc

    now = int(time.time())
    if abs(now - timestamp) > tolerance_seconds:
        raise AweWebhookSignatureError("Webhook timestamp outside allowed skew window")

    expected_mac = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.".encode("utf-8") + body,
        hashlib.sha256,
    ).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    if not hmac.compare_digest(expected_mac, provided):
        raise AweWebhookSignatureError("Webhook signature mismatch")
