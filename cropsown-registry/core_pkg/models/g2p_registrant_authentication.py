import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from openg2p_fastapi_common.models import BaseORMModel


class AuthenticationStatusEnum(str, enum.Enum):
    pending = "PENDING"
    success = "SUCCESS"
    failure = "FAILURE"
    expired = "EXPIRED"


class G2PRegistrantAuthentication(BaseORMModel):
    __tablename__ = "g2p_registrant_authentications"

    authentication_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    internal_record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    provider_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    initiated_by_staff_id: Mapped[str] = mapped_column(String, nullable=False)
    initiated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    status: Mapped[str] = mapped_column(
        String, nullable=False, default=AuthenticationStatusEnum.pending.value, index=True
    )

    # Successful authentication details
    user_claims: Mapped[str] = mapped_column(String, nullable=True)  # encrypted JSON (or plaintext JSON)
    authentication_method: Mapped[str] = mapped_column(String, nullable=True)
    claim_verifications: Mapped[dict] = mapped_column(JSONB, nullable=True)
    token_hash: Mapped[str] = mapped_column(String, nullable=True)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    expiry_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)

    # Failure details
    failure_reason: Mapped[str] = mapped_column(String, nullable=True)

    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index(
            "idx_registrant_auth_register_internal",
            "register_id",
            "internal_record_id",
        ),
        Index(
            "idx_registrant_auth_internal_status",
            "internal_record_id",
            "status",
        ),
        Index("idx_registrant_auth_expiry_at", "expiry_at"),
    )

