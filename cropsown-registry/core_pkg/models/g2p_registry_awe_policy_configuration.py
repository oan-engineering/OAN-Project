import uuid

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from openg2p_fastapi_common.models import BaseORMModel

from .enum import AwePolicyScopeEnum


class G2PRegistryAwePolicyConfiguration(BaseORMModel):
    """
    Staff-configured AWE policy bindings (register / intake form / section scope).

    - policy_scope: REGISTER / INTAKE_FORM / SECTION (AwePolicyScopeEnum), stored as VARCHAR.
    - intake_form_id / section_id: optional depending on scope.
    - context_field_names: list[str] as JSON.
    """

    __tablename__ = "g2p_registry_awe_policy_configurations"

    awe_policy_config_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    policy_scope: Mapped[AwePolicyScopeEnum] = mapped_column(String, nullable=False, index=True)
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    intake_form_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    section_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    policy_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    policy_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    context_field_names: Mapped[list | None] = mapped_column(JSON, nullable=True)
