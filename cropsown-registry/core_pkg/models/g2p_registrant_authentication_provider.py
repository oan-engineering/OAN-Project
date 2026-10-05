import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from openg2p_fastapi_common.models import BaseORMModel


class G2PRegistrantAuthenticationProvider(BaseORMModel):
    __tablename__ = "g2p_registrant_authentication_providers"

    provider_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    register_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    provider_name: Mapped[str] = mapped_column(String, nullable=False)
    provider_description: Mapped[str] = mapped_column(String, nullable=True)

    adapter_name: Mapped[str] = mapped_column(String, nullable=False)

    # OIDC metadata / endpoints (can be overridden if metadata_url is absent)
    server_metadata_url: Mapped[str] = mapped_column(String, nullable=True)
    authorization_endpoint: Mapped[str] = mapped_column(String, nullable=True)
    token_endpoint: Mapped[str] = mapped_column(String, nullable=True)
    userinfo_endpoint: Mapped[str] = mapped_column(String, nullable=True)
    jwks_endpoint: Mapped[str] = mapped_column(String, nullable=True)
    introspection_endpoint: Mapped[str] = mapped_column(String, nullable=True)

    # Client credentials
    client_id: Mapped[str] = mapped_column(String, nullable=False)
    client_secret: Mapped[str] = mapped_column(String, nullable=True)
    client_private_key: Mapped[bytes | None] = mapped_column(LargeBinary(), nullable=True)
    token_endpoint_auth_method: Mapped[str] = mapped_column(
        String, nullable=False, default="client_secret_basic"
    )

    # Callback URL registered with IdP for this provider
    oauth_callback_url: Mapped[str] = mapped_column(String, nullable=False)

    # Optional: KeyManager integration for MOSIP e-Signet
    keymanager_sign_app_id: Mapped[str] = mapped_column(String, nullable=True)

    # Provider-specific config (realm, locale, extra params, scope overrides, etc.)
    provider_config: Mapped[dict] = mapped_column(JSONB, nullable=True)

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

