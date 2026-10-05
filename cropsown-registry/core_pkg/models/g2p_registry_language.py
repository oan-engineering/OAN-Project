import uuid

from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from openg2p_fastapi_common.models import BaseORMModel


class G2PRegistryLanguage(BaseORMModel):
    __tablename__ = "registry_languages"

    language_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    language_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        unique=True
    )
    language_label: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    language_flag_base64: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    core_translation: Mapped[dict] = mapped_column(
        JSON,
        nullable=True
    )
    domain_translation: Mapped[dict] = mapped_column(
        JSON,
        nullable=True
    )