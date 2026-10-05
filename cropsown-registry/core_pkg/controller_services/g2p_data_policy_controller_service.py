import logging
from typing import Optional, Tuple

from openg2p_fastapi_common.schemas import G2PPaginationRequest, G2PPaginationResponse
from sqlalchemy.ext.asyncio import async_sessionmaker

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService

from ..schemas import (
    AddPolicyRequest,
    AddPolicyResponsePayload,
    GetAllPoliciesRequest,
    GetAllPoliciesResponsePayload,
    GetPolicyRequest,
    GetPolicyResponsePayload,
    RemovePolicyRequest,
    RemovePolicyResponsePayload,
)
from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..helpers.data_policy_keycloak_helper import DataPolicyKeycloakHelper
from ..services import G2PDataPolicyService, G2PRegisterService

_logger = logging.getLogger("g2p-data-policy-controller-service")


class G2PDataPolicyControllerService(BaseService):
    async def get_policy(
        self, get_policy_request: GetPolicyRequest
    ) -> GetPolicyResponsePayload:
        payload = get_policy_request.request_body.request_payload
        _logger.info("Getting data policy policy_id=%s", payload.policy_id)

        data_policy_service = G2PDataPolicyService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            policy = await data_policy_service.get_policy(
                session,
                policy_id=payload.policy_id,
            )
        return GetPolicyResponsePayload(policy=policy)

    async def get_all_policies(
        self, get_all_policies_request: GetAllPoliciesRequest
    ) -> Tuple[GetAllPoliciesResponsePayload, Optional[G2PPaginationResponse]]:
        pagination_request = get_all_policies_request.request_body.pagination_request
        current_page, page_size = self._extract_pagination_values(pagination_request)
        _logger.info(
            "Getting all data policies current_page=%s page_size=%s",
            current_page,
            page_size,
        )

        data_policy_service = G2PDataPolicyService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            policies, total_items = await data_policy_service.get_all_policies(
                session,
                current_page=current_page,
                page_size=page_size,
            )
        pagination_response = self._build_pagination_response(
            total_items, page_size, pagination_request
        )
        return GetAllPoliciesResponsePayload(policies=policies), pagination_response

    async def add_policy(self, add_policy_request: AddPolicyRequest) -> AddPolicyResponsePayload:
        payload = add_policy_request.request_body.request_payload
        _logger.info(
            "Adding data policy mnemonic=%s register_id=%s policy_target=%s",
            payload.policy_mnemonic,
            payload.register_id,
            payload.policy_target,
        )

        register_service = G2PRegisterService.get_component()
        data_policy_service = G2PDataPolicyService.get_component()
        keycloak_helper = DataPolicyKeycloakHelper()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            if payload.register_id:
                await register_service.validate_register_definition(payload.register_id, session)
            policy = await data_policy_service.add_policy(
                policy_mnemonic=payload.policy_mnemonic,
                policy_description=payload.policy_description,
                register_id=payload.register_id,
                policy_filter_expression=payload.policy_filter_expression,
                session=session,
                policy_type=payload.policy_type,
                policy_target=payload.policy_target,
            )
            try:
                await keycloak_helper.create_data_policy_role(
                    policy.policy_mnemonic,
                    policy_description=policy.policy_description,
                )
            except G2PRegistryException as exc:
                _logger.error(
                    "Keycloak sync failed for policy mnemonic=%s: %s",
                    policy.policy_mnemonic,
                    exc,
                )
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.KEYCLOAK_SYNC_ERROR.value[1],
                    message=f"Failed to publish data policy role to Keycloak: {exc}",
                ) from exc
            await session.commit()
        return AddPolicyResponsePayload(policy=policy)

    async def remove_policy(
        self, remove_policy_request: RemovePolicyRequest
    ) -> RemovePolicyResponsePayload:
        policy_id = remove_policy_request.request_body.request_payload.policy_id
        _logger.info("Removing data policy policy_id=%s", policy_id)

        data_policy_service = G2PDataPolicyService.get_component()
        keycloak_helper = DataPolicyKeycloakHelper()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            deleted_id, policy_mnemonic, should_delete_role = await data_policy_service.remove_policy(
                policy_id=policy_id,
                session=session,
            )
            if should_delete_role:
                try:
                    await keycloak_helper.delete_data_policy_role(policy_mnemonic)
                except G2PRegistryException as exc:
                    _logger.error(
                        "Keycloak role delete failed for policy mnemonic=%s: %s",
                        policy_mnemonic,
                        exc,
                    )
                    raise G2PRegistryException(
                        code=G2PRegistryErrorCodes.KEYCLOAK_SYNC_ERROR.value[1],
                        message=f"Failed to remove data policy role from Keycloak: {exc}",
                    ) from exc
            await session.commit()
        return RemovePolicyResponsePayload(policy_id=deleted_id)

    def _extract_pagination_values(
        self,
        pagination_request: Optional[G2PPaginationRequest],
    ) -> tuple[Optional[int], Optional[int]]:
        if pagination_request is None:
            return None, None
        return pagination_request.current_page, pagination_request.page_size

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
