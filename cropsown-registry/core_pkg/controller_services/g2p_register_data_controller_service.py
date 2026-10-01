import logging
from openg2p_fastapi_common.service import BaseService

from ..services import G2PRegisterService, G2PRegisterHierarchicalService
from ..schemas import (
    NumberOfVersionsData, RecordData, RegisterTabRecordData,
    RecordHistoryListData, VersionDatesData, VersionsForDateData,
    DeduplicationRegisterResultData, DeduplicationChangerequestResultData,
    GetNumberOfVersionsRequest, GetSubjectRecordRequest,
    GetRecordHistoryRequest, GetVersionDatesRequest, GetChangesForDateRequest,
    GetDeduplicationRegisterResultsRequest,
    GetDeduplicationChangerequestResultsRequest,
    GetRegisterSectionRequest, RegisterSectionData,
    GetSectionRecordsRequest, GetRegisterTabRecordsRequest,
    GetRegisterSummaryDataRequest, RegisterSummaryData,
    SearchRegisterRequest, SearchResultData,
    GetAllowedParentsForChildSectionRequest, AllowedParentsData
)

_logger = logging.getLogger('g2p-register-data-controller-service')


class G2PRegisterDataControllerService(BaseService):

    async def get_number_of_versions(self, get_number_of_versions_request: GetNumberOfVersionsRequest) -> NumberOfVersionsData:
        register_id = get_number_of_versions_request.request_body.request_payload.register_id
        internal_record_id = get_number_of_versions_request.request_body.request_payload.internal_record_id
        tab_id = get_number_of_versions_request.request_body.request_payload.tab_id
        _logger.info(f"Getting number of versions for register_id: {register_id}, internal_record_id: {internal_record_id}, tab_id: {tab_id} through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        number_of_versions_data: NumberOfVersionsData = await g2p_register_service.get_number_of_versions(register_id, internal_record_id, tab_id)
        return number_of_versions_data

    async def get_record_history(
        self,
        get_record_history_request: GetRecordHistoryRequest,
        policy_mnemonics: list[str] | None = None,
    ) -> RecordHistoryListData:
        """Get the history records for a given register, internal_record_id and tab_id"""
        register_id = get_record_history_request.request_body.request_payload.register_id
        internal_record_id = get_record_history_request.request_body.request_payload.internal_record_id
        tab_id = get_record_history_request.request_body.request_payload.tab_id
        _logger.info(f"Getting record history for register_id: {register_id}, internal_record_id: {internal_record_id}, tab_id: {tab_id} through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        record_history_data: RecordHistoryListData = await g2p_register_service.get_record_history(
            register_id, internal_record_id, tab_id, policy_mnemonics=policy_mnemonics
        )
        return record_history_data

    async def get_version_dates(self, get_version_dates_request: GetVersionDatesRequest) -> VersionDatesData:
        """Get unique truncated dates from history records for a given register, internal_record_id and tab_id"""
        register_id = get_version_dates_request.request_body.request_payload.register_id
        internal_record_id = get_version_dates_request.request_body.request_payload.internal_record_id
        tab_id = get_version_dates_request.request_body.request_payload.tab_id
        _logger.info(f"Getting version dates for register_id: {register_id}, internal_record_id: {internal_record_id}, tab_id: {tab_id} through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        version_dates_data: VersionDatesData = await g2p_register_service.get_version_dates(register_id, internal_record_id, tab_id)
        return version_dates_data

    async def get_versions_for_a_date(self, get_changes_for_date_request: GetChangesForDateRequest) -> list[VersionsForDateData]:
        """Get changes from history records for a given register, internal_record_id, tab_id and specific date"""
        register_id = get_changes_for_date_request.request_body.request_payload.register_id
        internal_record_id = get_changes_for_date_request.request_body.request_payload.internal_record_id
        tab_id = get_changes_for_date_request.request_body.request_payload.tab_id
        truncated_created_date = get_changes_for_date_request.request_body.request_payload.truncated_created_date
        _logger.info(f"Getting changes for date for register_id: {register_id}, internal_record_id: {internal_record_id}, tab_id: {tab_id}, truncated_created_date: {truncated_created_date} through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        changes_for_date_data: list[VersionsForDateData] = await g2p_register_service.get_versions_for_a_date(register_id, internal_record_id, tab_id, truncated_created_date)
        return changes_for_date_data

    async def get_subject_record(
        self,
        get_subject_record_request: GetSubjectRecordRequest,
        policy_mnemonics: list[str] | None = None,
    ) -> RecordData:
        subject_register_id = get_subject_record_request.request_body.request_payload.subject_register_id
        subject_record_id = get_subject_record_request.request_body.request_payload.subject_record_id
        _logger.info(f"Getting subject record for subject_register_id: {subject_register_id}, subject_record_id: {subject_record_id} through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        record_data: RecordData = await g2p_register_service.get_record(
            subject_register_id,
            subject_record_id,
            policy_mnemonics=policy_mnemonics,
        )
        return record_data

    async def get_deduplication_register_results(self, get_deduplication_register_results_request: GetDeduplicationRegisterResultsRequest) -> tuple[list[DeduplicationRegisterResultData], int, int]:
        """
        Get deduplication results for a change request against register records.
        """
        payload = get_deduplication_register_results_request.request_body.request_payload
        pagination = get_deduplication_register_results_request.request_body.pagination_request
        change_request_id = payload.change_request_id
        _logger.info(f"Getting deduplication register results for change_request_id: {change_request_id} through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        dedup_results_list, total_items = await g2p_register_service.get_deduplication_register_results(
            change_request_id, pagination.current_page, pagination.page_size, pagination.sort_by, pagination.filter_by
        )
        number_of_pages = (total_items + pagination.page_size - 1) // pagination.page_size if total_items > 0 else 0
        return dedup_results_list, total_items, number_of_pages

    async def get_deduplication_change_request_results(self, get_deduplication_change_request_results_request: GetDeduplicationChangerequestResultsRequest) -> tuple[list[DeduplicationChangerequestResultData], int, int]:
        """
        Get deduplication results for a change request against other change requests.
        """
        payload = get_deduplication_change_request_results_request.request_body.request_payload
        pagination = get_deduplication_change_request_results_request.request_body.pagination_request
        change_request_id = payload.change_request_id
        _logger.info(f"Getting deduplication change_request results for change_request_id: {change_request_id} through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        dedup_results_list, total_items = await g2p_register_service.get_deduplication_change_request_results(
            change_request_id, pagination.current_page, pagination.page_size, pagination.sort_by, pagination.filter_by
        )
        number_of_pages = (total_items + pagination.page_size - 1) // pagination.page_size if total_items > 0 else 0
        return dedup_results_list, total_items, number_of_pages

    async def get_register_section(self, get_register_section_request: GetRegisterSectionRequest) -> RegisterSectionData:
        """
        Get a single register section for a given register_id and section_id.
        """
        payload = get_register_section_request.request_body.request_payload
        register_id: str = payload.register_id
        section_id: str = payload.section_id
        _logger.info(f"Getting register section for register_id: {register_id}, section_id: {section_id} through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        register_section_data: RegisterSectionData = await g2p_register_service.get_register_section(register_id, section_id)
        return register_section_data

    async def get_section_records(
        self,
        get_section_records_request: GetSectionRecordsRequest
    ) -> list[RecordData]:
        """
        Get records from a related register that are linked to a subject record.
        Traverses the master-child hierarchy between registers.
        If subject_register_id == section_register_id, returns the subject record directly.
        """
        payload = get_section_records_request.request_body.request_payload
        subject_register_id: str = payload.subject_register_id
        subject_record_id: str = payload.subject_record_id
        section_register_id: str = payload.section_register_id
        _logger.info(
            f"Getting section records for subject_register_id: {subject_register_id}, "
            f"subject_record_id: {subject_record_id}, section_register_id: {section_register_id} "
            f"through controller service"
        )
        g2p_register_hierarchical_service = G2PRegisterHierarchicalService.get_component()
        section_records: list[RecordData] = await g2p_register_hierarchical_service.get_section_records(
            subject_register_id,
            subject_record_id,
            section_register_id
        )
        return section_records

    async def get_tab_records(
        self,
        get_register_tab_records_request: GetRegisterTabRecordsRequest,
        policy_mnemonics: list[str] | None = None,
    ) -> list[RegisterTabRecordData]:
        """
        Get all records for a tab, grouped by unique section_register_id.
        Multiple sections with the same section_register_id are deduplicated.
        """
        payload = get_register_tab_records_request.request_body.request_payload
        subject_register_id: str = payload.subject_register_id
        subject_record_id: str = payload.subject_record_id
        tab_id: str = payload.tab_id
        _logger.info(
            f"Getting register tab records for subject_register_id: {subject_register_id}, "
            f"subject_record_id: {subject_record_id}, tab_id: {tab_id} "
            f"through controller service"
        )
        g2p_register_hierarchical_service = G2PRegisterHierarchicalService.get_component()
        tab_records: list[RegisterTabRecordData] = await g2p_register_hierarchical_service.get_tab_records(
            subject_register_id, subject_record_id, tab_id, policy_mnemonics=policy_mnemonics
        )
        return tab_records

    async def get_register_summary_data(
        self,
        get_register_summary_data_request: GetRegisterSummaryDataRequest,
        policy_mnemonics: list[str] | None = None,
    ) -> list[RegisterSummaryData]:
        _logger.info("Fetching register summary data through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        register_summary_data_list: list[RegisterSummaryData] = await g2p_register_service.get_register_summary_data(
            policy_mnemonics=policy_mnemonics
        )
        return register_summary_data_list

    async def search_in_a_register(self, search_register_request: SearchRegisterRequest, policy_mnemonics: list[str] | None = None) -> tuple[list[SearchResultData], int, int]:
        payload = search_register_request.request_body.request_payload
        pagination = search_register_request.request_body.pagination_request
        register_id = payload.register_id

        _logger.info(f"Searching in register_id: {register_id} with search_text: {pagination.search_text}, page: {pagination.current_page}, page_size: {pagination.page_size} through controller service")
        g2p_register_service = G2PRegisterService.get_component()
        search_results_list, total_items = await g2p_register_service.search_in_a_register(
            register_id, pagination.search_text, pagination.current_page, pagination.page_size, pagination.sort_by, pagination.filter_by,
            policy_mnemonics=policy_mnemonics,
        )

        # Calculate number of pages
        number_of_pages = (total_items + pagination.page_size - 1) // pagination.page_size if total_items > 0 else 0

        return search_results_list, total_items, number_of_pages

    async def get_allowed_parents_for_child_section(
        self,
        get_allowed_parents_request: GetAllowedParentsForChildSectionRequest
    ) -> AllowedParentsData:
        """
        Get allowed parent records for a child section.
        """
        payload = get_allowed_parents_request.request_body.request_payload
        subject_register_id: str = payload.subject_register_id
        internal_record_id: str = payload.internal_record_id
        section_register_id: str = payload.section_register_id
        _logger.info(
            f"Getting allowed parents for child section: subject_register_id={subject_register_id}, "
            f"internal_record_id={internal_record_id}, section_register_id={section_register_id}"
        )
        g2p_register_hierarchical_service = G2PRegisterHierarchicalService.get_component()
        allowed_parents_data: AllowedParentsData = await g2p_register_hierarchical_service.get_allowed_parents_for_child_section(
            subject_register_id, internal_record_id, section_register_id
        )
        return allowed_parents_data

