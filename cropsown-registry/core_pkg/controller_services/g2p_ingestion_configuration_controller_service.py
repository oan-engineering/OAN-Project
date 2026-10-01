import logging
from typing import Optional
from openg2p_fastapi_common.service import BaseService

from ..services import G2PIngestionConfigurationService
from ..schemas import (
    IncomingModelKeyPathPayload,
    IncomingModelKeyPathUpdatePayload,
    IncomingModelKeyPathData,
    IncomingModelKeyPathListData,
    IncomingModelSemanticPatternPayload,
    IncomingModelSemanticPatternUpdatePayload,
    IncomingModelSemanticPatternData,
    IncomingModelRegisterSemanticPatternPayload,
    IncomingModelRegisterSemanticPatternUpdatePayload,
    IncomingModelRegisterSemanticPatternData,
    IncomingTemplatePayload,
    IncomingTemplateUpdatePayload,
    IncomingTemplateData,
    SubscriptionActivityLogPayload,
    SubscriptionActivityLogData,
)

_logger = logging.getLogger("g2p-ingestion-configuration-controller-service")


class G2PIngestionConfigurationControllerService(BaseService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.g2p_ingestion_configuration_service = G2PIngestionConfigurationService.get_component()

    # IncomingModelKeyPath Methods
    async def create_incoming_key_path(
        self, pattern_payload: IncomingModelKeyPathPayload
    ) -> IncomingModelKeyPathData:
        """Create a new incoming key path"""
        return await self.g2p_ingestion_configuration_service.create_incoming_key_path(
            pattern_payload
        )

    async def get_incoming_key_path(self, key_path_id: str) -> IncomingModelKeyPathData:
        """Get incoming key path by ID"""
        return await self.g2p_ingestion_configuration_service.get_incoming_key_path(
            key_path_id
        )

    async def get_all_incoming_key_paths(
        self, current_page: Optional[int] = 1, page_size: Optional[int] = 10
    ) -> tuple[list[IncomingModelKeyPathListData], int, int]:
        """Get paginated incoming key paths."""
        current_page = current_page or 1
        page_size = page_size or 10
        return await self.g2p_ingestion_configuration_service.get_all_incoming_key_paths(
            current_page, page_size
        )

    async def update_incoming_key_path(
        self, key_path_id: str, pattern_payload: IncomingModelKeyPathUpdatePayload
    ) -> IncomingModelKeyPathData:
        """Update incoming key path"""
        return await self.g2p_ingestion_configuration_service.update_incoming_key_path(
            key_path_id, pattern_payload
        )

    async def delete_incoming_key_path(self, key_path_id: str) -> IncomingModelKeyPathData:
        """Delete incoming key path"""
        return await self.g2p_ingestion_configuration_service.delete_incoming_key_path(
            key_path_id
        )

    async def create_semantic_pattern(
        self, pattern_payload: IncomingModelSemanticPatternPayload
    ) -> IncomingModelSemanticPatternData:
        """Create a new semantic pattern"""
        return await self.g2p_ingestion_configuration_service.create_semantic_pattern(
            pattern_payload
        )

    async def get_semantic_pattern(
        self, semantic_pattern_id: str
    ) -> IncomingModelSemanticPatternData:
        """Get semantic pattern by ID"""
        return await self.g2p_ingestion_configuration_service.get_semantic_pattern(
            semantic_pattern_id
        )

    async def get_all_semantic_patterns(
        self, current_page: Optional[int] = 1, page_size: Optional[int] = 10
    ) -> tuple[list[IncomingModelSemanticPatternData], int, int]:
        """Get paginated semantic patterns."""
        current_page = current_page or 1
        page_size = page_size or 10
        return await self.g2p_ingestion_configuration_service.get_all_semantic_patterns(
            current_page, page_size
        )

    async def update_semantic_pattern(
        self, semantic_pattern_id: str, pattern_payload: IncomingModelSemanticPatternUpdatePayload
    ) -> IncomingModelSemanticPatternData:
        """Update semantic pattern"""
        return await self.g2p_ingestion_configuration_service.update_semantic_pattern(
            semantic_pattern_id, pattern_payload
        )

    async def delete_semantic_pattern(self, semantic_pattern_id: str) -> IncomingModelSemanticPatternData:
        """Delete semantic pattern"""
        return await self.g2p_ingestion_configuration_service.delete_semantic_pattern(
            semantic_pattern_id
        )

    async def create_register_semantic_pattern(
        self, pattern_payload: IncomingModelRegisterSemanticPatternPayload
    ) -> IncomingModelRegisterSemanticPatternData:
        return await self.g2p_ingestion_configuration_service.create_register_semantic_pattern(
            pattern_payload
        )

    async def get_register_semantic_pattern(
        self, register_semantic_pattern_id: str
    ) -> IncomingModelRegisterSemanticPatternData:
        return await self.g2p_ingestion_configuration_service.get_register_semantic_pattern(
            register_semantic_pattern_id
        )

    async def get_all_register_semantic_patterns(
        self, current_page: Optional[int] = 1, page_size: Optional[int] = 10
    ) -> tuple[list[IncomingModelRegisterSemanticPatternData], int, int]:
        current_page = current_page or 1
        page_size = page_size or 10
        return await self.g2p_ingestion_configuration_service.get_all_register_semantic_patterns(
            current_page, page_size
        )

    async def update_register_semantic_pattern(
        self, pattern_payload: IncomingModelRegisterSemanticPatternUpdatePayload
    ) -> IncomingModelRegisterSemanticPatternData:
        return await self.g2p_ingestion_configuration_service.update_register_semantic_pattern(
            pattern_payload
        )

    async def delete_register_semantic_pattern(
        self, register_semantic_pattern_id: str
    ) -> IncomingModelRegisterSemanticPatternData:
        return await self.g2p_ingestion_configuration_service.delete_register_semantic_pattern(
            register_semantic_pattern_id
        )

    async def create_template(
        self, template_payload: IncomingTemplatePayload
    ) -> IncomingTemplateData:
        """Create a new template"""
        return await self.g2p_ingestion_configuration_service.create_template(
            template_payload
        )

    async def get_template(self, template_id: str) -> IncomingTemplateData:
        """Get template by ID"""
        return await self.g2p_ingestion_configuration_service.get_template(template_id)

    async def get_all_templates(
        self, current_page: Optional[int] = 1, page_size: Optional[int] = 10
    ) -> tuple[list[IncomingTemplateData], int, int]:
        """Get paginated templates."""
        current_page = current_page or 1
        page_size = page_size or 10
        return await self.g2p_ingestion_configuration_service.get_all_templates(
            current_page, page_size
        )

    async def update_template(
        self, template_update_payload: IncomingTemplateUpdatePayload
    ) -> IncomingTemplateData:
        """Update template"""
        return await self.g2p_ingestion_configuration_service.update_template(
            template_update_payload
        )

    async def delete_template(self, template_id: str) -> IncomingTemplateData:
        """Delete template"""
        return await self.g2p_ingestion_configuration_service.delete_template(template_id)

    async def create_subscription_activity_log(
        self, subscription_activity_log_payload: SubscriptionActivityLogPayload
    ) -> SubscriptionActivityLogData:
        """Create a new subscription activity log"""
        return await self.g2p_ingestion_configuration_service.create_subscription_activity_log(
            subscription_activity_log_payload
        )

    async def get_subscription_activity_logs_by_partner(
        self, partner_id: str
    ) -> list[SubscriptionActivityLogData]:
        """Get all subscription activity logs for a partner"""
        return await self.g2p_ingestion_configuration_service.get_subscription_activity_logs_by_partner(
            partner_id
        )

    async def get_all_subscription_activity_logs(
        self, current_page: Optional[int] = 1, page_size: Optional[int] = 10
    ) -> tuple[list[SubscriptionActivityLogData], int, int]:
        """Get paginated subscription activity logs."""
        current_page = current_page or 1
        page_size = page_size or 10
        return await self.g2p_ingestion_configuration_service.get_all_subscription_activity_logs(
            current_page, page_size
        )
