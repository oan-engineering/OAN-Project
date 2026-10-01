import uuid

from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel


class G2PRegisterScoreDefinition(BaseORMModel):
    """
    Header row for score metadata: which score types exist for a register mnemonic.
    Per-attribute rules live in `g2p_register_score_contributing_attributes`.
    """

    __tablename__ = "g2p_register_score_definitions"

    score_definition_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    register_mnemonic: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Used as factory lookup key in extensions (e.g. "PMT_SCORE")
    score_type: Mapped[str] = mapped_column(String, nullable=False, index=True)

    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index(
            "ix_g2p_register_score_def_reg_mnem_score_type_unique",
            "register_mnemonic",
            "score_type",
            unique=True,
        ),
    )
