"""
Sync Registry data policies to Keycloak as DP_<policy_mnemonic> client roles.

See: https://docs.openg2p.org/products/registry/registry/design/record-level-permissions
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from ..config import Settings
from ..errors.exceptions import G2PRegistryException
from ..errors.codes import G2PRegistryErrorCodes

_logger = logging.getLogger("g2p-data-policy-keycloak")

DATA_POLICY_ROLE_PREFIX = "DP_"

class DataPolicyKeycloakHelper:
    """Keycloak Admin REST client for data-policy client roles."""

    def __init__(self) -> None:
        self._config = Settings.get_config(strict=False)
        self._token: str | None = None
        self._token_expires_at: float = 0

    @property
    def is_configured(self) -> bool:
        if not self._config.keycloak_data_policy_role_sync_enabled:
            return False
        return bool(
            self._config.keycloak_admin_url
            and self._config.keycloak_admin_client_id
            and self._config.keycloak_admin_client_secret
            and self._config.keycloak_client_id
        )

    def _registry_client_id(self) -> str:
        client_id = self._config.keycloak_client_id
        if not client_id:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.KEYCLOAK_SYNC_ERROR,
                message="keycloak_client_id is not configured",
            )
        return client_id

    def _admin_base_url(self) -> str:
        return f"{self._config.keycloak_admin_url.rstrip('/')}/admin"

    async def _fetch_admin_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token

        token_url = (
            f"{self._config.keycloak_admin_url.rstrip('/')}"
            f"/realms/{self._config.keycloak_admin_realm}/protocol/openid-connect/token"
        )
        data = {
            "grant_type": "client_credentials",
            "client_id": self._config.keycloak_admin_client_id,
            "client_secret": self._config.keycloak_admin_client_secret,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(token_url, data=data)
        if resp.status_code >= 400:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.KEYCLOAK_SYNC_ERROR,
                message=f"Failed to obtain Keycloak admin token: {resp.text}",
            )
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + int(payload.get("expires_in", 300))
        return self._token

    async def _admin_request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: dict | None = None,
    ) -> Any:
        token = await self._fetch_admin_token()
        url = f"{self._admin_base_url()}{path}"
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.request(
                method,
                url,
                headers=headers,
                json=json_body,
                params=params,
            )
        if resp.status_code == 204:
            return None
        if resp.status_code == 409:
            return {"conflict": True, "body": resp.text}
        if resp.status_code >= 400:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.KEYCLOAK_SYNC_ERROR,
                message=resp.text,
            )
        if not resp.content:
            return None
        return resp.json()

    async def _resolve_client_uuid(self, client_id: str) -> str:
        realm = self._config.keycloak_realm
        clients = await self._admin_request(
            "GET",
            f"/realms/{realm}/clients",
            params={"clientId": client_id},
        )
        if not clients:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.KEYCLOAK_SYNC_ERROR,
                message=f"Keycloak client not found: {client_id}",
            )
        return clients[0]["id"]

    async def create_data_policy_role(
        self,
        policy_mnemonic: str,
        *,
        policy_description: str | None = None,
    ) -> str:
        """
        Create DP_<mnemonic> client role on the registry staff portal client if missing.
        Returns the role name.
        """
        if not self.is_configured:
            _logger.debug(
                "Keycloak data-policy role sync disabled or not configured; skipping %s",
                policy_mnemonic,
            )
            return self._data_policy_role_name(policy_mnemonic)

        role_name = self._data_policy_role_name(policy_mnemonic)
        client_id = self._registry_client_id()
        client_uuid = await self._resolve_client_uuid(client_id)
        realm = self._config.keycloak_realm

        body: dict[str, str] = {"name": role_name}
        if policy_description:
            body["description"] = policy_description

        result = await self._admin_request(
            "POST",
            f"/realms/{realm}/clients/{client_uuid}/roles",
            json_body=body,
        )
        if isinstance(result, dict) and result.get("conflict"):
            _logger.info(
                "Keycloak client role %s already exists on client %s",
                role_name,
                client_id,
            )
        else:
            _logger.info(
                "Created Keycloak client role %s on client %s",
                role_name,
                client_id,
            )
        return role_name

    async def delete_data_policy_role(self, policy_mnemonic: str) -> None:
        """Remove DP_<mnemonic> client role from the registry staff portal client."""
        if not self.is_configured:
            _logger.debug(
                "Keycloak data-policy role sync disabled or not configured; skipping delete %s",
                policy_mnemonic,
            )
            return

        role_name = self._data_policy_role_name(policy_mnemonic)
        client_id = self._registry_client_id()
        client_uuid = await self._resolve_client_uuid(client_id)
        realm = self._config.keycloak_realm

        await self._admin_request(
            "DELETE",
            f"/realms/{realm}/clients/{client_uuid}/roles/{role_name}",
        )
        _logger.info(
            "Deleted Keycloak client role %s from client %s",
            role_name,
            client_id,
        )

    def _data_policy_role_name(self, policy_mnemonic: str) -> str:
        """Build Keycloak client role name for a policy mnemonic (e.g. policy-1 -> DP_policy-1)."""
        name = str(policy_mnemonic).strip()
        if not name:
            raise ValueError("policy_mnemonic is required")
        if self._is_data_policy_role(name):
            return name
        return f"{DATA_POLICY_ROLE_PREFIX}{name}"

    def _is_data_policy_role(self, role: str) -> bool:
        return str(role).strip().upper().startswith(DATA_POLICY_ROLE_PREFIX)
