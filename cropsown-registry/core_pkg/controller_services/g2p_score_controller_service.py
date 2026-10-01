import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService

from ..schemas import (
    GetScoreHistoryRequest,
    GetScoreHistoryResponsePayload,
    GetScoresRequest,
    GetScoresResponsePayload,
)
from ..errors import G2PRegistryErrorCodes, G2PRegistryException

from ..services import G2PScoreComputeService

_logger = logging.getLogger("g2p-score-controller-service")


class G2PScoreControllerService(BaseService):
    async def get_scores_for_record(
        self, get_scores_request: GetScoresRequest
    ) -> GetScoresResponsePayload:
        _logger.info("Fetching scores for record through controller service")
        scores_request_payload = get_scores_request.request_body.request_payload
        link_internal_record_id: str = scores_request_payload.link_internal_record_id

        try:
            g2p_score_compute_service = G2PScoreComputeService.get_component()
            session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
            async with session_maker() as session:
                scores_data = await g2p_score_compute_service.get_scores_for_record(
                    link_internal_record_id=link_internal_record_id, session=session
                )
        except Exception as e:
            _logger.error(f"Error fetching scores for record {link_internal_record_id}: {str(e)}")
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SCORE_COMPUTE_SERVICE_ERROR.value[1],
                message=f"Failed to fetch scores for record: {str(e)}",
            )

        return GetScoresResponsePayload(scores=scores_data)

    async def get_score_history(
        self,
        get_score_history_request: GetScoreHistoryRequest,
    ) -> GetScoreHistoryResponsePayload:
        _logger.info("Getting score history through controller service")
        score_history_request_payload = get_score_history_request.request_body.request_payload
        link_internal_record_id: str = score_history_request_payload.link_internal_record_id
        score_type: str = score_history_request_payload.score_type

        g2p_score_compute_service = G2PScoreComputeService.get_component()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            score_history_data = await g2p_score_compute_service.get_score_history_for_record(
                link_internal_record_id=link_internal_record_id,
                score_type=score_type,
                session=session,
            )

        return GetScoreHistoryResponsePayload(history=score_history_data)
