import logging
from typing import Optional, Tuple, List

from openg2p_fastapi_common.service import BaseService

from sqlalchemy.ext.asyncio import AsyncSession
from ..models import G2PRegisterChangeRequest, G2PRegisterChangeRequestDocument, G2PRegisterDefinition, G2PRegisterSection
from ..schemas import ChangeRequestRequestPayload
from .g2p_register_change_request_service import G2PRegisterChangeRequestService

_logger = logging.getLogger("g2p-change-request-worker-service")


class G2PChangeRequestWorkerService(BaseService):

    async def create_change_request(
        self,
        change_request_request_payload: ChangeRequestRequestPayload,
        session: AsyncSession,
        source_partner_id: Optional[str] = None,
        created_by: str | None = None,
        change_request_source: str | None = None,
    ) -> G2PRegisterChangeRequest:
        change_request_service = G2PRegisterChangeRequestService.get_component()
        g2p_register_definition: G2PRegisterDefinition = await change_request_service.validate_register_definition(
            change_request_request_payload.register_id, session
        )
        g2p_register_section: G2PRegisterSection = await change_request_service.validate_section(
            change_request_request_payload.section_id, session
        )
        section_register_definition: G2PRegisterDefinition = await change_request_service.validate_register_definition(
            g2p_register_section.section_register_id, session
        )
        await change_request_service.validate_change_request_creation(
            change_request_request_payload,
            g2p_register_definition,
            g2p_register_section,
            section_register_definition,
        )
        await change_request_service._validate_domain_attributes(
            change_request_service._records_from_change_request_payload(change_request_request_payload),
            section_register_definition.register_mnemonic,
        )

        g2p_register_change_request: G2PRegisterChangeRequest = await change_request_service.construct_change_request(
            change_request_request_payload,
            g2p_register_section,
            g2p_register_definition.register_mnemonic,
            section_register_definition.register_mnemonic,
            source_partner_id,
            created_by,
            change_request_source_override=change_request_source,
            session=session,
        )

        session.add(g2p_register_change_request)
        # Add the payload object if it exists
        if hasattr(g2p_register_change_request, '_payload'):
            session.add(g2p_register_change_request._payload)

        # Attach already-uploaded documents (validated against the catalog)
        if change_request_request_payload.documents:
            from .g2p_document_service import G2PDocumentService
            document_service = G2PDocumentService.get_component()
            await document_service.validate_documents_exist(
                session,
                [doc.document_id for doc in change_request_request_payload.documents],
            )
            for doc in change_request_request_payload.documents:
                session.add(G2PRegisterChangeRequestDocument(
                    change_request_id=g2p_register_change_request.change_request_id,
                    document_id=doc.document_id,
                    section_id=change_request_request_payload.section_id,
                    label=doc.label,
                ))

        # Ensure `change_request_id` and relationship rows are persisted within the caller's transaction.
        await session.flush()
        await session.refresh(g2p_register_change_request)
        return g2p_register_change_request


    async def auto_approve_primary_master_section_change_request(self, change_request_id: str, session: AsyncSession) -> Tuple[G2PRegisterChangeRequest, str]:
        change_request_service = G2PRegisterChangeRequestService.get_component()
        change_request = await change_request_service._approve_change_request_core(
            change_request_id=change_request_id,
            session=session,
            skip_verification=True,
        )
        _logger.info(f"Auto-approved primary master section change request: {change_request_id}")
        await session.refresh(change_request)
        return change_request, change_request.internal_record_id

    async def auto_approve_non_primary_master_section_change_request(self, change_request_id: str, subject_internal_record_id: str, session: AsyncSession) -> G2PRegisterChangeRequest:
        change_request_service = G2PRegisterChangeRequestService.get_component()
        change_request = await change_request_service._approve_change_request_core(
            change_request_id=change_request_id,
            session=session,
            skip_verification=True,
        )
        _logger.info(f"Auto-approved non-primary master section change request: {change_request_id}")
        await session.refresh(change_request)
        return change_request

    async def auto_approve_child_section_change_request(self, change_request_id: str, subject_internal_record_id: str, session: AsyncSession) -> G2PRegisterChangeRequest:
        change_request_service = G2PRegisterChangeRequestService.get_component()
        change_request = await change_request_service._approve_change_request_core(
            change_request_id=change_request_id,
            session=session,
            skip_verification=True,
        )
        _logger.info(f"Auto-approved child section change request: {change_request_id}")
        await session.refresh(change_request)
        return change_request

    async def auto_approve_change_requests_in_order(
        self,
        change_request_ids: List[str],
        session: AsyncSession,
        *,
        fallback_subject_internal_record_id: Optional[str] = None,
    ) -> tuple[Optional[str], int, Optional[str]]:
        """Approve change requests sequentially using the consolidated approval flow."""
        _logger.debug("Change Request Ids=%s", change_request_ids)
        _logger.debug("Session Type=%s", type(session))
        _logger.debug("Fallback Subject Internal Record Id=%s", fallback_subject_internal_record_id)

        change_request_service = G2PRegisterChangeRequestService.get_component()
        approved_count = 0
        subject_internal_record_id: Optional[str] = fallback_subject_internal_record_id
        last_attempted_change_request_id: Optional[str] = None

        for change_request_id in change_request_ids:
            last_attempted_change_request_id = change_request_id
            change_request = await change_request_service._approve_change_request_core(
                change_request_id=change_request_id,
                session=session,
                skip_verification=True,
            )
            subject_internal_record_id = subject_internal_record_id or change_request.internal_record_id
            approved_count += 1

        return subject_internal_record_id, approved_count, last_attempted_change_request_id
