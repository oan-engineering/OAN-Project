from typing import List, Optional

from openg2p_fastapi_common.schemas import G2PResponse, G2PResponseBody

from .register_metadata_payload import (
    G2PRegisterSectionData,
    G2PRegisterUITabData,
    G2PRegisterUITabSectionData,
    RegisterSectionIdData,
    RegisterSectionUISchemaData,
    RegisterTabIdData,
    RegisterTabSectionIdData,
)


class RegisterTabMetadataDataResponseBody(G2PResponseBody):
    response_payload: Optional[G2PRegisterUITabData | RegisterTabIdData] = None


class RegisterTabMetadataDataResponse(G2PResponse):
    response_body: Optional[RegisterTabMetadataDataResponseBody] = None


class RegisterTabMetadataListResponseBody(G2PResponseBody):
    response_payload: Optional[List[G2PRegisterUITabData]] = None


class RegisterTabMetadataListResponse(G2PResponse):
    response_body: Optional[RegisterTabMetadataListResponseBody] = None


class RegisterTabSectionDataResponseBody(G2PResponseBody):
    response_payload: Optional[G2PRegisterUITabSectionData | RegisterTabSectionIdData] = None


class RegisterTabSectionDataResponse(G2PResponse):
    response_body: Optional[RegisterTabSectionDataResponseBody] = None


class RegisterTabSectionsDataResponseBody(G2PResponseBody):
    response_payload: Optional[List[G2PRegisterUITabSectionData]] = None


class RegisterTabSectionsDataResponse(G2PResponse):
    response_body: Optional[RegisterTabSectionsDataResponseBody] = None


class RegisterSectionMetadataDataResponseBody(G2PResponseBody):
    response_payload: Optional[G2PRegisterSectionData | RegisterSectionIdData] = None


class RegisterSectionMetadataDataResponse(G2PResponse):
    response_body: Optional[RegisterSectionMetadataDataResponseBody] = None


class RegisterSectionMetadataListResponseBody(G2PResponseBody):
    response_payload: Optional[List[G2PRegisterSectionData]] = None


class RegisterSectionMetadataListResponse(G2PResponse):
    response_body: Optional[RegisterSectionMetadataListResponseBody] = None


class RegisterSectionMetadataUISchemaDataResponseBody(G2PResponseBody):
    response_payload: Optional[RegisterSectionUISchemaData] = None


class RegisterSectionMetadataUISchemaDataResponse(G2PResponse):
    response_body: Optional[RegisterSectionMetadataUISchemaDataResponseBody] = None
