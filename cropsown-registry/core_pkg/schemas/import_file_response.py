from typing import List, Optional

from openg2p_fastapi_common.schemas import G2PResponse, G2PResponseBody

from .import_file_payload import ImportFileConfigurationData


class ImportFileConfigurationResponseBody(G2PResponseBody):
    response_payload: Optional[List[ImportFileConfigurationData]] = None


class ImportFileConfigurationResponse(G2PResponse):
    response_body: Optional[ImportFileConfigurationResponseBody] = None

