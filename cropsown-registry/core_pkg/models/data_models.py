import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel

from .enum import ProcessStatusEnum

class DataModel(BaseORMModel):
    __tablename__ = "data_models"

    data_model_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    data_model_mnemonic: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    pattern_for_data_model: Mapped[str] = mapped_column(String, nullable=False)
    # document_id of the response template in g2p_registry_documents (TEMPLATES bucket)
    response_template_document_id: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
