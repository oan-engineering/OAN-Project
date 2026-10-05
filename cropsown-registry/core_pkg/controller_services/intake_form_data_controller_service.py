import logging
import math

from openg2p_fastapi_common.service import BaseService

from ..schemas import (
    ApproveRejectSubmissionRequest,
    DeleteIntakeFormSubmissionRequest,
    FinalizeSubmissionRequest,
    GetSubmissionRequest,
    GetIntakeFormTabRecordsRequest,
    GetDeduplicationIntakeFormRegisterResultsRequest,
    GetDeduplicationIntakeFormIntakeFormResultsRequest,
    DeduplicationIntakeFormRegisterResultData,
    DeduplicationIntakeFormIntakeFormResultData,
    SaveIntakeFormSubmissionRequest,
    SearchInSubmissionRequest,
    SectionPayloadResponseItem,
    SubmissionResponsePayload,
    GetIntakeFormSubmissionsSummaryRequest,
    IntakeFormSubmissionsSummaryData
)
from ..services import G2PIntakeFormDataService, G2PIntakeFormDataService

_logger = logging.getLogger("g2p-intake-form-data-controller-service")


class G2PIntakeFormDataControllerService(BaseService):
    async def save_intake_form_submission(
        self,
        request: SaveIntakeFormSubmissionRequest,
    ) -> SubmissionResponsePayload:
        payload = request.request_body.request_payload
        return await G2PIntakeFormDataService.get_component().save_intake_form_submission(
            submission_id=payload.submission_id,
            section_id=payload.section_id,
            section_payload=payload.section_payload,
            section_register_id=payload.section_register_id,
            form_id=payload.form_id,
            register_id=payload.register_id,
            created_by=payload.created_by or "Unknown",
            documents=payload.documents,
        )

    async def finalize_intake_form_submission(
        self,
        request: FinalizeSubmissionRequest,
        *,
        bearer_token: str | None = None,
        requester_sub: str | None = None,
    ) -> SubmissionResponsePayload:
        payload = request.request_body.request_payload
        return await G2PIntakeFormDataService.get_component().finalize_submission(
            payload.submission_id,
            bearer_token=bearer_token,
            requester_sub=requester_sub,
        )

    async def delete_intake_form_submission(
        self,
        request: DeleteIntakeFormSubmissionRequest,
    ) -> SubmissionResponsePayload:
        payload = request.request_body.request_payload
        return await G2PIntakeFormDataService.get_component().delete_submission(payload.submission_id)

    async def approve_intake_form_submission(
        self,
        request: ApproveRejectSubmissionRequest,
    ) -> SubmissionResponsePayload:
        payload = request.request_body.request_payload
        return await G2PIntakeFormDataService.get_component().approve_submission(
            payload.submission_id,
            payload.approved_by or "Unknown",
        )

    async def reject_intake_form_submission(
        self,
        request: ApproveRejectSubmissionRequest,
    ) -> SubmissionResponsePayload:
        payload = request.request_body.request_payload
        return await G2PIntakeFormDataService.get_component().reject_submission(
            payload.submission_id,
            payload.approved_by or "Unknown",
        )

    async def get_intake_form_submission(
        self,
        request: GetSubmissionRequest,
        policy_mnemonics: list[str] | None = None,
    ) -> SubmissionResponsePayload:
        payload = request.request_body.request_payload
        return await G2PIntakeFormDataService.get_component().get_intake_form_submission(
            payload.submission_id,
            policy_mnemonics=policy_mnemonics,
        )

    async def get_tab_records(
        self,
        request: GetIntakeFormTabRecordsRequest,
        policy_mnemonics: list[str] | None = None,
    ) -> list[SectionPayloadResponseItem]:
        payload = request.request_body.request_payload
        return await G2PIntakeFormDataService.get_component().get_tab_records(
            payload.submission_id,
            payload.tab_id,
            policy_mnemonics=policy_mnemonics,
        )

    async def search_in_intake_form_submissions(
        self,
        request: SearchInSubmissionRequest,
        policy_mnemonics: list[str] | None = None,
    ):
        payload = request.request_body.request_payload
        pagination = request.request_body.pagination_request
        records, total_items = await G2PIntakeFormDataService.get_component().search_submissions(
            payload.register_id,
            pagination.search_text if pagination else None,
            pagination.current_page if pagination else 1,
            pagination.page_size if pagination else 10,
            pagination.sort_by if pagination else None,
            pagination.filter_by if pagination else None,
            policy_mnemonics=policy_mnemonics,
        )
        page_size = pagination.page_size if pagination else 10
        return records, total_items, math.ceil(total_items / page_size) if page_size else 0

    async def get_deduplication_intake_form_register_results(
        self,
        request: GetDeduplicationIntakeFormRegisterResultsRequest,
    ) -> list[DeduplicationIntakeFormRegisterResultData]:
        payload = request.request_body.request_payload
        return await G2PIntakeFormDataService.get_component().get_deduplication_intake_form_register_results(
            submission_id=payload.submission_id,
        )

    async def get_deduplication_intake_form_intake_form_results(
        self,
        request: GetDeduplicationIntakeFormIntakeFormResultsRequest,
    ) -> list[DeduplicationIntakeFormIntakeFormResultData]:
        payload = request.request_body.request_payload
        return await G2PIntakeFormDataService.get_component().get_deduplication_intake_form_intake_form_results(
            submission_id=payload.submission_id,
        )
    
    async def get_intake_form_submissions_summary(
        self,
        get_intake_form_submissions_summary_request: GetIntakeFormSubmissionsSummaryRequest,
        policy_mnemonics: list[str] | None = None,
    ) -> IntakeFormSubmissionsSummaryData:
        _ = get_intake_form_submissions_summary_request
        _logger.info("Getting intake form submissions summary through controller service")
        g2p_intake_form_data_service = G2PIntakeFormDataService.get_component()
        return await g2p_intake_form_data_service.get_intake_form_submissions_summary(
            policy_mnemonics=policy_mnemonics,
        )
