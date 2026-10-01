import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from openg2p_fastapi_common.models import BaseORMModel


class AuthenticationStatusEnum(str, enum.Enum):
    pending = "PENDING"
    success = "SUCCESS"
    failure = "FAILURE"
    expired = "EXPIRED"


class G2PRegisterAuthentication(BaseORMModel):
    """
    Optional mixin for domain registers that want denormalized registrant-auth fields.
    Domain models can inherit this alongside `G2PRegister`.
    """

    __abstract__ = True

    last_authentication_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    last_authenticated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_authentication_status: Mapped[str] = mapped_column(String, nullable=True, default=AuthenticationStatusEnum.pending.value)

    authentication_expiry_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)
    authentication_expiry_notified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    authentication_token: Mapped[str] = mapped_column(String, nullable=True)

