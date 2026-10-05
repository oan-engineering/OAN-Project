import logging
from typing import Tuple

from sqlalchemy.ext.asyncio import async_sessionmaker

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.schemas import G2PPaginationResponse
from openg2p_fastapi_common.service import BaseService

from ..schemas import (
    CreateScoreDefinitionRequest,
    CreateScoreDefinitionResponsePayload,
    DeleteScoreDefinitionRequest,
    DeleteScoreDefinitionResponsePayload,
    GetScoreDefinitionsRequest,
    GetScoreDefinitionsResponsePayload,
    ScoreDefinitionData,
    UpdateScoreDefinitionRequest,
    UpdateScoreDefinitionResponsePayload,
)
from ..services import G2PScoreComputeService

_logger = logging.getLogger("g2p-score-definition-controller-service")

class G2PScoreDefinitionControllerService(BaseService):
    async def get_score_definitions(
        self, get_score_definitions_request: GetScoreDefinitionsRequest
    ) -> Tuple[GetScoreDefinitionsResponsePayload, G2PPaginationResponse]:
        _logger.info("Getting score definitions (header only)")
        payload = get_score_definitions_request.request_body.request_payload
        pagination = get_score_definitions_request.request_body.pagination_request
        register_id = payload.register_id
        page_number = pagination.current_page
        page_size = pagination.page_size

        g2p_score_compute_service = G2PScoreComputeService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            score_definitions_data, total = await g2p_score_compute_service.get_score_definitions_for_register(
                register_id=register_id,
                page_number=page_number,
                page_size=page_size,
                session=session,
            )

        pagination = G2PPaginationResponse(
            number_of_items=total,
            number_of_pages=self._number_of_pages(total, page_size),
        )
        return (
            GetScoreDefinitionsResponsePayload(score_definitions=score_definitions_data),
            pagination,
        )

    async def create_score_definition(
        self, create_score_definition_request: CreateScoreDefinitionRequest
    ) -> CreateScoreDefinitionResponsePayload:
        _logger.info("Creating score definition header")
        payload = create_score_definition_request.request_body.request_payload

        g2p_score_compute_service = G2PScoreComputeService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            score_definition_data: ScoreDefinitionData = await g2p_score_compute_service.create_score_definition(
                register_id=payload.register_id,
                score_type=payload.score_type,
                session=session,
            )
            await session.commit()

        return CreateScoreDefinitionResponsePayload(score_definition=score_definition_data)

    async def update_score_definition(
        self, update_score_definition_request: UpdateScoreDefinitionRequest
    ) -> UpdateScoreDefinitionResponsePayload:
        _logger.info("Updating score definition header")
        payload = update_score_definition_request.request_body.request_payload

        g2p_score_compute_service = G2PScoreComputeService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            score_definition_data = await g2p_score_compute_service.update_score_definition(
                score_definition_id=payload.score_definition_id,
                is_enabled=payload.is_enabled,
                session=session,
            )
            await session.commit()

        return UpdateScoreDefinitionResponsePayload(score_definition=score_definition_data)

    async def delete_score_definition(
        self, delete_score_definition_request: DeleteScoreDefinitionRequest
    ) -> DeleteScoreDefinitionResponsePayload:
        _logger.info("Deleting score definition")
        payload = delete_score_definition_request.request_body.request_payload

        g2p_score_compute_service = G2PScoreComputeService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            deleted_id = await g2p_score_compute_service.delete_score_definition(
                score_definition_id=payload.score_definition_id,
                session=session,
            )
            await session.commit()

        return DeleteScoreDefinitionResponsePayload(score_definition_id=deleted_id)

    def _number_of_pages(self, total_items: int, page_size: int) -> int:
        if total_items <= 0:
            return 0
        if page_size <= 0:
            return 1
        return (total_items + page_size - 1) // page_size
