import enum
import uuid

from sqlalchemy import Boolean, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from openg2p_fastapi_common.models import BaseORMModel


class RegistryThemeAttributeNameEnum(enum.Enum):
    primary_color_1 = "primary_color_1"
    primary_color_2 = "primary_color_2"
    secondary_color_1 = "secondary_color_1"
    secondary_color_2 = "secondary_color_2"
    secondary_color_3 = "secondary_color_3"
    neutral_color_1 = "neutral_color_1"
    neutral_color_2 = "neutral_color_2"
    font_family = "font_family"
    font_url = "font_url"
    dashboard_image = "dashboard_image"


class G2PRegistryTheme(BaseORMModel):
    __tablename__ = "registry_themes"

    theme_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    theme_mnemonic: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    is_factory_shipped: Mapped[bool] = mapped_column(Boolean, nullable=False)


class G2PRegistryThemeValue(BaseORMModel):
    __tablename__ = "registry_theme_values"

    theme_value_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    theme_id: Mapped[str] = mapped_column(
        String,
        nullable=False
    )
    attribute_name: Mapped[RegistryThemeAttributeNameEnum] = mapped_column(
        Enum(RegistryThemeAttributeNameEnum, name="registry_theme_attribute_name_enum"),
        nullable=False
    )
    attribute_value: Mapped[str] = mapped_column(Text, nullable=False)
