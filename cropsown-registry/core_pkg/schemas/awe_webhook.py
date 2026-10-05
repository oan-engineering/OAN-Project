from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AweWebhookEvent(BaseModel):
    """Body POSTed by AWE to the Registry callback (matches awe.schemas.callback.WebhookEvent)."""

    event_id: str
    event_type: str = Field(
        ...,
        description=(
            "request_created | stage_started | stage_completed | "
            "request_approved | request_rejected | request_cancelled"
        ),
    )
    request_id: str
    artifact_type: str = Field(
        ...,
        examples=["registry.change_request", "registry.intake_form"],
    )
    artifact_id: str
    status: str
    stage_order: Optional[int] = None
    actor: Optional[str] = None
    occurred_at: datetime


class AweWebhookDecisionResponse(BaseModel):
    event_id: str
    applied: bool
    message: str = "ok"
