from openg2p_fastapi_common.schemas import (
    G2PRequest,
    G2PRequestBody,
)
from .awe_payload import (
    CreateAwePolicyConfigurationRequestPayload,
    DeleteAwePolicyConfigurationRequestPayload,
    GetAllAwePolicyConfigurationsRequestPayload,
    GetAwePolicyConfigurationRequestPayload,
    UpdateAwePolicyConfigurationRequestPayload,
)


# =============================================================================
# AWE policy configuration request schemas
# =============================================================================


class CreateAwePolicyConfigurationRequestBody(G2PRequestBody):
    request_payload: CreateAwePolicyConfigurationRequestPayload


class CreateAwePolicyConfigurationRequest(G2PRequest):
    request_body: CreateAwePolicyConfigurationRequestBody


class UpdateAwePolicyConfigurationRequestBody(G2PRequestBody):
    request_payload: UpdateAwePolicyConfigurationRequestPayload


class UpdateAwePolicyConfigurationRequest(G2PRequest):
    request_body: UpdateAwePolicyConfigurationRequestBody


class GetAwePolicyConfigurationRequestBody(G2PRequestBody):
    request_payload: GetAwePolicyConfigurationRequestPayload


class GetAwePolicyConfigurationRequest(G2PRequest):
    request_body: GetAwePolicyConfigurationRequestBody


class DeleteAwePolicyConfigurationRequestBody(G2PRequestBody):
    request_payload: DeleteAwePolicyConfigurationRequestPayload


class DeleteAwePolicyConfigurationRequest(G2PRequest):
    request_body: DeleteAwePolicyConfigurationRequestBody


class GetAllAwePolicyConfigurationsRequestBody(G2PRequestBody):
    request_payload: GetAllAwePolicyConfigurationsRequestPayload


class GetAllAwePolicyConfigurationsRequest(G2PRequest):
    request_body: GetAllAwePolicyConfigurationsRequestBody
