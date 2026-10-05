import uuid

from sqlalchemy import String, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel


class G2PRegisterSchema(BaseORMModel):
    """
    Stores schema configurations for each register.
    This includes deduplication fields, search result display fields, and filter configurations.
    """
    __tablename__ = "g2p_register_schemas"

    register_id: Mapped[str] = mapped_column(
        String,
        primary_key=True
    )

    # Deduplication schema configuration
    # JSON structure: [{"field_name": str, "match_type": str, "weight": float, "similarity_threshold": float}]
    deduplicate_schema: Mapped[JSON] = mapped_column(JSON, nullable=True)

    # Search result display schema configuration
    # JSON structure: [{"field_name": str, "display_label": str, "order": int}]
    search_result_schema: Mapped[JSON] = mapped_column(JSON, nullable=True)

    # Filter schema configuration
    # JSON structure to be defined based on filter requirements
    filter_schema: Mapped[JSON] = mapped_column(JSON, nullable=True)

