import uuid

from sqlalchemy import Index, JSON, String, text
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel

from .enum import PolicyTargetEnum


class G2PRegistryDataPolicy(BaseORMModel):
    """
    Data access policy scoped to a governed resource type.
    policy_mnemonic is published to Keycloak as a client role DP_<policy_mnemonic>.
    The same mnemonic may appear on multiple rows (one per policy_target).
    register_id is required for REGISTER_RECORD policies; null for GEO/ATTRIBUTE.
    """

    __tablename__ = "g2p_registry_data_policies"

    policy_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    policy_mnemonic: Mapped[str] = mapped_column(String, nullable=False, index=True)
    policy_description: Mapped[str | None] = mapped_column(String, nullable=True)
    register_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    policy_target: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=PolicyTargetEnum.REGISTER_RECORD.value,
        index=True,
    )
    policy_type: Mapped[str] = mapped_column(String, nullable=False)
    policy_filter_expression: Mapped[JSON] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index(
            "ix_g2p_registry_data_policies_reg_mnemonic_target_unique",
            "register_id",
            "policy_mnemonic",
            "policy_target",
            unique=True,
            postgresql_where=text("register_id IS NOT NULL"),
        ),
        Index(
            "ix_g2p_registry_data_policies_mnemonic_target_unique",
            "policy_mnemonic",
            "policy_target",
            unique=True,
            postgresql_where=text("register_id IS NULL"),
        ),
    )
