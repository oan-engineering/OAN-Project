import logging
from typing import Dict

from openg2p_registry_core.interfaces import G2PPayloadEnricherInterface
from sqlalchemy.orm import Session

_logger = logging.getLogger('g2p-payload-enricher-service')

# DCI Payload Enrichers
class G2PDciCropSownCreateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PDciCropSownCreateEnricherService")
        return data

class G2PDciCropSownUpdateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PDciCropSownUpdateEnricherService")
        return data

class G2PDciCropSownDeleteEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PDciCropSownDeleteEnricherService")
        return data

# SPDCI Payload Enrichers
class G2PSpdciCropSownCreateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PSpdciCropSownCreateEnricherService")
        return data

class G2PSpdciCropSownUpdateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PSpdciCropSownUpdateEnricherService")
        return data

class G2PSpdciCropSownDeleteEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PSpdciCropSownDeleteEnricherService")
        return data

# UNDP Payload Enrichers
class G2PUndpCropSownCreateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PUndpCropSownCreateEnricherService")
        return data

class G2PUndpCropSownUpdateEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PUndpCropSownUpdateEnricherService")
        return data

class G2PUndpCropSownDeleteEnricherService(G2PPayloadEnricherInterface):
    def enrich(self, data: Dict, session: Session) -> Dict:
        _logger.info("Processing G2PUndpCropSownDeleteEnricherService")
        return data
