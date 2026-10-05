from typing import Optional, List
from openg2p_fastapi_common.schemas import (
    G2PResponse,
    G2PResponseBody,
)
from .vc_payload import VcConfigurationData


# =============================================================================
# VC Response Schemas
# =============================================================================

class VcConfigurationResponseBody(G2PResponseBody):
    response_payload: Optional[List[VcConfigurationData]] = None


class VcConfigurationResponse(G2PResponse):
    response_body: Optional[VcConfigurationResponseBody] = None
