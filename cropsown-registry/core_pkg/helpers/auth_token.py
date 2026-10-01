"""Extract bearer tokens from FastAPI requests / auth principals."""

from __future__ import annotations

from fastapi import Request


def bearer_from_request(request: Request) -> str | None:
    auth = getattr(getattr(request, "state", None), "auth", None)
    token = getattr(auth, "credentials", None) if auth else None
    if token and str(token).strip():
        return str(token).strip()
    header = request.headers.get("authorization", "")
    parts = header.split(maxsplit=1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def requester_sub_from_request(request: Request) -> str | None:
    auth = getattr(getattr(request, "state", None), "auth", None)
    sub = getattr(auth, "sub", None) if auth else None
    return str(sub).strip() if sub else None
