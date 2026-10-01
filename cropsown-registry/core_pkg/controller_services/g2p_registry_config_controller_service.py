import logging
from openg2p_fastapi_common.service import BaseService

from ..services import G2PRegisterService
from ..schemas import (
    CreateRegistryConfigurationRequest,
    GetRegistryConfigurationRequest,
    UpdateRegistryConfigurationRequest,
    GetNumberOfRequestsPendingRequest,
    GetEarliestPendingChangeRequestRequest,
    RegistryConfigurationData,
    NumberOfRequestsPendingData,
    EarliestPendingChangeRequestData
)

_logger = logging.getLogger('g2p-registry-controller-service')


class G2PRegistryConfigurationControllerService(BaseService):

    async def create_registry_configuration(
        self, 
        create_request: CreateRegistryConfigurationRequest
    ) -> RegistryConfigurationData:
        """Create a new registry configuration"""
        payload = create_request.request_body.request_payload
        _logger.info(f"Creating registry configuration with name: {payload.registry_name}")
        g2p_register_service = G2PRegisterService.get_component()
        registry_configuration_data: RegistryConfigurationData = await g2p_register_service.create_registry_configuration(
            registry_name=payload.registry_name,
            registry_logo=payload.registry_logo,
            registry_favicon=payload.registry_favicon,
            registry_theme_id=payload.registry_theme_id,
            registry_language_id=payload.registry_language_id
        )
        return registry_configuration_data

    async def get_registry_configuration(
        self, 
        get_request: GetRegistryConfigurationRequest
    ) -> RegistryConfigurationData:
        """Get the registry configuration"""
        _logger.info("Fetching registry configuration through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        registry_configuration_data: RegistryConfigurationData = await g2p_register_service.get_registry_configuration()
        return registry_configuration_data

    async def update_registry_configuration(
        self, 
        update_request: UpdateRegistryConfigurationRequest
    ) -> RegistryConfigurationData:
        """Update the registry configuration"""
        payload = update_request.request_body.request_payload
        _logger.info(f"Updating registry configuration with id: {payload.configuration_id}")
        g2p_register_service = G2PRegisterService.get_component()
        registry_configuration_data: RegistryConfigurationData = await g2p_register_service.update_registry_configuration(
            configuration_id=payload.configuration_id,
            registry_name=payload.registry_name,
            registry_logo=payload.registry_logo,
            registry_favicon=payload.registry_favicon,
            registry_theme_id=payload.registry_theme_id,
            registry_language_id=payload.registry_language_id
        )
        return registry_configuration_data

    async def get_number_of_requests_pending(
        self, 
        get_request: GetNumberOfRequestsPendingRequest
    ) -> NumberOfRequestsPendingData:
        """Get the number of pending change requests across all registers"""
        _logger.info("Fetching number of pending requests through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        number_of_requests_pending: int = await g2p_register_service.get_total_pending_change_requests()
        return NumberOfRequestsPendingData(number_of_requests_pending=number_of_requests_pending)

    async def get_earliest_pending_change_request(
        self, 
        get_request: GetEarliestPendingChangeRequestRequest
    ) -> EarliestPendingChangeRequestData:
        """Get the earliest pending change request"""
        _logger.info("Fetching earliest pending change request through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        earliest_change_request: EarliestPendingChangeRequestData = await g2p_register_service.get_earliest_pending_change_request()
        return earliest_change_request

