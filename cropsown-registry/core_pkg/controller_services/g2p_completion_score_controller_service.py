import logging

from openg2p_fastapi_common.service import BaseService

from ..services import G2PCompletionScoreService
from ..schemas import (
    GetIdealCompletionScoreForRegisterRequest,
    GetIdealCompletionScoreForSectionRequest,
    GetComputedCompletionScoreForSectionRequest,
    GetComputedCompletionScoreForRecordRequest,
    IdealRegisterScoreData,
    IdealSectionScoreData,
    SectionCompletionScoreData,
    RecordCompletionScoreData,
)

_logger = logging.getLogger("g2p-completion-score-controller-service")


class G2PCompletionScoreControllerService(BaseService):

    async def get_ideal_completion_score_for_register(
        self, request: GetIdealCompletionScoreForRegisterRequest
    ) -> IdealRegisterScoreData:
        payload = request.request_body.request_payload
        service = G2PCompletionScoreService.get_component()
        return await service.get_ideal_completion_score_for_register(payload.register_id)

    async def get_ideal_completion_score_for_section(
        self, request: GetIdealCompletionScoreForSectionRequest
    ) -> IdealSectionScoreData:
        payload = request.request_body.request_payload
        service = G2PCompletionScoreService.get_component()
        return await service.get_ideal_completion_score_for_section(payload.section_id)

    async def get_computed_completion_score_for_section(
        self, request: GetComputedCompletionScoreForSectionRequest
    ) -> SectionCompletionScoreData:
        payload = request.request_body.request_payload
        service = G2PCompletionScoreService.get_component()
        return await service.get_computed_completion_score_for_section(
            register_id=payload.register_id,
            internal_record_id=payload.internal_record_id,
            section_id=payload.section_id,
        )

    async def get_computed_completion_score_for_record(
        self, request: GetComputedCompletionScoreForRecordRequest
    ) -> RecordCompletionScoreData:
        payload = request.request_body.request_payload
        service = G2PCompletionScoreService.get_component()
        return await service.get_computed_completion_score_for_record(
            register_id=payload.register_id,
            internal_record_id=payload.internal_record_id,
        )
