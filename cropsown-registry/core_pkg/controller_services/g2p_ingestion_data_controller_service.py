import logging
from openg2p_fastapi_common.service import BaseService

from ..services import G2PIngestionDataService
from ..schemas import (
    IngestionSummaryData,
    GetIngestionSummaryDataRequest,
    IngestionDataSearchResultData,
    SearchIngestionDataRequest,
    GetIngestionDataPayloadRequest,
    IngestionDataPayload
)

_logger = logging.getLogger('g2p-ingestion-data-controller-service')


class G2PIngestionDataControllerService(BaseService):

    async def get_ingestion_summary_data(self, get_ingestion_summary_data_request: GetIngestionSummaryDataRequest) -> IngestionSummaryData:
        _logger.info("Fetching ingestion summary data through controller service")
        g2p_ingestion_data_service = G2PIngestionDataService.get_component()
        ingestion_summary_data: IngestionSummaryData = await g2p_ingestion_data_service.get_ingestion_summary_data()
        return ingestion_summary_data

    async def search_in_ingestion_data(self, search_ingestion_data_request: SearchIngestionDataRequest) -> tuple[list[IngestionDataSearchResultData], int, int]:
        pagination = search_ingestion_data_request.request_body.pagination_request

        _logger.info(f"Searching in ingestion with search_text: {pagination.search_text}, page: {pagination.current_page}, page_size: {pagination.page_size} through controller service")
        g2p_ingestion_data_service = G2PIngestionDataService.get_component()
        search_results_list, total_items = await g2p_ingestion_data_service.search_in_ingestion_data(
            pagination.search_text, pagination.current_page, pagination.page_size, pagination.sort_by, pagination.filter_by
        )

        # Calculate number of pages
        number_of_pages = (total_items + pagination.page_size - 1) // pagination.page_size if total_items > 0 else 0

        return search_results_list, total_items, number_of_pages

    async def get_raw_data_payload(self, get_ingestion_data_payload_request: GetIngestionDataPayloadRequest) -> IngestionDataPayload:
        _logger.info("Fetching raw payload through controller service")
        g2p_ingestion_data_service = G2PIngestionDataService.get_component()
        raw_data_payload: IngestionDataPayload = await g2p_ingestion_data_service.get_raw_data_payload(
            get_ingestion_data_payload_request.request_body.request_payload.ingest_id
        )
        return raw_data_payload
    
    async def get_enriched_and_transformed_data_payload(self, get_ingestion_data_payload_request: GetIngestionDataPayloadRequest) -> IngestionDataPayload:
        _logger.info("Fetching enriched and transformed data payload through controller service")
        g2p_ingestion_data_service = G2PIngestionDataService.get_component()
        enriched_and_transformed_data_payload: IngestionDataPayload = await g2p_ingestion_data_service.get_enriched_and_transformed_data_payload(
            get_ingestion_data_payload_request.request_body.request_payload.ingest_id
        )
        return enriched_and_transformed_data_payload

