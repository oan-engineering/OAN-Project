from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict

from openg2p_fastapi_common.models import BaseORMModel

class G2PRegistryVcConfiguration(BaseORMModel):
    __tablename__ = "g2p_registry_vc_configurations"

    vc_config_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    intake_form_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    data_model_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    vc_mnemonic: Mapped[str] = mapped_column(String, nullable=False, unique=False, index=True)
    descriptor_schema: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False
    )
