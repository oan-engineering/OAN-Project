import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from cryptography.fernet import Fernet

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from openg2p_fastapi_common.service import BaseService
from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.utils.crypto import KeymanagerCryptoHelper

from iam_core.models import LoginProvider
from iam_core.schemas import TokenEndpointAuthMethod
from iam_core.schemas import AuthTransaction
from iam_core.services.auth_transaction_store import AuthTransactionStore
from iam_core.services.redis_auth_transaction_store import RedisAuthTransactionStore
from iam_core.user_auth.adapters import AdapterFactory

from ..config import Settings
from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..models import (
    AuthenticationStatusEnum,
    G2PRegistrantAuthentication,
    G2PRegistrantAuthenticationProvider,
    G2PRegister,
    G2PRegisterDefinition,
)

_logger = logging.getLogger("g2p-registrant-auth-service")
_config = Settings.get_config()


class _ClaimsCrypto:
    def __init__(self, fernet_key: str | None):
        self._fernet = None
        if fernet_key:
            try:
                self._fernet = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
            except Exception as e:
                _logger.warning("Registrant claims encryption disabled (invalid key). %s", repr(e))
                self._fernet = None

    def encrypt_json(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if not self._fernet:
            return raw.decode("utf-8")
        return self._fernet.encrypt(raw).decode("utf-8")


class G2PRegistrantAuthenticationService(BaseService):
    def __init__(self):
        super().__init__()
        self._engine = dbengine.get()
        self._auth_tx_store = self._init_auth_transaction_store()
        self._adapters = AdapterFactory.get_component()
        self._crypto = _ClaimsCrypto(_config.registrant_auth_claims_encryption_key)

    @staticmethod
    async def _mark_failure(session, auth: G2PRegistrantAuthentication, reason: str) -> G2PRegistrantAuthentication:
        auth.status = AuthenticationStatusEnum.failure.value
        auth.failure_reason = reason
        auth.completed_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        session.add(auth)
        await session.commit()
        await session.refresh(auth)
        return auth

    @staticmethod
    def _init_auth_transaction_store() -> AuthTransactionStore | RedisAuthTransactionStore:
        backend = (_config.registrant_auth_session_store_backend or "memory").strip().lower()
        ttl = int(_config.registrant_auth_session_ttl_seconds or 300)
        if backend == "redis":
            redis_url = _config.registrant_auth_redis_url
            if not redis_url:
                _logger.warning("registrant_auth_redis_url missing; falling back to memory store.")
                return AuthTransactionStore(ttl_seconds=ttl)
            return RedisAuthTransactionStore(ttl_seconds=ttl, redis_url=redis_url)
        return AuthTransactionStore(ttl_seconds=ttl)

    async def get_available_providers(
        self,
        register_id: str,
    ) -> list[G2PRegistrantAuthenticationProvider]:
        session_maker = async_sessionmaker(self._engine, expire_on_commit=False)
        async with session_maker() as session:
            rows = await session.execute(
                select(G2PRegistrantAuthenticationProvider)
                .where(
                    G2PRegistrantAuthenticationProvider.register_id == register_id,
                    G2PRegistrantAuthenticationProvider.is_active.is_(True),
                )
                .order_by(G2PRegistrantAuthenticationProvider.display_order.asc())
            )
            return list(rows.scalars().all())

    async def get_provider(
        self,
        provider_id: str,
    ) -> G2PRegistrantAuthenticationProvider:
        session_maker = async_sessionmaker(self._engine, expire_on_commit=False)
        async with session_maker() as session:
            provider = await session.get(G2PRegistrantAuthenticationProvider, provider_id)
            if not provider:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                    message="Authentication provider not found.",
                )
            return provider

    async def start_authentication(
        self,
        *,
        register_id: str,
        internal_record_id: str,
        provider_id: str,
        initiated_by_staff_id: str,
    ) -> tuple[str, str, str]:
        session_maker = async_sessionmaker(self._engine, expire_on_commit=False)
        async with session_maker() as session:
            register_definition = await session.get(G2PRegisterDefinition, register_id)
            if not register_definition:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.REGISTER_NOT_FOUND.value[1],
                    message=G2PRegistryErrorCodes.REGISTER_NOT_FOUND.value[0],
                )
            if not getattr(register_definition, "requires_registrant_authentication", False):
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.REGISTRANT_AUTH_NOT_REQUIRED_FOR_REGISTER.value[1],
                    message="Registrant authentication is not enabled for this register.",
                )

            provider = await session.get(G2PRegistrantAuthenticationProvider, provider_id)
            if not provider:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.REGISTRANT_AUTH_PROVIDER_NOT_FOUND.value[1],
                    message="Authentication provider not found.",
                )
            if not provider.is_active:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.REGISTRANT_AUTH_PROVIDER_INACTIVE.value[1],
                    message="Authentication provider is inactive.",
                )

            auth = G2PRegistrantAuthentication(
                register_id=register_id,
                internal_record_id=internal_record_id,
                provider_id=provider_id,
                initiated_by_staff_id=initiated_by_staff_id,
                status=AuthenticationStatusEnum.pending.value,
            )
            session.add(auth)
            await session.commit()
            await session.refresh(auth)

            # Get foundational_id from register record
            try:
                # Get the implementation class for this register (similar to G2PRegisterService)
                if register_definition:
                    import importlib, os
                    ext_mod = os.environ.get("REGISTRY_EXTENSION_MODULE", "openg2p_registry_extensions")
                    module = importlib.import_module(f"{ext_mod}.register_domain.models")
                    register_class_prefix = "G2PRegister"
                    implementation_class_name = f"{register_class_prefix}{register_definition.register_mnemonic}"
                    implementation_class = getattr(module, implementation_class_name)
                    
                    # Fetch the record by internal_record_id
                    register_record = (
                        await session.execute(
                            select(implementation_class).where(
                                implementation_class.internal_record_id == internal_record_id
                            )
                        )
                    ).scalar()
                    
                    foundational_id = register_record.foundational_id if register_record and hasattr(register_record, 'foundational_id') and register_record.foundational_id else ""
                else:
                    foundational_id = ""
            except (AttributeError, ModuleNotFoundError):
                # Fallback if we can't determine the implementation class
                foundational_id = ""

        login_provider = self._provider_to_login_provider(provider)
        adapter = self._adapters.resolve_for_provider(login_provider)
        auth_tx: AuthTransaction = self._auth_tx_store.create(
            login_provider_id=login_provider.id,
            redirect_uri="/",
            server_metadata=None,
            context={
                "authentication_id": auth.authentication_id,
                "provider_id": provider_id,
                "register_id": register_id,
                "internal_record_id": internal_record_id,
                "foundational_id": foundational_id,
            },
        )
        authorization_url, _ = await adapter.build_authorize_redirect(
            login_provider=login_provider,
            state=auth_tx.state,
            nonce=auth_tx.nonce,
            code_verifier=auth_tx.code_verifier,
        )
        return auth_tx.state, authorization_url, provider.provider_name

    async def complete_authentication(
        self,
        *,
        state: str,
        authorization_code: str,
    ) -> G2PRegistrantAuthentication:
        auth_tx: AuthTransaction | None = self._auth_tx_store.get_and_pop(state)
        if not auth_tx:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTRANT_AUTH_SESSION_INVALID_OR_EXPIRED.value[1],
                message="Invalid or expired authentication session.",
            )
        ctx = auth_tx.context or {}
        auth_id = ctx.get("authentication_id")
        foundational_id = str(ctx.get("foundational_id") or "")

        session_maker = async_sessionmaker(self._engine, expire_on_commit=False)
        async with session_maker() as session:
            auth = await session.get(G2PRegistrantAuthentication, auth_id)
            if not auth:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.REGISTRANT_AUTH_RECORD_NOT_FOUND.value[1],
                    message="Authentication record not found.",
                )

            provider = await session.get(G2PRegistrantAuthenticationProvider, auth.provider_id)
            if not provider:
                auth.status = AuthenticationStatusEnum.failure.value
                auth.failure_reason = "Provider not found."
                auth.completed_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)
                session.add(auth)
                await session.commit()
                return auth

            try:
                login_provider = self._provider_to_login_provider(provider)
                adapter = self._adapters.resolve_for_provider(login_provider)

                keymanager_helper = None
                if (
                    login_provider.token_endpoint_auth_method
                    == TokenEndpointAuthMethod.private_key_jwt_keymanager
                ):
                    keymanager_helper = KeymanagerCryptoHelper().get_component()

                # Use the standard adapter method which already supports private_key_jwt
                token_response = await adapter.exchange_code_for_token(
                    login_provider=login_provider,
                    code=authorization_code,
                    code_verifier=auth_tx.code_verifier,
                    keymanager_helper=keymanager_helper,
                    km_app_id=provider.keymanager_sign_app_id,
                )

                await adapter.validate_callback_id_token(
                    login_provider=login_provider,
                    token_response=token_response,
                    nonce=auth_tx.nonce,
                )

                id_token = token_response.get("id_token")
                access_token = token_response.get("access_token")
                
                if not id_token:
                    return await self._mark_failure(session, auth, "Missing id_token in token response.")

                claims = await adapter.oidc_client.decode_jwt(
                    login_provider=login_provider,
                    token=id_token,
                    nonce=auth_tx.nonce,
                    access_token=access_token,
                )

                claims = await adapter.enrich_claims_from_userinfo(
                    claims,
                    login_provider=login_provider,
                    access_token=access_token,
                )
                claims = adapter.normalize_claims(claims, login_provider=login_provider)
                adapter.validate_claims(claims, login_provider=login_provider)

                token_subject = adapter.registrant_subject(claims, login_provider=login_provider)
                if not foundational_id:
                    return await self._mark_failure(
                        session,
                        auth,
                        "Registrant record does not have a foundational_id; cannot verify authentication.",
                    )
                if not token_subject:
                    return await self._mark_failure(
                        session,
                        auth,
                        "Token subject is missing; cannot verify against registrant record.",
                    )
                if token_subject.strip() != foundational_id.strip():
                    return await self._mark_failure(
                        session,
                        auth,
                        f"Token subject ({token_subject}) does not match registrant record ({foundational_id}).",
                    )

                token_hash = hashlib.sha256(id_token.encode("utf-8")).hexdigest()

                register_definition = await session.get(G2PRegisterDefinition, auth.register_id)
                validity_days = (
                    register_definition.registrant_authentication_validity_days
                    if register_definition
                    else None
                )
                expiry_at = datetime.now(tz=timezone.utc) + timedelta(days=int(validity_days))

                auth.status = AuthenticationStatusEnum.success.value
                auth.user_claims = self._crypto.encrypt_json(claims)
                auth.authentication_method = adapter.get_authentication_method(
                    claims, login_provider=login_provider
                )
                auth.claim_verifications = adapter.get_claim_verifications(
                    claims, login_provider=login_provider
                )
                auth.token_hash = token_hash

                expires_in = token_response.get("expires_in")
                if isinstance(expires_in, int):
                    auth.token_expires_at = (datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in)).replace(
                        tzinfo=None
                    )
                auth.expiry_at = expiry_at.replace(tzinfo=None)
                auth.completed_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)

                session.add(auth)
                await session.commit()
                
                # Update register record if it inherits from G2PRegisterAuthentication
                try:
                    register_definition = await session.get(G2PRegisterDefinition, auth.register_id)
                    if register_definition:
                        import importlib, os
                        ext_mod = os.environ.get("REGISTRY_EXTENSION_MODULE", "openg2p_registry_extensions")
                        module = importlib.import_module(f"{ext_mod}.register_domain.models")
                        implementation_class_name = f"G2PRegister{register_definition.register_mnemonic}"
                        implementation_class = getattr(module, implementation_class_name)
                        
                        # Check if the register model inherits from G2PRegisterAuthentication
                        from ..models import G2PRegisterAuthentication
                        if issubclass(implementation_class, G2PRegisterAuthentication):
                            register_record = (
                                await session.execute(
                                    select(implementation_class).where(
                                        implementation_class.internal_record_id == auth.internal_record_id
                                    )
                                )
                            ).scalar()
                            
                            if register_record:
                                register_record.last_authentication_id = auth.authentication_id
                                register_record.last_authenticated_at = auth.completed_at
                                register_record.last_authentication_status = auth.status
                                register_record.authentication_expiry_at = auth.expiry_at
                                register_record.authentication_expiry_notified = False
                                register_record.authentication_token = claims.get("sub")
                                session.add(register_record)
                                await session.commit()
                except (AttributeError, ModuleNotFoundError, TypeError) as e:
                    _logger.warning(f"Could not update register record: {e}")
                except Exception as e:
                    _logger.error(f"Error updating register record: {e}")
                
                await session.refresh(auth)
                return auth
            except Exception as e:
                _logger.exception("Registrant auth completion failed.")
                auth.status = AuthenticationStatusEnum.failure.value
                auth.failure_reason = str(e)
                auth.completed_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)
                session.add(auth)
                await session.commit()
                return auth

    async def get_authentication_status(
        self,
        *,
        internal_record_id: str,
    ) -> G2PRegistrantAuthentication | None:
        session_maker = async_sessionmaker(self._engine, expire_on_commit=False)
        async with session_maker() as session:
            row = await session.execute(
                select(G2PRegistrantAuthentication)
                .where(G2PRegistrantAuthentication.internal_record_id == internal_record_id)
                .order_by(desc(G2PRegistrantAuthentication.initiated_at))
                .limit(1)
            )
            return row.scalars().one_or_none()

    async def get_authentication_history(
        self,
        *,
        internal_record_id: str,
        limit: int = 50,
    ) -> list[G2PRegistrantAuthentication]:
        session_maker = async_sessionmaker(self._engine, expire_on_commit=False)
        async with session_maker() as session:
            row = await session.execute(
                select(G2PRegistrantAuthentication)
                .where(G2PRegistrantAuthentication.internal_record_id == internal_record_id)
                .order_by(desc(G2PRegistrantAuthentication.initiated_at))
                .limit(limit)
            )
            return list(row.scalars().all())

    async def is_authentication_valid(
        self,
        *,
        internal_record_id: str,
    ) -> bool:
        auth = await self.get_authentication_status(internal_record_id=internal_record_id)
        if not auth or auth.status != AuthenticationStatusEnum.success.value:
            return False
        if not auth.expiry_at:
            return False
        return auth.expiry_at > datetime.now(tz=timezone.utc).replace(tzinfo=None)

    async def find_expiring_authentications(
        self,
        *,
        days_before: int = 30,
        limit: int = 500,
    ) -> list[tuple[str, str, datetime]]:
        """
        Find authentications expiring within N days.

        Returns: [(register_id, internal_record_id, expiry_at), ...]
        """
        now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        window_end = now + timedelta(days=int(days_before))

        session_maker = async_sessionmaker(self._engine, expire_on_commit=False)
        async with session_maker() as session:
            rows = await session.execute(
                select(
                    G2PRegistrantAuthentication.register_id,
                    G2PRegistrantAuthentication.internal_record_id,
                    G2PRegistrantAuthentication.expiry_at,
                )
                .where(
                    G2PRegistrantAuthentication.status == AuthenticationStatusEnum.success.value,
                    G2PRegistrantAuthentication.expiry_at.is_not(None),
                    G2PRegistrantAuthentication.expiry_at <= window_end,
                    G2PRegistrantAuthentication.expiry_at > now,
                )
                .order_by(G2PRegistrantAuthentication.expiry_at.asc())
                .limit(limit)
            )
            return [(r[0], r[1], r[2]) for r in rows.all() if r[2] is not None]

    @staticmethod
    def _provider_to_login_provider(provider: G2PRegistrantAuthenticationProvider) -> LoginProvider:
        extra = provider.provider_config or {}
        scope = extra.get("scope") or "openid profile"
        extra_authorize_params = extra.get("extra_authorize_params")
        if isinstance(extra_authorize_params, dict):
            extra_authorize_params = json.dumps(extra_authorize_params)
        elif extra_authorize_params is not None and not isinstance(extra_authorize_params, str):
            extra_authorize_params = None

        issuer = extra.get("issuer")
        audiences = extra.get("audiences")
        if isinstance(audiences, list):
            audiences_str = ",".join([str(a) for a in audiences])
        else:
            audiences_str = None

        method_raw = (provider.token_endpoint_auth_method or "client_secret_basic").strip()
        # Use the actual method for private_key_jwt, don't map to client_secret_post
        method_enum = TokenEndpointAuthMethod(method_raw)

        if not provider.oauth_callback_url:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTRANT_AUTH_PROVIDER_MISCONFIGURED.value[1],
                message="Authentication provider callback URL is not configured.",
            )

        return LoginProvider(
            id=provider.provider_id,
            provider_name=provider.provider_name,
            adapter_name=provider.adapter_name,
            server_metadata_url=provider.server_metadata_url,
            authorization_endpoint=provider.authorization_endpoint,
            token_endpoint=provider.token_endpoint,
            userinfo_endpoint=provider.userinfo_endpoint,
            jwks_uri=provider.jwks_endpoint,
            client_id=provider.client_id,
            client_secret=provider.client_secret,
            client_private_key=provider.client_private_key,
            oauth_callback_url=provider.oauth_callback_url,
            scope=scope,
            enable_pkce=True,
            token_endpoint_auth_method=method_enum,
            issuer=issuer,
            audiences=audiences_str,
            extra_authorize_params=extra_authorize_params,
        )

    
