import uuid

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel


class G2PRegistryConfiguration(BaseORMModel):
    """
    Stores global registry configuration settings.
    This includes registry-wide settings like name and logo.
    """
    __tablename__ = "g2p_registry_configuration"

    configuration_id: Mapped[str] = mapped_column(
        String, 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    registry_name: Mapped[str] = mapped_column(String, nullable=False)
    registry_logo: Mapped[str] = mapped_column(Text, nullable=True)  # BASE64 encoded image
    registry_favicon: Mapped[str] = mapped_column(Text, nullable=True)  # BASE64 encoded square icon
    registry_theme_id: Mapped[str] = mapped_column(String, nullable=True)
    registry_language_id: Mapped[str] = mapped_column(String, nullable=True)

