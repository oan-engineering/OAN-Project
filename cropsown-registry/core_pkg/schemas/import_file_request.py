from openg2p_fastapi_common.schemas import G2PRequest, G2PRequestBody

from .import_file_payload import ImportFileConfigurationRequestPayload


class ImportFileConfigurationRequestBody(G2PRequestBody):
    request_payload: ImportFileConfigurationRequestPayload


class ImportFileConfigurationRequest(G2PRequest):
    request_body: ImportFileConfigurationRequestBody

