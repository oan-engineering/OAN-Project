import logging
from typing import List, Optional, Tuple

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.schemas import G2PPaginationRequest, G2PPaginationResponse
from openg2p_fastapi_common.service import BaseService
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..schemas import (
    AttributeData,
    AttributeValueData,
    CreateAttributeRequest,
    CreateAttributeResponsePayload,
    CreateAttributeValueRequest,
    CreateAttributeValueResponsePayload,
    DeleteAttributeRequest,
    DeleteAttributeResponsePayload,
    DeleteAttributeValueRequest,
    DeleteAttributeValueResponsePayload,
    GetAttributeRequest,
    GetAttributesRequest,
    GetAttributeValuesRequest,
    UpdateAttributeRequest,
    UpdateAttributeResponsePayload,
    UpdateAttributeValueRequest,
    UpdateAttributeValueResponsePayload,
)
from ..services import G2PAttributeService

_logger = logging.getLogger("g2p-attribute-controller-service")


class G2PAttributeControllerService(BaseService):
    async def get_attributes(
        self, request: GetAttributesRequest
    ) -> Tuple[List[AttributeData], Optional[G2PPaginationResponse]]:
        _logger.info("Fetching attributes through controller service")
        pagination_request = request.request_body.pagination_request
        current_page, page_size = self._extract_pagination_values(pagination_request)
        search_text = self._extract_search_text(pagination_request)
        g2p_attribute_service = G2PAttributeService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            attributes, total_items = await g2p_attribute_service.get_attributes(
                session,
                current_page=current_page,
                page_size=page_size,
                search_text=search_text,
            )
        pagination_response = self._build_pagination_response(
            total_items, page_size, pagination_request
        )
        return attributes, pagination_response

    async def get_attribute(self, request: GetAttributeRequest) -> AttributeData:
        _logger.info("Fetching attribute through controller service")
        payload = request.request_body.request_payload
        g2p_attribute_service = G2PAttributeService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            return await g2p_attribute_service.get_attribute(payload.attribute_id, session)

    async def create_attribute(self, request: CreateAttributeRequest) -> CreateAttributeResponsePayload:
        _logger.info("Creating attribute through controller service")
        payload = request.request_body.request_payload
        g2p_attribute_service = G2PAttributeService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            attribute = await g2p_attribute_service.create_attribute(
                attribute_code=payload.attribute_code,
                attribute_display=payload.attribute_display,
                is_hierarchical=payload.is_hierarchical,
                session=session,
            )
            await session.commit()
        return CreateAttributeResponsePayload(attribute=attribute)

    async def update_attribute(self, request: UpdateAttributeRequest) -> UpdateAttributeResponsePayload:
        _logger.info("Updating attribute through controller service")
        payload = request.request_body.request_payload
        g2p_attribute_service = G2PAttributeService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            attribute = await g2p_attribute_service.update_attribute(
                attribute_id=payload.attribute_id,
                attribute_code=payload.attribute_code,
                attribute_display=payload.attribute_display,
                is_hierarchical=payload.is_hierarchical,
                session=session,
            )
            await session.commit()
        return UpdateAttributeResponsePayload(attribute=attribute)

    async def delete_attribute(self, request: DeleteAttributeRequest) -> DeleteAttributeResponsePayload:
        _logger.info("Deleting attribute through controller service")
        payload = request.request_body.request_payload
        g2p_attribute_service = G2PAttributeService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            attribute_id = await g2p_attribute_service.delete_attribute(
                payload.attribute_id,
                session,
            )
            await session.commit()
        return DeleteAttributeResponsePayload(attribute_id=attribute_id)

    async def get_attribute_values(
        self,
        request: GetAttributeValuesRequest,
        policy_mnemonics: list[str] | None = None,
    ) -> Tuple[List[AttributeValueData], Optional[G2PPaginationResponse]]:
        _logger.info("Fetching attribute values through controller service")
        payload = request.request_body.request_payload
        pagination_request = request.request_body.pagination_request
        current_page, page_size = self._extract_pagination_values(pagination_request)
        search_text = self._extract_search_text(pagination_request)
        parent_value_id = payload.parent_value_id or None

        g2p_attribute_service = G2PAttributeService.get_component()
        attribute_values, total_items = await g2p_attribute_service.get_attribute_values(
            attribute_id=payload.attribute_id,
            parent_value_id=parent_value_id,
            current_page=current_page,
            page_size=page_size,
            search_text=search_text,
            policy_mnemonics=policy_mnemonics,
        )
        pagination_response = self._build_pagination_response(
            total_items, page_size, pagination_request
        )
        return attribute_values, pagination_response

    async def create_attribute_value(
        self, request: CreateAttributeValueRequest
    ) -> CreateAttributeValueResponsePayload:
        _logger.info("Creating attribute value through controller service")
        payload = request.request_body.request_payload
        g2p_attribute_service = G2PAttributeService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            attribute_value = await g2p_attribute_service.create_attribute_value(
                attribute_id=payload.attribute_id,
                value_code=payload.value_code,
                value_display=payload.value_display,
                parent_value_id=payload.parent_value_id,
                sort_order=payload.sort_order,
                session=session,
            )
            await session.commit()
        return CreateAttributeValueResponsePayload(attribute_value=attribute_value)

    async def update_attribute_value(
        self, request: UpdateAttributeValueRequest
    ) -> UpdateAttributeValueResponsePayload:
        _logger.info("Updating attribute value through controller service")
        payload = request.request_body.request_payload
        g2p_attribute_service = G2PAttributeService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            attribute_value = await g2p_attribute_service.update_attribute_value(
                value_id=payload.value_id,
                value_code=payload.value_code,
                value_display=payload.value_display,
                parent_value_id=payload.parent_value_id,
                sort_order=payload.sort_order,
                session=session,
            )
            await session.commit()
        return UpdateAttributeValueResponsePayload(attribute_value=attribute_value)

    async def delete_attribute_value(
        self, request: DeleteAttributeValueRequest
    ) -> DeleteAttributeValueResponsePayload:
        _logger.info("Deleting attribute value through controller service")
        payload = request.request_body.request_payload
        g2p_attribute_service = G2PAttributeService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            value_id = await g2p_attribute_service.delete_attribute_value(
                payload.value_id,
                session,
            )
            await session.commit()
        return DeleteAttributeValueResponsePayload(value_id=value_id)

    def _extract_pagination_values(
        self,
        pagination_request: Optional[G2PPaginationRequest],
    ) -> tuple[Optional[int], Optional[int]]:
        if pagination_request is None:
            return None, None
        return pagination_request.current_page, pagination_request.page_size

    def _extract_search_text(
        self,
        pagination_request: Optional[G2PPaginationRequest],
    ) -> Optional[str]:
        if pagination_request is None or pagination_request.search_text is None:
            return None
        search_text = pagination_request.search_text.strip()
        return search_text or None

    def _build_pagination_response(
        self,
        total_items: int,
        page_size: Optional[int],
        pagination_request: Optional[G2PPaginationRequest],
    ) -> Optional[G2PPaginationResponse]:
        if pagination_request is None:
            return None
        return G2PPaginationResponse(
            number_of_items=total_items,
            number_of_pages=self._calculate_number_of_pages(total_items, page_size),
        )

    def _calculate_number_of_pages(self, total_items: int, page_size: int | None) -> int:
        if total_items <= 0:
            return 0
        if page_size is None or page_size <= 0:
            return 1
        return (total_items + page_size - 1) // page_size
