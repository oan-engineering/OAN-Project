import logging
from abc import ABC, abstractmethod
from typing import Dict
from sqlalchemy.orm import Session
from openg2p_fastapi_common.context import dbengine

_logger = logging.getLogger('g2p-payload-enricher-service')
_engine = dbengine.get()

class G2PPayloadEnricherInterface(ABC):

    @abstractmethod
    async def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing payload enricher interface")
        pass