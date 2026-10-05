import importlib

from openg2p_fastapi_common.service import BaseService

from .g2p_score_compute_interface import G2PScoreComputeInterface


class G2PScoreComputeFactory(BaseService):
    """
    Dynamically loads the compute service for the given score_type.

    Naming convention:
        score_type "PMT_SCORE"  →  G2PScoreComputeServicePmtScore
        score_type "FSF_SCORE"  →  G2PScoreComputeServiceFsfScore

    The implementation class must exist in:
        openg2p_registry_extensions.score_compute.services
    """

    def get_compute_service(self, score_type: str) -> G2PScoreComputeInterface:
        class_name = self._score_type_to_class_name(score_type)
        module = importlib.import_module(
            "openg2p_registry_extensions.score_compute.services"
        )
        compute_class = getattr(module, class_name)
        return compute_class()

    @staticmethod
    def _score_type_to_class_name(score_type: str) -> str:
        # "PMT_SCORE" -> "G2PScoreComputeServicePmtScore"
        title_case = score_type.replace("_", " ").title().replace(" ", "")
        return f"G2PScoreComputeService{title_case}"

