import logging
from typing import Optional

from openg2p_fastapi_common.service import BaseService

from ..schemas import DataModelData, DataModelPayload, DataModelUpdatePayload
from ..services import G2PDataModelService

_logger = logging.getLogger("g2p-data-model-controller-service")


class G2PDataModelControllerService(BaseService):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.g2p_data_model_service = G2PDataModelService.get_component()

    async def create_data_model(self, data_model_payload: DataModelPayload) -> DataModelData:
        return await self.g2p_data_model_service.create_data_model(data_model_payload)

    async def get_data_model(self, data_model_id: str) -> DataModelData:
        return await self.g2p_data_model_service.get_data_model(data_model_id)

    async def get_all_data_models(
        self, current_page: Optional[int] = 1, page_size: Optional[int] = 10
    ) -> tuple[list[DataModelData], int, int]:
        current_page = current_page or 1
        page_size = page_size or 10
        return await self.g2p_data_model_service.get_all_data_models(
            current_page, page_size
        )

    async def update_data_model(
        self, data_model_id: str, data_model_payload: DataModelUpdatePayload
    ) -> DataModelData:
        return await self.g2p_data_model_service.update_data_model(
            data_model_id, data_model_payload
        )

    async def delete_data_model(self, data_model_id: str) -> DataModelData:
        return await self.g2p_data_model_service.delete_data_model(data_model_id)
