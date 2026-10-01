import logging

from openg2p_fastapi_common.service import BaseService

from ..services import G2POutgestionDataService
from ..schemas import (
    OutgestionSummaryData,
    GetOutgestionSummaryDataRequest,
    OutgestionDataSearchResultData,
    SearchOutgestionDataRequest,
)

_logger = logging.getLogger("g2p-outgestion-data-controller-service")


class G2POutgestionDataControllerService(BaseService):

    async def get_outgestion_summary_data(
        self, get_outgestion_summary_data_request: GetOutgestionSummaryDataRequest
    ) -> OutgestionSummaryData:
        _logger.info("Fetching outgestion summary data through controller service")
        g2p_outgestion_data_service = G2POutgestionDataService.get_component()
        return await g2p_outgestion_data_service.get_outgestion_summary_data()

    async def search_in_outgestion_data(
        self, search_outgestion_data_request: SearchOutgestionDataRequest
    ) -> tuple[list[OutgestionDataSearchResultData], int, int]:
        pagination = search_outgestion_data_request.request_body.pagination_request

        _logger.info(
            "Searching in outgestion with search_text: %s, page: %s, page_size: %s through controller service",
            pagination.search_text,
            pagination.current_page,
            pagination.page_size,
        )
        g2p_outgestion_data_service = G2POutgestionDataService.get_component()
        search_results_list, total_items = await g2p_outgestion_data_service.search_in_outgestion_data(
            pagination.search_text,
            pagination.current_page,
            pagination.page_size,
            pagination.sort_by,
            pagination.filter_by,
        )

        number_of_pages = (
            (total_items + pagination.page_size - 1) // pagination.page_size if total_items > 0 else 0
        )

        return search_results_list, total_items, number_of_pages
