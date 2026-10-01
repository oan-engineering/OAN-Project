import importlib
from openg2p_fastapi_common.service import BaseService
from .g2p_payload_enricher_interface import G2PPayloadEnricherInterface

class G2PPayloadEnricherFactory(BaseService):
    
    def get_enricher_service(
        self,
        raw_payload_enricher_class: str,
    ) -> G2PPayloadEnricherInterface:

        module = importlib.import_module("openg2p_registry_extensions.ingestion_pipeline.enricher_services")
        enricher_service = getattr(module, raw_payload_enricher_class)
        g2p_payload_enricher_interface: G2PPayloadEnricherInterface = enricher_service()

        return g2p_payload_enricher_interface
