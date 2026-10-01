from typing import Optional

from openg2p_fastapi_common.schemas import G2PResponse, G2PResponseBody

from .input_mechanism_payload import EnqueueImportFileData


class EnqueueImportFileResponseBody(G2PResponseBody):
    response_payload: Optional[EnqueueImportFileData] = None


class EnqueueImportFileResponse(G2PResponse):
    response_body: Optional[EnqueueImportFileResponseBody] = None

