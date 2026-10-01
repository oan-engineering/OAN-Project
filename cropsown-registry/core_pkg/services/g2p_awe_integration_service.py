from __future__ import annotations

import logging
from typing import Any

from openg2p_fastapi_common.service import BaseService
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..helpers import AWEClientError, AweHelper, get_awe_settings
from ..helpers.awe_status_summary import format_awe_request_status_summary
from ..models import (
    G2PIntakeFormDefinition,
    G2PIntakeFormSubmission,
    G2PRegisterChangeRequest,
    G2PRegisterDefinition,
    G2PRegisterSection,
)
from .g2p_awe_policy_configuration_service import G2PAwePolicyConfigurationService

_config = Settings.get_config(strict=False)
_logger = logging.getLogger(_config.logging_default_logger_name)

REGISTRY_CHANGE_REQUEST_ARTIFACT = "registry.change_request"
REGISTRY_INTAKE_FORM_ARTIFACT = "registry.intake_form"


class G2PAweIntegrationService(BaseService):
    """Registry ↔ AWE orchestration (policy resolve, create_request, proxy decisions)."""

    def _config(self):
        return get_awe_settings()

    def _awe_enabled(self) -> bool:
        return bool(self._config().awe_enabled)

    def _require_bearer(self, bearer_token: str | None) -> str:
        token = (bearer_token or "").strip()
        if not token:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.AWE_BEARER_TOKEN_REQUIRED.value[1],
                message=G2PRegistryErrorCodes.AWE_BEARER_TOKEN_REQUIRED.value[0],
            )
        return token

    @staticmethod
    def _build_context(
        base: dict[str, Any],
        source_data: dict[str, Any] | list[dict[str, Any]] | None,
        context_field_names: list | None,
    ) -> dict[str, Any]:
        context = dict(base)
        if not context_field_names:
            return context
        flat: dict[str, Any] = {}
        if isinstance(source_data, list):
            for item in source_data:
                if isinstance(item, dict):
                    flat.update(item)
        elif isinstance(source_data, dict):
            flat = source_data
        for name in context_field_names:
            if name in flat:
                context[name] = flat[name]
        return context

    async def _resolve_register_mnemonic(
        self,
        session: AsyncSession,
        register_id: str,
    ) -> str | None:
        register = await session.get(G2PRegisterDefinition, register_id)
        return register.register_mnemonic if register else None

    async def _resolve_section_mnemonic(
        self,
        session: AsyncSession,
        section_id: str,
    ) -> str | None:
        section = await session.get(G2PRegisterSection, section_id)
        return section.section_mnemonic if section else None

    async def _resolve_intake_form_mnemonic(
        self,
        session: AsyncSession,
        form_id: str,
    ) -> str | None:
        intake_form = await session.get(G2PIntakeFormDefinition, form_id)
        return intake_form.form_mnemonic if intake_form else None

    def _callback_params(self) -> tuple[str | None, str | None]:
        cfg = self._config()
        url = (cfg.awe_default_callback_url or "").strip() or None
        secret_id = (cfg.awe_callback_secret_id or "").strip() or None
        return url, secret_id

    async def start_change_request_workflow(
        self,
        session: AsyncSession,
        change_request: G2PRegisterChangeRequest,
        change_payload: list[dict] | None,
        *,
        bearer_token: str | None,
        requester: str | None,
    ) -> None:
        if not self._awe_enabled():
            return

        policy_service = G2PAwePolicyConfigurationService.get_component()
        policy = await policy_service.find_effective_policy_configuration(
            session,
            register_id=change_request.register_id,
            policy_type=REGISTRY_CHANGE_REQUEST_ARTIFACT,
            section_id=change_request.section_id,
        )
        if policy is None:
            return

        token = self._require_bearer(bearer_token)
        base = {
            "record_name": change_request.record_name,
            "section_mnemonic": await self._resolve_section_mnemonic(
                session, change_request.section_id
            ),
            "register_mnemonic": await self._resolve_register_mnemonic(
                session, change_request.register_id
            ),
            "change_request_id": change_request.change_request_id,
        }
        context = self._build_context(base, change_payload, policy.context_field_names)
        callback_url, callback_secret_id = self._callback_params()

        try:
            result = await AweHelper.get_component().create_request(
                token,
                policy_key=policy.policy_key,
                artifact_type=REGISTRY_CHANGE_REQUEST_ARTIFACT,
                artifact_id=change_request.change_request_id,
                context=context,
                callback_url=callback_url,
                callback_secret_id=callback_secret_id,
                requester=requester,
                idempotency_key=f"cr-{change_request.change_request_id}",
            )
        except AWEClientError as exc:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.AWE_REQUEST_FAILED.value[1],
                message=f"{G2PRegistryErrorCodes.AWE_REQUEST_FAILED.value[0]}: {exc.message}",
            ) from exc

        change_request.awe_request_id = result.get("request_id")
        change_request.awe_request_status_summary = format_awe_request_status_summary(
            result.get("status"),
            result.get("current_stage_order"),
        )
        session.add(change_request)
        _logger.info(
            "AWE workflow started for change_request_id=%s awe_request_id=%s",
            change_request.change_request_id,
            change_request.awe_request_id,
        )

    async def start_intake_submission_workflow(
        self,
        session: AsyncSession,
        submission: G2PIntakeFormSubmission,
        *,
        bearer_token: str | None,
        requester: str | None,
        record_name: str | None = None,
        register_mnemonic: str | None = None,
        intake_form_mnemonic: str | None = None,
        source_data: list[dict] | None = None,
    ) -> None:
        if not self._awe_enabled():
            return

        policy_service = G2PAwePolicyConfigurationService.get_component()
        policy = await policy_service.find_effective_policy_configuration(
            session,
            register_id=submission.register_id,
            policy_type=REGISTRY_INTAKE_FORM_ARTIFACT,
            intake_form_id=submission.form_id,
        )
        if policy is None:
            return

        token = self._require_bearer(bearer_token)
        base = {
            "record_name": record_name,
            "intake_form_mnemonic": (
                intake_form_mnemonic
                if intake_form_mnemonic is not None
                else await self._resolve_intake_form_mnemonic(session, submission.form_id)
            ),
            "register_mnemonic": (
                register_mnemonic
                if register_mnemonic is not None
                else await self._resolve_register_mnemonic(session, submission.register_id)
            ),
            "submission_id": submission.submission_id,
        }
        context = self._build_context(base, source_data, policy.context_field_names)
        callback_url, callback_secret_id = self._callback_params()

        try:
            result = await AweHelper.get_component().create_request(
                token,
                policy_key=policy.policy_key,
                artifact_type=REGISTRY_INTAKE_FORM_ARTIFACT,
                artifact_id=submission.submission_id,
                context=context,
                callback_url=callback_url,
                callback_secret_id=callback_secret_id,
                requester=requester,
                idempotency_key=f"intake-{submission.submission_id}",
            )
        except AWEClientError as exc:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.AWE_REQUEST_FAILED.value[1],
                message=f"{G2PRegistryErrorCodes.AWE_REQUEST_FAILED.value[0]}: {exc.message}",
            ) from exc

        submission.awe_request_id = result.get("request_id")
        submission.awe_request_status_summary = format_awe_request_status_summary(
            result.get("status"),
            result.get("current_stage_order"),
        )
        session.add(submission)
        _logger.info(
            "AWE workflow started for submission_id=%s awe_request_id=%s",
            submission.submission_id,
            submission.awe_request_id,
        )
