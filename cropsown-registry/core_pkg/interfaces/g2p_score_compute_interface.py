from abc import ABC, abstractmethod
from typing import Any


class G2PScoreComputeInterface(ABC):
    """
    Domain-specific score compute contract.
    Implementations live in `openg2p_registry_extensions.score_compute.services`.
    """

    @abstractmethod
    async def compute_score(
        self,
        link_internal_record_id: str,
        contributing_attribute_config: list[dict[str, Any]],
        contributing_attribute_values: dict[str, Any],
    ) -> float:
        """
        Compute and return the score for the given record.

        Args:
            link_internal_record_id: Registrant / domain record internal ID.
            contributing_attribute_config: Metadata from ``g2p_register_score_contributing_attributes``.
                Each row: attribute_name, attribute_computation_required,
                attribute_computation_value (lookup map), attribute_weightage.
            contributing_attribute_values: Field snapshots from the queue at enqueue time,
                keyed by attribute_name.
        """
        pass
