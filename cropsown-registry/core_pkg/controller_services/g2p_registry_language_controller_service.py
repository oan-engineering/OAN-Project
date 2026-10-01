import logging

from openg2p_fastapi_common.service import BaseService

from ..schemas import (
    CreateLanguageRequest,
    CreateLanguageRequestPayload,
    GetAllLanguagesRequest,
    GetLanguageRequest,
    RegistryLanguageData,
    RemoveLanguageRequest,
    RemoveLanguageRequestPayload,
    UpdateLanguageRequest,
    UpdateLanguageRequestPayload,
)
from ..services import G2PRegisterService

_logger = logging.getLogger("g2p-registry-language-controller-service")


class G2PRegistryLanguageControllerService(BaseService):
    async def get_all_languages(self, get_request: GetAllLanguagesRequest) -> list[RegistryLanguageData]:
        _logger.info("Fetching all languages through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        return await g2p_register_service.get_all_languages()

    async def create_language(self, create_request: CreateLanguageRequest) -> RegistryLanguageData:
        create_language_request_payload: CreateLanguageRequestPayload = create_request.request_body.request_payload
        _logger.info(f"Creating language with code: {create_language_request_payload.language_code}")
        g2p_register_service = G2PRegisterService.get_component()
        registry_language_data: RegistryLanguageData = await g2p_register_service.create_language(
            language_code=create_language_request_payload.language_code,
            language_label=create_language_request_payload.language_label,
            language_flag_base64=create_language_request_payload.language_flag_base64,
            is_default=create_language_request_payload.is_default,
            core_translation=create_language_request_payload.core_translation,
            domain_translation=create_language_request_payload.domain_translation,
        )
        return registry_language_data

    async def get_language(self, get_request: GetLanguageRequest) -> RegistryLanguageData:
        payload = get_request.request_body.request_payload
        _logger.info(f"Fetching language with id: {payload.language_id}")

        g2p_register_service = G2PRegisterService.get_component()
        registry_languauge_data: RegistryLanguageData = await g2p_register_service.get_language(payload.language_id)
        return registry_languauge_data

    async def update_language(self, update_request: UpdateLanguageRequest) -> RegistryLanguageData:
        update_language_request_payload: UpdateLanguageRequestPayload = update_request.request_body.request_payload
        _logger.info(f"Updating language with id: {update_language_request_payload.language_id}")
        g2p_register_service = G2PRegisterService.get_component()
        registry_language_data: RegistryLanguageData = await g2p_register_service.update_language(
            language_id=update_language_request_payload.language_id,
            language_code=update_language_request_payload.language_code,
            language_label=update_language_request_payload.language_label,
            language_flag_base64=update_language_request_payload.language_flag_base64,
            is_default=update_language_request_payload.is_default,
            core_translation=update_language_request_payload.core_translation,
            domain_translation=update_language_request_payload.domain_translation,
        )
        return registry_language_data

    async def remove_language(self, remove_request: RemoveLanguageRequest) -> RegistryLanguageData:
        remove_language_request_payload: RemoveLanguageRequestPayload = remove_request.request_body.request_payload
        _logger.info(f"Removing language with id: {remove_language_request_payload.language_id}")
        g2p_register_service = G2PRegisterService.get_component()
        registry_language_data: RegistryLanguageData = await g2p_register_service.remove_language(
            remove_language_request_payload.language_id
        )
        return registry_language_data