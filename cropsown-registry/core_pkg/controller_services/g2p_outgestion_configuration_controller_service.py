import logging
from typing import Optional
from openg2p_fastapi_common.service import BaseService

from ..services import G2POutgestionConfigurationService
from ..schemas import (
    OutgoingTopicPayload,
    OutgoingTopicUpdatePayload,
    OutgoingTopicData,
    OutgoingTemplatePayload,
    OutgoingTemplateUpdatePayload,
    OutgoingTemplateData,
)

_logger = logging.getLogger("g2p-outgestion-configuration-controller-service")


class G2POutgestionConfigurationControllerService(BaseService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.g2p_outgestion_configuration_service = G2POutgestionConfigurationService.get_component()

    async def create_outgoing_topic(
        self, outgoing_topic_payload: OutgoingTopicPayload
    ) -> OutgoingTopicData:
        """Create a new outgoing topic"""
        return await self.g2p_outgestion_configuration_service.create_outgoing_topic(
            outgoing_topic_payload
        )

    async def get_outgoing_topic(self, topic_id: str) -> OutgoingTopicData:
        """Get outgoing topic by ID"""
        return await self.g2p_outgestion_configuration_service.get_outgoing_topic(topic_id)

    async def get_all_outgoing_topics(
        self, current_page: Optional[int] = 1, page_size: Optional[int] = 10
    ) -> tuple[list[OutgoingTopicData], int, int]:
        """Get paginated outgoing topics."""
        current_page = current_page or 1
        page_size = page_size or 10
        return await self.g2p_outgestion_configuration_service.get_all_outgoing_topics(
            current_page, page_size
        )

    async def update_outgoing_topic(
        self, outgoing_topic_update_payload: OutgoingTopicUpdatePayload
    ) -> OutgoingTopicData:
        """Update outgoing topic"""
        return await self.g2p_outgestion_configuration_service.update_outgoing_topic(
            outgoing_topic_update_payload
        )
    
    async def toggle_outgoing_topic_status(self, topic_id: str) -> OutgoingTopicData:
        """Toggle outgoing topic status"""
        return await self.g2p_outgestion_configuration_service.toggle_outgoing_topic_status(topic_id)
    
    async def re_register_outgoing_topic(self, topic_id: str) -> OutgoingTopicData:
        """Re-register outgoing topic"""
        return await self.g2p_outgestion_configuration_service.re_register_outgoing_topic(topic_id)

    async def delete_outgoing_topic(self, topic_id: str) -> OutgoingTopicData:
        """Delete outgoing topic"""
        return await self.g2p_outgestion_configuration_service.delete_outgoing_topic(topic_id)

    async def create_template(
        self, template_payload: OutgoingTemplatePayload
    ) -> OutgoingTemplateData:
        """Create a new template"""
        return await self.g2p_outgestion_configuration_service.create_template(
            template_payload
        )

    async def get_template(self, template_id: str) -> OutgoingTemplateData:
        """Get template by ID"""
        return await self.g2p_outgestion_configuration_service.get_template(template_id)

    async def get_all_templates(
        self, current_page: Optional[int] = 1, page_size: Optional[int] = 10
    ) -> tuple[list[OutgoingTemplateData], int, int]:
        """Get paginated templates."""
        current_page = current_page or 1
        page_size = page_size or 10
        return await self.g2p_outgestion_configuration_service.get_all_templates(
            current_page, page_size
        )

    async def update_template(
        self, template_update_payload: OutgoingTemplateUpdatePayload
    ) -> OutgoingTemplateData:
        """Update template"""
        return await self.g2p_outgestion_configuration_service.update_template(
            template_update_payload
        )

    async def delete_template(self, template_id: str) -> OutgoingTemplateData:
        """Delete template"""
        return await self.g2p_outgestion_configuration_service.delete_template(template_id)