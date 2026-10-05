import logging
from typing import Dict, Optional, Tuple

from openg2p_fastapi_common.service import BaseService
from openg2p_fastapi_common.context import dbengine

from ..models import IncomingRawData
from ..services import G2PIngestService
from ..schemas import IngestDataPayload

_logger = logging.getLogger('g2p-partner-contoller-service')
_engine = dbengine.get()

class G2PIngestControllerService(BaseService):

    async def ingest_data(
        self,
        data_model: Optional[str],
        ingest_data: Dict,
        register_id: Optional[str] = None,
        intake_form_id: Optional[str] = None,
    ) -> Tuple[IngestDataPayload, Optional[str]]:
        g2p_ingest_service = G2PIngestService.get_component()
        correlation_id, response_template_store_id = await g2p_ingest_service.ingest_data(
            data_model.upper() if data_model else None,
            ingest_data,
            register_id=register_id,
            intake_form_id=intake_form_id,
        )

        ingest_data_payload = IngestDataPayload(correlation_id=correlation_id)
        return ingest_data_payload, response_template_store_id
