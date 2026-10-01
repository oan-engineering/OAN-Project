import uuid

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from openg2p_fastapi_common.models import BaseORMModel


class G2PRegistryImportFileConfiguration(BaseORMModel):
    __tablename__ = "g2p_registry_import_file_configurations"

    import_file_configuration_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    form_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    data_model_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    import_file_template_mnemonic: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )
    import_file_template_description: Mapped[str] = mapped_column(Text, nullable=False)

