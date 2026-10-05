import logging
import uuid
from datetime import datetime

from sqlalchemy import select

from ..models import (
    G2PRegisterDefinition,
    OutgoingRawData,
    OutgoingRawDataPayload,
    OutgoingTopic,
    ProcessStatusEnum,
)
from .g2p_register_hierarchical_service import G2PRegisterHierarchicalService

_logger = logging.getLogger(__name__)


async def fanout_outgest_rows(
    register_definition: G2PRegisterDefinition,
    register_row,
    session,
    *,
    changed_by: str,
    changed_at: datetime,
    approved_by: str | None = None,
    approved_at: datetime | None = None,
    intake_form_submission_id: str | None = None,
    change_request_id: str | None = None,
    changed_by_partner_id: str | None = None,
    hierarchical_service: G2PRegisterHierarchicalService | None = None,
) -> None:
    if not (intake_form_submission_id or change_request_id):
        raise ValueError(
            "fanout_outgest_rows requires either intake_form_submission_id or change_request_id"
        )

    if not register_definition.outgest_applicable:
        _logger.info(
            "Skipping outgest fanout — outgest_applicable=False for register_id=%s",
            register_definition.register_id,
        )
        return

    topics = (
        await session.execute(
            select(OutgoingTopic).where(
                OutgoingTopic.register_id == register_definition.register_id,
                OutgoingTopic.is_active.is_(True),
            )
        )
    ).scalars().all()
    if not topics:
        return

    hierarchical_service = hierarchical_service or G2PRegisterHierarchicalService()
    full_record = await hierarchical_service.enrich_record_hierarchy(
        register_definition, register_row, session
    )

    source_id = intake_form_submission_id or change_request_id
    payload_id = f"{source_id}:{register_definition.register_id}:{register_row.internal_record_id}"

    session.add(
        OutgoingRawDataPayload(
            payload_id=payload_id,
            intake_form_submission_id=intake_form_submission_id,
            change_request_id=change_request_id,
            raw_data_json=full_record,
        )
    )

    for topic in topics:
        session.add(
            OutgoingRawData(
                outgest_id=str(uuid.uuid4()),
                payload_id=payload_id,
                intake_form_submission_id=intake_form_submission_id,
                change_request_id=change_request_id,
                internal_record_id=register_row.internal_record_id,
                register_id=register_definition.register_id,
                data_model_id=topic.data_model_id,
                topic_id=topic.topic_id,
                changed_by=changed_by,
                changed_at=changed_at,
                approved_by=approved_by,
                approved_at=approved_at,
                changed_by_partner_id=changed_by_partner_id,
                transformation_status=ProcessStatusEnum.PENDING.value,
            )
        )
