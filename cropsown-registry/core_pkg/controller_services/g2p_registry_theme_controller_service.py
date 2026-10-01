import logging

from openg2p_fastapi_common.service import BaseService

from ..schemas import (
    CreateThemeRequest,
    GetAllThemesRequest,
    GetThemeValuesRequest,
    RegistryThemeData,
    RegistryThemeValueData,
    RemoveThemeRequest,
    ThemeOperationData,
    UpdateThemeValuesRequest,
    CreateThemeRequestPayload,
    RemoveThemeRequestPayload,
    UpdateThemeValuesRequestPayload,
    GetThemeValuesRequestPayload
)
from ..services import G2PRegisterService

_logger = logging.getLogger("g2p-registry-theme-controller-service")


class G2PRegistryThemeControllerService(BaseService):
    async def get_all_themes(self, get_request: GetAllThemesRequest) -> list[RegistryThemeData]:
        _logger.info("Fetching all themes through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        registry_theme_data_list: list[RegistryThemeData] = await g2p_register_service.get_all_themes()
        return registry_theme_data_list

    async def create_theme(self, create_request: CreateThemeRequest) -> ThemeOperationData:
        create_theme_request_payload: CreateThemeRequestPayload = create_request.request_body.request_payload
        _logger.info(f"Creating theme with mnemonic: {create_theme_request_payload.theme_mnemonic}")
        g2p_register_service = G2PRegisterService.get_component()
        theme_operation_data: ThemeOperationData = await g2p_register_service.create_theme(
            theme_mnemonic=create_theme_request_payload.theme_mnemonic,
            theme_values=create_theme_request_payload.theme_values,
        )
        return theme_operation_data

    async def remove_theme(self, remove_request: RemoveThemeRequest) -> ThemeOperationData:
        remove_theme_request_payload: RemoveThemeRequestPayload = remove_request.request_body.request_payload
        _logger.info(f"Removing theme with id: {remove_theme_request_payload.theme_id}")
        g2p_register_service = G2PRegisterService.get_component()
        theme_operation_data: ThemeOperationData = await g2p_register_service.remove_theme(theme_id=remove_theme_request_payload.theme_id)
        return theme_operation_data

    async def update_theme_values(self, update_request: UpdateThemeValuesRequest) -> ThemeOperationData:
        update_theme_values_request_payload: UpdateThemeValuesRequestPayload = update_request.request_body.request_payload
        _logger.info(f"Updating theme values for theme id: {update_theme_values_request_payload.theme_id}")
        g2p_register_service = G2PRegisterService.get_component()
        theme_operation_data: ThemeOperationData = await g2p_register_service.update_theme_values(
            theme_id=update_theme_values_request_payload.theme_id,
            theme_attribute_values=update_theme_values_request_payload.theme_attribute_values,
        )
        return theme_operation_data

    async def get_theme_values(self, get_request: GetThemeValuesRequest) -> list[RegistryThemeValueData]:
        get_theme_values_request_payload: GetThemeValuesRequestPayload = get_request.request_body.request_payload
        _logger.info(f"Fetching theme values for theme id: {get_theme_values_request_payload.theme_id}")
        g2p_register_service = G2PRegisterService.get_component()
        registry_theme_value_data_list: list[RegistryThemeValueData] = await g2p_register_service.get_theme_values(theme_id=get_theme_values_request_payload.theme_id)
        return registry_theme_value_data_list
