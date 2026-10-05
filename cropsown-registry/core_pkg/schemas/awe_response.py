from typing import List, Optional

from openg2p_fastapi_common.schemas import (
    G2PResponse,
    G2PResponseBody,
)
from .awe_payload import AwePolicyConfigurationData


# =============================================================================
# AWE policy configuration response schemas
# =============================================================================


class AwePolicyConfigurationDataResponseBody(G2PResponseBody):
    response_payload: Optional[AwePolicyConfigurationData] = None


class AwePolicyConfigurationDataResponse(G2PResponse):
    response_body: Optional[AwePolicyConfigurationDataResponseBody] = None


class AwePolicyConfigurationListResponseBody(G2PResponseBody):
    response_payload: Optional[List[AwePolicyConfigurationData]] = None


class AwePolicyConfigurationListResponse(G2PResponse):
    response_body: Optional[AwePolicyConfigurationListResponseBody] = None
