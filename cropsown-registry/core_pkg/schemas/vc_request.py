from openg2p_fastapi_common.schemas import (
    G2PRequest,
    G2PRequestBody,
)
from .vc_payload import VcConfigurationRequestPayload


# =============================================================================
# VC Request Schemas
# =============================================================================

class VcConfigurationRequestBody(G2PRequestBody):
    request_payload: VcConfigurationRequestPayload


class VcConfigurationRequest(G2PRequest):
    request_body: VcConfigurationRequestBody
