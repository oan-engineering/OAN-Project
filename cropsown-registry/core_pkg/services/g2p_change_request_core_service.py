import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService

from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..models import G2PRegisterChangeRequest
from ..schemas import ChangeRequestRequestPayload
from .g2p_register_change_request_service import G2PRegisterChangeRequestService

_logger = logging.getLogger("g2p-change-request-core-service")


class G2PChangeRequestCoreService(BaseService):
    async def create_change_request_for_core_data(
        self,
        change_request_request_payload: ChangeRequestRequestPayload,
        source_partner_id: str | None = None,
        bearer_token: str | None = None,
        requester_sub: str | None = None,
        created_by: str | None = None,
    ) -> G2PRegisterChangeRequest:
        _logger.info("Creating core-data change request")

        change_request_service = G2PRegisterChangeRequestService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._validate_section_is_core(
                change_request_request_payload.section_id,
                change_request_service,
                session,
            )

        return await change_request_service.create_change_request(
            change_request_request_payload=change_request_request_payload,
            source_partner_id=source_partner_id,
            created_by=created_by or change_request_request_payload.created_by,
            bearer_token=bearer_token,
            requester_sub=requester_sub,
        )

    async def approve_change_request_for_core_data(
        self, change_request_id: str
    ) -> G2PRegisterChangeRequest:
        _logger.info(
            "Approving core-data change request with change_request_id: %s",
            change_request_id,
        )

        change_request_service = G2PRegisterChangeRequestService.get_component()
        await self._validate_change_request_section_is_core(change_request_id, change_request_service)
        return await change_request_service.approve_change_request(change_request_id)

    async def reject_change_request_for_core_data(
        self, change_request_id: str, reason: str | None
    ) -> G2PRegisterChangeRequest:
        _logger.info(
            "Rejecting core-data change request with change_request_id: %s",
            change_request_id,
        )

        change_request_service = G2PRegisterChangeRequestService.get_component()
        await self._validate_change_request_section_is_core(change_request_id, change_request_service)
        return await change_request_service.reject_change_request(change_request_id, reason)

    async def _validate_section_is_core(self, section_id: str | None, change_request_service: G2PRegisterChangeRequestService, session) -> None:
        if not section_id:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                message="section_id is required for core-data change request operations",
            )

        try:
            section = await change_request_service.validate_section(section_id, session)
        except ValueError as error:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SECTION_NOT_FOUND.value[1],
                message=str(error),
            ) from error

        if not section.is_core_section:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.NON_CORE_SECTION_OPERATION_NOT_ALLOWED.value[1],
                message=G2PRegistryErrorCodes.NON_CORE_SECTION_OPERATION_NOT_ALLOWED.value[0],
            )

    async def _validate_change_request_section_is_core(
        self, change_request_id: str | None, change_request_service: G2PRegisterChangeRequestService
    ) -> None:
        if not change_request_id:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                message="change_request_id is required for core-data change request operations",
            )

        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            change_request = await change_request_service.validate_change_request_exists(
                change_request_id,
                session,
            )
            await self._validate_section_is_core(
                change_request.section_id,
                change_request_service,
                session,
            )
