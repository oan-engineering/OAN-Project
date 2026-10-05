from openg2p_fastapi_common.schemas import G2PRequest, G2PRequestBody

from .input_mechanism_payload import EnqueueImportFileRequestPayload


class EnqueueImportFileRequestBody(G2PRequestBody):
    request_payload: EnqueueImportFileRequestPayload


class EnqueueImportFileRequest(G2PRequest):
    request_body: EnqueueImportFileRequestBody

