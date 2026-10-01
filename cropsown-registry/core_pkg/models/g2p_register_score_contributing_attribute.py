import uuid

from sqlalchemy import JSON, Boolean, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel


class G2PRegisterScoreContributingAttribute(BaseORMModel):
    """
    Contributing attribute metadata for a score type (weights, lookups, computation flags).
    Scoped by register mnemonic + score_type (aligned with score definition rows).
    """

    __tablename__ = "g2p_register_score_contributing_attributes"

    contributing_attribute_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    register_mnemonic: Mapped[str] = mapped_column(String, nullable=False, index=True)
    score_type: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Column name of the register attribute that contributes to the score (e.g. headship_type)
    attribute_name: Mapped[str] = mapped_column(String, nullable=False)

    attribute_computation_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # e.g. {"CHILD_HEADED": 0.2, "ELDER_HEADED": 0.4}
    attribute_computation_value: Mapped[JSON] = mapped_column(JSON, nullable=True)

    attribute_weightage: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        Index(
            "ix_g2p_reg_score_contrib_reg_mnem_score_attr_unique",
            "register_mnemonic",
            "score_type",
            "attribute_name",
            unique=True,
        ),
    )
