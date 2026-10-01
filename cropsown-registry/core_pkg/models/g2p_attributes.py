import uuid
from sqlalchemy import Boolean, String, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from openg2p_fastapi_common.models import BaseORMModel


class G2PAttribute(BaseORMModel):
    __tablename__ = "g2p_attributes"

    attribute_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    attribute_code: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    attribute_display: Mapped[str] = mapped_column(String, nullable=False)
    is_hierarchical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class G2PAttributeValue(BaseORMModel):
    __tablename__ = "g2p_attribute_values"

    value_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    attribute_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    value_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    value_display: Mapped[str] = mapped_column(String, nullable=False)
    parent_value_id: Mapped[str] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

