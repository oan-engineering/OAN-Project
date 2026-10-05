from openg2p_fastapi_common.service import BaseService

from ..schemas import (
    RegistrantAuthProvidersRequest,
    RegistrantAuthProvidersResponsePayload,
    RegistrantAuthProviderSummary,
    RegistrantAuthInitiateRequest,
    RegistrantAuthInitiateResponsePayload,
    RegistrantAuthCallbackCompleteRequest,
    RegistrantAuthStatusRequest,
    RegistrantAuthStatusResponsePayload,
    RegistrantAuthHistoryRequest,
    RegistrantAuthHistoryResponsePayload,
    RegistrantAuthHistoryItem,
)
from ..services import G2PRegistrantAuthenticationService


class G2PRegistrantAuthenticationControllerService(BaseService):
    def __init__(self):
        super().__init__()
        self.registrant_authentication_service = G2PRegistrantAuthenticationService.get_component()

    async def get_available_providers(
        self,
        request: RegistrantAuthProvidersRequest,
    ) -> RegistrantAuthProvidersResponsePayload:
        providers = await self.registrant_authentication_service.get_available_providers(
            register_id=request.request_body.request_payload.register_id
        )
        return RegistrantAuthProvidersResponsePayload(
            providers=[
                RegistrantAuthProviderSummary(
                    provider_id=provider.provider_id,
                    provider_name=provider.provider_name,
                    provider_description=provider.provider_description,
                    adapter_name=provider.adapter_name,
                    display_order=provider.display_order,
                )
                for provider in providers
            ]
        )

    async def initiate_authentication(
        self,
        request: RegistrantAuthInitiateRequest,
    ) -> RegistrantAuthInitiateResponsePayload:
        payload = request.request_body.request_payload
        state, authorization_url, provider_name = await self.registrant_authentication_service.start_authentication(
            register_id=payload.register_id,
            internal_record_id=payload.internal_record_id,
            provider_id=payload.provider_id,
            initiated_by_staff_id=payload.initiated_by_staff_id,
        )
        return RegistrantAuthInitiateResponsePayload(
            authentication_session_id=state,
            authorization_url=authorization_url,
            provider_name=provider_name,
        )

    async def complete_callback(
        self,
        request: RegistrantAuthCallbackCompleteRequest,
    ) -> dict:
        payload = request
        auth = await self.registrant_authentication_service.complete_authentication(
            state=payload.state,
            authorization_code=payload.code,
        )
        return {
            "authentication_id": auth.authentication_id,
            "status": auth.status,
            "failure_reason": auth.failure_reason,
        }

    async def get_status(
        self,
        request: RegistrantAuthStatusRequest,
    ) -> RegistrantAuthStatusResponsePayload:
        payload = request.request_body.request_payload
        auth = await self.registrant_authentication_service.get_authentication_status(internal_record_id=payload.internal_record_id)
        if not auth:
            return RegistrantAuthStatusResponsePayload(authentication=None)
        return RegistrantAuthStatusResponsePayload(
            authentication=RegistrantAuthHistoryItem(
                authentication_id=auth.authentication_id,
                initiated_at=auth.initiated_at,
                status=auth.status,
                authentication_method=auth.authentication_method,
                initiated_by_staff_id=auth.initiated_by_staff_id,
                claim_verifications=auth.claim_verifications,
                expiry_at=auth.expiry_at,
                failure_reason=auth.failure_reason,
            )
        )

    async def get_history(
        self,
        request: RegistrantAuthHistoryRequest,
    ) -> RegistrantAuthHistoryResponsePayload:
        payload = request.request_body.request_payload
        authentications = await self.registrant_authentication_service.get_authentication_history(internal_record_id=payload.internal_record_id)
        return RegistrantAuthHistoryResponsePayload(
            authentications=[
                RegistrantAuthHistoryItem(
                    authentication_id=authentication.authentication_id,
                    initiated_at=authentication.initiated_at,
                    status=authentication.status,
                    authentication_method=authentication.authentication_method,
                    initiated_by_staff_id=authentication.initiated_by_staff_id,
                    claim_verifications=authentication.claim_verifications,
                    expiry_at=authentication.expiry_at,
                    failure_reason=authentication.failure_reason,
                )
                for authentication in authentications
            ]
        )

