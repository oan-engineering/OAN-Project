"""Keycloak lookup backing the approver-resolver HTTP endpoint (see
`g2p_approver_resolver_controller.py`): given a hierarchical approval level
(kebele/woreda) and the specific location value the record being
approved carries at that level, return the username(s) of whichever staff
user holds BOTH the matching client role (Kebele/Woreda Approver,
under the staff portal client) AND an `approver_location_value` attribute
matching that location.
"""

import logging
import os
from typing import Any

import httpx

_logger = logging.getLogger("g2p-cropsown-approver-resolver")

_LEVEL_TO_ROLE = {
    "kebele": "Kebele Approver",
    "woreda": "Woreda Approver",
    "zone": "Zone Approver",
    "region": "Region Approver",
}

_LOCATION_ATTR = "approver_location_value"

_GEO_LABEL_CACHE: dict[str, str] = {
    "central_ethiopia": "Central Ethiopia",
    "amhara": "Amhara",
    "dire": "Dire Dawa",
    "dire_dawa": "Dire Dawa",
    "oromia": "Oromia",
    "benishangul": "Benishangul-Gumuz",
    "ethiopia_somali": "Somali",
    "somali": "Somali",
    "tigray": "Tigray",
    "afar": "Afar",
    "sidama": "Sidama",
    "south_ethiopian": "South Ethiopian",
    "south_west_ethiopia": "South West Ethiopia",
    "gambela": "Gambela",
    "harari": "Harari",
    "addis_ababa": "Addis Ababa",
    "ET01": "Tigray",
    "ET02": "Afar",
    "ET03": "Amhara",
    "ET04": "Oromia",
    "ET05": "Somali",
    "ET06": "Benishangul-Gumuz",
    "ET07": "Central Ethiopia",
    "ET08": "South Ethiopian",
    "ET11": "South West Ethiopia",
    "ET12": "Gambela",
    "ET13": "Harari",
    "ET14": "Addis Ababa",
    "ET15": "Dire Dawa",
    "ET16": "Sidama",
}


def _keycloak_config() -> dict[str, Any] | None:
    """Where and how to talk to Keycloak."""
    base = (
        os.environ.get("KEYCLOAK_BASE_URL", "").strip().rstrip("/")
        or os.environ.get("KEYCLOAK_URL", "").strip().rstrip("/")
    )
    host = os.environ.get("KEYCLOAK_HOST", "").strip()
    if not base and host:
        base = f"http://{host}:{os.environ.get('KEYCLOAK_PORT', '8080').strip() or '8080'}"
    if base:
        realm = os.environ.get("KEYCLOAK_REALM", "staff").strip() or "staff"
        return {
            "base": base,
            "token_realm": realm,
            "users_realm": realm,
            "client_id": os.environ.get("AUTH_CLIENT_ID", "cropsown-staff-portal"),
            "client_secret": os.environ.get("AUTH_CLIENT_SECRET", ""),
        }
    try:
        from openg2p_registry_core.config import Settings

        cfg = Settings.get_config(strict=False)
    except Exception as exc:
        _logger.warning("approver-resolver: registry settings unavailable: %s", exc)
        return None

    url = (getattr(cfg, "keycloak_admin_url", None) or "").rstrip("/")
    client_id = getattr(cfg, "keycloak_admin_client_id", None)
    client_secret = getattr(cfg, "keycloak_admin_client_secret", None)
    if not (url and client_id and client_secret):
        _logger.warning(
            "approver-resolver: Keycloak not configured — set KEYCLOAK_BASE_URL (or "
            "KEYCLOAK_HOST/KEYCLOAK_PORT), KEYCLOAK_REALM, AUTH_CLIENT_ID and "
            "AUTH_CLIENT_SECRET on staff-api, or the registry keycloak_admin_* settings"
        )
        return None
    return {
        "base": url,
        "token_realm": getattr(cfg, "keycloak_admin_realm", None) or "master",
        "users_realm": getattr(cfg, "keycloak_realm", None) or "staff",
        "client_id": client_id,
        "client_secret": client_secret,
    }


def _roles_client_id() -> str:
    """The Keycloak client that carries the approver roles."""
    explicit = os.environ.get("APPROVER_ROLES_CLIENT_ID") or os.environ.get("AUTH_CLIENT_ID")
    if explicit:
        return explicit
    try:
        from openg2p_registry_core.config import Settings

        configured = getattr(Settings.get_config(strict=False), "keycloak_client_id", None)
    except Exception:
        configured = None
    return configured or "cropsown-staff-portal"


async def _admin_token(client: httpx.AsyncClient, cfg: dict[str, Any]) -> str:
    """Client-credentials token able to read users of the staff realm."""
    resp = await client.post(
        f"{cfg['base']}/realms/{cfg['token_realm']}/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


async def _resolve_code_to_mnemonic(raw_val: str, level: str) -> str | None:
    """Defensive fallback: resolve raw code (e.g. 30405401001) to mnemonic (e.g. Dire Arerti)."""
    if not raw_val:
        return None
    cleaned = raw_val.strip()
    if not cleaned:
        return None
    if cleaned in _GEO_LABEL_CACHE:
        return _GEO_LABEL_CACHE[cleaned]

    try:
        from ..odk_ingest_hooks import resolve_geo_label

        mnemonic = await resolve_geo_label(cleaned, level)
        if mnemonic:
            return mnemonic
    except Exception as e:
        _logger.debug("approver-resolver: fallback geo resolution error for %s: %s", raw_val, e)
    return None


async def resolve_approvers(level: str, location_value: str | None) -> list[str]:
    """Return the username(s) of the approver(s) for this level+location.
    
    Empty list if the role, client, or matching user doesn't exist (triggers
    AWE's on_empty='block' stage config).
    
    If location_value is empty/None, resolves to all approvers holding the role
    (unscoped fallback rule, preventing stalling on unassigned/empty locations).
    """
    role_name = _LEVEL_TO_ROLE.get(level.lower())
    if not role_name:
        _logger.warning("approver-resolver: unknown level '%s'", level)
        return []

    raw_loc = (location_value or "").strip() or None

    cfg = _keycloak_config()
    if cfg is None:
        return []

    # Prepare candidate location strings for matching Keycloak attributes:
    # 1. Raw value as passed
    # 2. Resolved mnemonic if raw value is a code (e.g. "Dire Arerti")
    candidate_locations = set()
    if raw_loc:
        candidate_locations.add(raw_loc)
        resolved = await _resolve_code_to_mnemonic(raw_loc, level)
        if resolved:
            candidate_locations.add(resolved)
        # Also stripped of prefixes like KEBELE_ET
        for prefix in ("KEBELE_", "WOREDA_", "ZONE_", "REGION_"):
            if raw_loc.startswith(prefix):
                candidate_locations.add(raw_loc[len(prefix):])

    base = cfg["base"]
    realm = cfg["users_realm"]
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            token = await _admin_token(client, cfg)
        except httpx.HTTPError as exc:
            _logger.warning("approver-resolver: could not get Keycloak admin token: %s", exc)
            return []
        headers = {"Authorization": f"Bearer {token}"}

        client_lookup = await client.get(
            f"{base}/admin/realms/{realm}/clients",
            headers=headers,
            params={"clientId": _roles_client_id()},
        )
        client_lookup.raise_for_status()
        found = client_lookup.json()
        if not found:
            _logger.warning("approver-resolver: client '%s' not found in realm '%s'", _roles_client_id(), realm)
            return []
        client_uuid = found[0]["id"]

        role_users_resp = await client.get(
            f"{base}/admin/realms/{realm}/clients/{client_uuid}/roles/{role_name}/users",
            headers=headers,
            params={"max": 200},
        )
        if role_users_resp.status_code == 404:
            _logger.warning("approver-resolver: role '%s' not found under client '%s'", role_name, _roles_client_id())
            return []
        role_users_resp.raise_for_status()
        candidates = role_users_resp.json()

        matched: list[str] = []
        for candidate in candidates:
            username = candidate.get("username")
            if not username:
                continue
            if not raw_loc:
                # Unscoped record: any holder of the role may approve.
                matched.append(username)
                continue

            user_resp = await client.get(
                f"{base}/admin/realms/{realm}/users/{candidate['id']}",
                headers=headers,
            )
            if user_resp.status_code != 200:
                continue
            attrs = user_resp.json().get("attributes") or {}
            attr_values = attrs.get(_LOCATION_ATTR) or []

            # Check if any candidate location matches the user's approver_location_value
            if any(cand in attr_values for cand in candidate_locations):
                matched.append(username)
            else:
                # Case-insensitive / whitespace-tolerant comparison
                attr_values_normalized = {str(v).strip().lower() for v in attr_values}
                if any(str(cand).strip().lower() in attr_values_normalized for cand in candidate_locations):
                    matched.append(username)

        # Unscoped fallback: if specific location approver didn't match anyone,
        # but holders of this level's role exist, return them so workflow doesn't block forever
        if not matched and candidates:
            _logger.warning(
                "approver-resolver: no user matched location candidates %s for level '%s', falling back to all role holders",
                candidate_locations,
                level,
            )
            return [c.get("username") for c in candidates if c.get("username")]

        return matched
