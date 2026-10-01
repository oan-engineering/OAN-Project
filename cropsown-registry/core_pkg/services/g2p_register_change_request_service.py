import importlib
import logging
import uuid
from datetime import datetime

from fastapi_cache.decorator import cache
from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService
from openg2p_registry_core.services.g2p_completion_score_service import G2PCompletionScoreService
from openg2p_registry_core.services.g2p_score_compute_service import G2PScoreComputeService
from sqlalchemy import Boolean, Date as SQLDate, Float, Integer, Numeric, and_, exists, func, inspect, or_, select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..cache import metadata_key_builder
from ..config import Settings
from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..models import (
    ApprovalStatusEnum,
    ChangeRequestSourceEnum,
    G2PFunctionalIdGenerationQueue,
    G2PRegisterChangeRequest,
    G2PRegisterChangeRequestDocument,
    G2PRegisterChangeRequestPayload,
    G2PRegisterDefinition,
    G2PRegisterDocumentHistory,
    G2PRegisterSection,
    G2PRegisterSectionDocument,
    G2PRegisterUITab,
    G2PRegisterVerification,
    RegisterPurposeEnum,
)
from ..schemas import (
    AddVerificationPayload,
    ChangePayload,
    ChangeRequestData,
    ChangeRequestFlattenedData,
    ChangeRequestRequestPayload,
    ChangeRequestSearchResultData,
    ChangeRequestSequenceCheckData,
    ChangeRequestSummaryData,
    CrossRegisterChangeRequestData,
    ChangeActionEnum,
    NumberOfCrossRegisterChangesData,
    NumberOfPendingChangeRequestsData,
    VerificationData,
)
from .g2p_outgest_fanout_service import fanout_outgest_rows
from .g2p_awe_integration_service import G2PAweIntegrationService
from .g2p_awe_status_reconcile import (
    REGISTRY_CHANGE_REQUEST_ARTIFACT,
    reconcile_artifact_status_summary,
)
from .g2p_register_domain_service import G2PRegisterDomainService
from .g2p_register_history_service import G2PRegisterHistoryService
from .g2p_register_service import G2PRegisterService

_logger = logging.getLogger("g2p-register-change-request-service")
_config = Settings.get_config(strict=False)

import os
_EXTENSION_MODULE = os.environ.get("REGISTRY_EXTENSION_MODULE", "openg2p_registry_extensions")
_DOMAIN_FACTORY_MODULE = f"{_EXTENSION_MODULE}.register_domain.factory"
_DOMAIN_MODELS_MODULE = f"{_EXTENSION_MODULE}.register_domain.models"
_DOMAIN_SCHEMAS_MODULE = f"{_EXTENSION_MODULE}.register_domain.schemas"
_DOMAIN_FACTORY_CLASS = "G2PRegisterDomainFactory"
_REGISTER_CLASS_PREFIX = "G2PRegister"
_REGISTER_SCHEMA_CLASS_PREFIX = "G2PRegisterSchema"
_REGISTER_HISTORY_CLASS_PREFIX = "G2PRegisterHistory"


class G2PRegisterChangeRequestService(BaseService):
    @cache(expire=_config.cache_expires_in_seconds, key_builder=metadata_key_builder)
    async def _get_register_definition(self, register_id: str, session):
        return await session.get(G2PRegisterDefinition, register_id)

    @cache(expire=_config.cache_expires_in_seconds, key_builder=metadata_key_builder)
    async def _get_section(self, section_id: str, session):
        return await session.get(G2PRegisterSection, section_id)

    @cache(expire=_config.cache_expires_in_seconds, key_builder=metadata_key_builder)
    async def _get_tab(self, tab_id: str, session):
        return await session.get(G2PRegisterUITab, tab_id)

    async def create_change_request(
        self,
        change_request_request_payload: ChangeRequestRequestPayload,
        source_partner_id: str = None,
        created_by: str | None = None,
        change_request_source: str | None = None,
        bearer_token: str | None = None,
        requester_sub: str | None = None,
    ):
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:

            register_definition: G2PRegisterDefinition = await self.validate_register_definition(change_request_request_payload.register_id, session)
            register_section: G2PRegisterSection = await self.validate_section(change_request_request_payload.section_id, session)
            register_tab: G2PRegisterUITab = await self.validate_tab(change_request_request_payload.tab_id, session)
            section_register_definition: G2PRegisterDefinition = await self.validate_register_definition(
                register_section.section_register_id,
                session,
            )
            await self.validate_change_request_creation(
                change_request_request_payload,
                register_definition,
                register_section,
                section_register_definition,
            )
            records = self._records_from_change_request_payload(change_request_request_payload)
            if change_request_request_payload.internal_record_id:
                for r in records:
                    if isinstance(r, dict) and not r.get("link_internal_record_id"):
                        r["link_internal_record_id"] = change_request_request_payload.internal_record_id
            await self._validate_domain_attributes(
                records,
                section_register_definition.register_mnemonic,
                session=session,
            )
            if change_request_request_payload.change_payload:
                for i, r in enumerate(records):
                    if i < len(change_request_request_payload.change_payload):
                        target = change_request_request_payload.change_payload[i]
                        if isinstance(target, dict):
                            target.update(r)
                        elif hasattr(target, "__dict__"):
                            for k, v in r.items():
                                setattr(target, k, v)
                            if hasattr(target, "__pydantic_extra__"):
                                if target.__pydantic_extra__ is None:
                                    target.__pydantic_extra__ = {}
                                for k, v in r.items():
                                    if k not in target.__class__.model_fields:
                                        target.__pydantic_extra__[k] = v

            # Extract internal_record_id from change_payload if present
            # Note: For new record creation, internal_record_id may be a new UUID that doesn't exist yet
            # We don't validate internal_record_id existence here - it will be created when the change request is approved

            g2p_register_change_request: G2PRegisterChangeRequest = await self.construct_change_request(
                change_request_request_payload,
                register_section,
                register_definition.register_mnemonic,
                section_register_definition.register_mnemonic,
                source_partner_id,
                created_by,
                change_request_source_override=change_request_source,
                session=session,
            )

            session.add(g2p_register_change_request)

            if hasattr(g2p_register_change_request, '_payload'):
                session.add(g2p_register_change_request._payload)

            # Attach already-uploaded documents (validated against the catalog)
            if change_request_request_payload.documents:
                from .g2p_document_service import G2PDocumentService
                document_service = G2PDocumentService.get_component()
                await document_service.validate_documents_exist(
                    session,
                    [doc.document_id for doc in change_request_request_payload.documents],
                )
                for doc in change_request_request_payload.documents:
                    session.add(G2PRegisterChangeRequestDocument(
                        change_request_id=g2p_register_change_request.change_request_id,
                        document_id=doc.document_id,
                        section_id=change_request_request_payload.section_id,
                        label=doc.label,
                    ))

            serialized_payloads: list[dict] = (
                [item.model_dump() for item in change_request_request_payload.change_payload]
                if change_request_request_payload.change_payload
                else []
            )
            await session.flush()
            await G2PAweIntegrationService.get_component().start_change_request_workflow(
                session,
                g2p_register_change_request,
                serialized_payloads,
                bearer_token=bearer_token,
                requester=requester_sub or created_by,
            )
            await session.commit()
            await session.refresh(g2p_register_change_request)

            return g2p_register_change_request

    async def get_change_request_summary_data(
        self,
        policy_mnemonics: list[str] | None = None,
    ) -> ChangeRequestSummaryData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            change_request_summary_data: ChangeRequestSummaryData = await self._fetch_change_request_summary_data(
                session, policy_mnemonics
            )
            return change_request_summary_data

    async def get_change_requests(
        self,
        subject_register_id: str,
        subject_record_id: str,
        tab_id: str,
        current_page: int = 1,
        page_size: int = 10,
        sort_by: str = None,
        filter_by: dict = None,
        policy_mnemonics: list[str] | None = None,
    ) -> tuple[list[ChangeRequestData], int]:
        """Get all change requests for a specific internal record and tab with pagination"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._ensure_subject_record_readable(
                subject_register_id, subject_record_id, policy_mnemonics, session
            )
            change_requests_list, total_items = await self._fetch_change_requests(subject_register_id, subject_record_id, tab_id, current_page, page_size, sort_by, filter_by, session)
            return change_requests_list, total_items

    async def get_change_request(
        self,
        change_request_id: str,
        policy_mnemonics: list[str] | None = None,
    ) -> ChangeRequestData:
        """Get a single change request by ID"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._ensure_change_request_readable(change_request_id, policy_mnemonics, session)
            change_request_data: ChangeRequestData = await self._fetch_change_request(change_request_id, session)
            await session.commit()
            return change_request_data

    async def get_change_request_sequence_check(
        self, change_request_id: str
    ) -> ChangeRequestSequenceCheckData:
        """Return whether earlier pending CRs block approval for this change request."""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            change_request = (
                await session.execute(
                    select(G2PRegisterChangeRequest).where(
                        G2PRegisterChangeRequest.change_request_id == change_request_id
                    )
                )
            ).scalar_one_or_none()
            if change_request is None:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_FOUND.value[1],
                    message=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_FOUND.value[0],
                )

            number_of_earlier_pending = await self._count_earlier_pending_change_requests(
                change_request, session
            )
            has_earlier_pending = number_of_earlier_pending > 0
            approval_decision_blocked = (
                change_request.approval_status == ApprovalStatusEnum.PENDING.value
                and has_earlier_pending
            )

            return ChangeRequestSequenceCheckData(
                change_request_id=change_request.change_request_id,
                internal_record_id=change_request.internal_record_id,
                has_earlier_pending_change_requests=has_earlier_pending,
                number_of_earlier_pending_change_requests=number_of_earlier_pending,
                approval_decision_blocked=approval_decision_blocked,
            )

    async def get_change_requests_flattened(
        self,
        subject_register_id: str,
        subject_record_id: str,
        tab_id: str,
        current_page: int = 1,
        page_size: int = 10,
        sort_by: str = None,
        filter_by: dict = None,
        policy_mnemonics: list[str] | None = None,
    ) -> tuple[list[ChangeRequestFlattenedData], int]:
        """Get all change requests for a specific internal record and tab with flattened change_payload fields"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._ensure_subject_record_readable(
                subject_register_id, subject_record_id, policy_mnemonics, session
            )
            change_requests_list, total_items = await self._fetch_change_requests_flattened(subject_register_id, subject_record_id, tab_id, current_page, page_size, sort_by, filter_by, session)
            return change_requests_list, total_items

    async def approve_change_request(self, change_request_id: str, approved_by: str | None = None):
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            change_request = await self._approve_change_request_core(
                change_request_id=change_request_id,
                session=session,
                approved_by=approved_by,
            )
            await self._fanout_outgest_for_change_request(change_request, session)
            
            _logger.info("Approved change request: %s", change_request_id)
            await session.commit()
            await session.refresh(change_request)
            return change_request


    async def _approve_change_request_core(
        self,
        change_request_id: str,
        session,
        skip_verification: bool = False,
        skip_sequence_check: bool = False,
        approved_by: str | None = None,
    ):
        change_request: G2PRegisterChangeRequest = await self.validate_change_request_exists(change_request_id, session)
        self._set_change_request_approval_state(
            change_request,
            approval_status=ApprovalStatusEnum.APPROVED.value,
            actor_name=approved_by,
            session=session,
        )

        _logger.info(f"Validating change request for approval: {change_request}")
        register_section = await self.validate_change_request_section(change_request, session)
        if not skip_verification:
            await self.validate_change_request_verifications(change_request, session)
        if not skip_sequence_check:
            await self.validate_change_request_sequence(change_request, session)

        await self._run_pre_approve_hook(change_request.section_register_id, change_request, session)

        if register_section.section_register_id == register_section.register_id:
            await self.approve_register(change_request, register_section, session)
        else:
            await self.approve_table(change_request, register_section, session)

        await self.insert_into_register_history(change_request, session)
        # Promote attached docs
        await self._handle_documents_on_approval(change_request, register_section, session)

        await self._run_post_approve_hook(change_request.section_register_id, change_request, session)

        # Enqueue completion score recomputation for the touched section
        completion_score_service = G2PCompletionScoreService.get_component() or G2PCompletionScoreService()
        await completion_score_service.enqueue_completion_score_computations(
            register_id=register_section.register_id,
            internal_record_id=change_request.internal_record_id,
            session=session,
            change_request_id=change_request.change_request_id,
            section_id=change_request.section_id,
        )

        # Enqueue score computations for the change request
        _logger.debug(f"Enqueuing score computations for change_request_id: {change_request_id}")
        g2p_score_compute_service = G2PScoreComputeService.get_component() or G2PScoreComputeService()
        await g2p_score_compute_service.enqueue_score_computations_for_change_request(
            change_request=change_request,
            session=session,
        )
        _logger.debug(f"Finished enqueuing score computations for change_request_id: {change_request_id}")
            

        return change_request

    async def approve_change_request_from_awe_webhook(
        self,
        change_request_id: str,
        session,
        approved_by: str | None = None,
    ) -> G2PRegisterChangeRequest:
        """Apply terminal AWE approval using the same path as the staff-portal approve API."""
        change_request = await self.validate_change_request_exists(change_request_id, session)
        if change_request.approval_status == ApprovalStatusEnum.APPROVED.value:
            return change_request

        change_request = await self._approve_change_request_core(
            change_request_id=change_request_id,
            session=session,
            skip_verification=True,
            skip_sequence_check=True,
            approved_by=approved_by,
        )
        await self._fanout_outgest_for_change_request(change_request, session)
        score_service = G2PScoreComputeService.get_component() or G2PScoreComputeService()
        await score_service.enqueue_score_computations_for_change_request(
            change_request=change_request,
            session=session,
        )
        return change_request

    async def approve_register(self, change_request: G2PRegisterChangeRequest, section: G2PRegisterSection, session) -> None:
        register_definition, register_class, schema_class = await self._get_register_class_and_schema(
            section.section_register_id,
            session,
        )
        payload = await self._get_change_request_payload(change_request.change_request_id, session)
        existing = await self._get_existing_record(register_class, change_request.internal_record_id, session)
        if not existing:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTER_DATA_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.REGISTER_DATA_NOT_FOUND.value[0],
            )

        changed = False
        for change_payload in payload.change_payload or []:
            action = change_payload.get("edit_action", ChangeActionEnum.UPDATE.value)
            if action == ChangeActionEnum.NO_CHANGE.value:
                continue
            change_payload["internal_record_id"] = change_request.internal_record_id
            schema_instance = schema_class(**(change_payload or {}))
            self._update_existing_record(existing, schema_instance.dict(), change_payload, register_class)
            self._set_if_column(existing, "last_approved_at", change_request.approved_at)
            self._set_if_column(existing, "last_approved_by", change_request.approved_by or "system")
            changed = True

        if changed:
            flag_modified(payload, "change_payload")

    async def approve_table(self, change_request: G2PRegisterChangeRequest, section: G2PRegisterSection, session) -> None:
        _, table_class, schema_class = await self._get_register_class_and_schema(section.section_register_id, session)
        payload = await self._get_change_request_payload(change_request.change_request_id, session)
        changed = False

        for change_payload in payload.change_payload or []:
            action = change_payload.get("edit_action", ChangeActionEnum.ADD.value)
            if action == ChangeActionEnum.NO_CHANGE.value:
                continue

            if action == ChangeActionEnum.ADD.value:
                if not change_payload.get("link_internal_record_id"):
                    raise self._invalid_request("link_internal_record_id is required for table ADD change payloads.")
                change_payload["internal_record_id"] = change_payload.get("internal_record_id") or str(uuid.uuid4())
                schema_instance = schema_class(**(change_payload or {}))
                record_data = self._build_record_data(schema_instance.dict(), change_payload, table_class)
                self._set_data_if_column(record_data, table_class, "created_by", change_request.created_by)
                self._set_data_if_column(record_data, table_class, "created_at", change_request.created_at)
                self._set_data_if_column(record_data, table_class, "last_approved_at", change_request.approved_at)
                self._set_data_if_column(record_data, table_class, "last_approved_by", change_request.approved_by or "system")
                session.add(table_class(**record_data))
                changed = True
                continue

            internal_record_id = change_payload.get("internal_record_id")
            if not internal_record_id:
                raise self._invalid_request(f"internal_record_id is required for table {action} change payloads.")
            existing = await self._get_existing_record(table_class, internal_record_id, session)
            if not existing:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.REGISTER_DATA_NOT_FOUND.value[1],
                    message=G2PRegistryErrorCodes.REGISTER_DATA_NOT_FOUND.value[0],
                )

            if action == ChangeActionEnum.UPDATE.value:
                schema_instance = schema_class(**(change_payload or {}))
                self._update_existing_record(existing, schema_instance.dict(), change_payload, table_class)
                self._set_if_column(existing, "last_approved_at", change_request.approved_at)
                self._set_if_column(existing, "last_approved_by", change_request.approved_by or "system")
                changed = True
            elif action == ChangeActionEnum.DELETE.value:
                await session.delete(existing)
            else:
                raise self._invalid_request(f"Unsupported table change payload action: {action}")

        if changed:
            flag_modified(payload, "change_payload")

    async def approve_primary_master_section_change_request(
        self,
        change_request_id: str,
        session,
        skip_verification: bool = False,
        skip_sequence_check: bool = False,
        approved_by: str | None = None,
    ) -> tuple[G2PRegisterChangeRequest, str]:
        change_request: G2PRegisterChangeRequest = await self.validate_change_request_exists(change_request_id, session)

        self._set_change_request_approval_state(
            change_request,
            approval_status=ApprovalStatusEnum.APPROVED.value,
            actor_name=approved_by,
            session=session,
        )

        _logger.info(f"Approving primary master section change request: {change_request}")
        register_section = await self.validate_change_request_core(change_request, session, skip_verification, skip_sequence_check)

        await self._run_pre_approve_hook(change_request.section_register_id, change_request, session)

        # In case of approval, insert data into register_history
        await self.insert_into_register_history(change_request, session)
        # Upsert data into register
        subject_internal_record_id = await self.insert_primary_master_section_into_register(change_request, session)
        await self._handle_documents_on_approval(change_request, register_section, session)

        # Handle POST APPROVAL domain service operation
        await self._run_post_approve_hook(change_request.section_register_id, change_request, session)

        return change_request, subject_internal_record_id

    async def approve_non_primary_master_section_change_request(
        self,
        change_request_id: str,
        session,
        skip_verification: bool = False,
        skip_sequence_check: bool = False,
        approved_by: str | None = None,
    ) -> G2PRegisterChangeRequest:
        change_request: G2PRegisterChangeRequest = await self.validate_change_request_exists(
            change_request_id, session
        )
        self._set_change_request_approval_state(
            change_request,
            approval_status=ApprovalStatusEnum.APPROVED.value,
            actor_name=approved_by,
            session=session,
        )

        _logger.info("Approving non-primary master section change request: %s", change_request)
        register_section = await self.validate_change_request_core(
            change_request, session, skip_verification, skip_sequence_check
        )
        await self._run_pre_approve_hook(change_request.section_register_id, change_request, session)
        await self.insert_into_register_history(change_request, session)
        await self.insert_non_primary_master_section_into_register(
            change_request, change_request.internal_record_id, session
        )
        await self._handle_documents_on_approval(change_request, register_section, session)
        await self._run_post_approve_hook(
            change_request.section_register_id, change_request, session
        )
        return change_request

    async def insert_primary_master_section_into_register(self, change_request: G2PRegisterChangeRequest, session) -> str:
        subject_internal_record_id: str | None = None

        register_definition, register_class, schema_class = await self._get_register_class_and_schema(
            change_request.section_register_id,
            session,
        )
        payload = await self._get_change_request_payload(change_request.change_request_id, session)
        change_payload = payload.change_payload[0]
        if change_payload.get("edit_action") == ChangeActionEnum.NO_CHANGE.value:
            _logger.info(f"No change action for change request '{change_request.change_request_id}', skipping register update.")
            return change_request.internal_record_id

        register_schema_instance = schema_class(**(change_payload or {}))

        existing = (
            await session.execute(
                select(register_class).where(
                    register_class.internal_record_id == change_request.internal_record_id
                )
            )
        ).scalar()

        if change_payload.get("edit_action") == ChangeActionEnum.ADD.value:
            # Build the payload dict excluding None values from schema, then add base fields
            schema_dict = {k: v for k, v in register_schema_instance.dict().items() if v is not None}
            # Use a single canonical internal_record_id for insert + queueing.
            subject_internal_record_id = (
                schema_dict.get("internal_record_id") or change_request.internal_record_id
            )
            schema_dict["internal_record_id"] = subject_internal_record_id

            generate_functional_record_id: bool = await self._check_functional_record_id_generation_required(
                register_definition
            )
            if generate_functional_record_id and not change_payload.get("functional_record_id"):
                await self._handle_functional_record_id_generation(
                    register_id=register_definition.register_id,
                    internal_record_id=subject_internal_record_id,
                    session=session,
                )
                gen_id = None
                try:
                    import random
                    from openg2p_registry_cropsown_extension.register_domain.factory import G2PIdGeneratorFactory
                    factory = G2PIdGeneratorFactory.get_component() or G2PIdGeneratorFactory()
                    generator = factory.get_id_generator()
                    if generator:
                        affix = generator.generate_prefix_suffix(schema_dict, register_definition.register_mnemonic)
                        seq_num = random.randint(10000, 99999)
                        gen_id = f"{affix.prefix}{seq_num:05d}{affix.suffix}"
                except Exception as e:
                    _logger.warning(f"Failed synchronous functional ID generation in CR: {e}")
                schema_dict["functional_record_id"] = gen_id or f"TEMP-{uuid.uuid4().hex}"
            else:
                schema_dict["functional_record_id"] = change_payload.get("functional_record_id")
            schema_dict["created_by"] = change_request.created_by
            schema_dict["created_at"] = change_request.created_at
            schema_dict["last_approved_at"] = change_request.approved_at
            schema_dict["last_approved_by"] = change_request.approved_by or "system"

            # Convert date strings to date objects before creating the instance
            schema_dict = self._convert_date_strings_to_objects(schema_dict, register_class)
            
            new_instance = register_class(**schema_dict)
            session.add(new_instance)
        elif change_payload.get("edit_action") == ChangeActionEnum.UPDATE.value and existing:
            subject_internal_record_id = existing.internal_record_id
            mapper = inspect(register_class)
            for key, value in register_schema_instance.dict().items():
                # Only update values in change request payload
                    if key in change_payload:
                        value = self._normalize_model_value(value, key, mapper)
                    setattr(existing, key, value)
            self._mark_record_as_last_approved(existing, change_request)
        else:
            self._raise_unknown_change_payload_action(change_payload, change_request.change_request_id)
        return subject_internal_record_id


    async def insert_non_primary_master_section_into_register(self, change_request: G2PRegisterChangeRequest, subject_internal_record_id: str, session):
        _, register_class, schema_class = await self._get_register_class_and_schema(
            change_request.section_register_id,
            session,
        )
        payload = await self._get_change_request_payload(change_request.change_request_id, session)
        
        for change_payload in payload.change_payload:
            if change_payload.get("edit_action") == ChangeActionEnum.NO_CHANGE.value:
                _logger.info(f"No change action for change request '{change_request.change_request_id}', skipping register update.")
                continue

            register_schema_instance = schema_class(**(change_payload or {}))

            existing = (
                await session.execute(
                    select(register_class).where(
                        register_class.internal_record_id == subject_internal_record_id
                    )
                )
            ).scalar()

            if not existing:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.REGISTER_DATA_NOT_FOUND.value[1],
                    message=(
                        f"Subject record not found for internal_record_id '{subject_internal_record_id}' "
                        f"while approving change request '{change_request.change_request_id}'."
                    ),
                )

            if change_payload.get("edit_action") == ChangeActionEnum.ADD.value or change_payload.get("edit_action") == ChangeActionEnum.UPDATE.value:
                mapper = inspect(register_class)
                for key, value in register_schema_instance.dict().items():
                    # Only update values in change request payload
                    if key in change_payload:
                        # Keep subject identity immutable across non-primary section approvals.
                        if key in {"internal_record_id", "link_internal_record_id"}:
                            continue
                        value = self._normalize_model_value(value, key, mapper)
                        setattr(existing, key, value)
                self._mark_record_as_last_approved(existing, change_request)
            else:
                self._raise_unknown_change_payload_action(change_payload, change_request.change_request_id)

    async def approve_child_section_change_request(
        self,
        change_request_id: str,
        subject_internal_record_id: str,
        session,
        skip_verification: bool = False,
        skip_sequence_check: bool = False,
        approved_by: str | None = None,
    ) -> G2PRegisterChangeRequest:
        change_request: G2PRegisterChangeRequest = await self.validate_change_request_exists(change_request_id, session)

        self._set_change_request_approval_state(
            change_request,
            approval_status=ApprovalStatusEnum.APPROVED.value,
            actor_name=approved_by,
            session=session,
        )

        _logger.info(f"Approving child section change request: {change_request}")
        register_section = await self.validate_change_request_core(change_request, session, skip_verification, skip_sequence_check)

        await self._run_pre_approve_hook(change_request.section_register_id, change_request, session)

        # In case of approval, insert data into register_history
        await self.insert_into_register_history(change_request, session)
        # Upsert data into register
        subject_internal_record_id = await self.insert_child_section_into_register(change_request, subject_internal_record_id, session)
        await self._handle_documents_on_approval(change_request, register_section, session)

        # Handle POST APPROVAL domain service operation
        await self._run_post_approve_hook(change_request.section_register_id, change_request, session)

        return change_request

    async def insert_child_section_into_register(self, change_request: G2PRegisterChangeRequest, subject_internal_record_id: str, session):
        _, register_class, schema_class = await self._get_register_class_and_schema(
            change_request.section_register_id,
            session,
        )
        payload = await self._get_change_request_payload(change_request.change_request_id, session)

        # change_payload is now always a list
        for change_payload in payload.change_payload:
            if change_payload.get("edit_action") == ChangeActionEnum.NO_CHANGE.value:
                _logger.info(f"No change action for change request '{change_request.change_request_id}', skipping register update.")
                continue

            register_schema_instance = schema_class(**(change_payload or {}))
        
            existing = (
                await session.execute(
                    select(register_class).where(
                        register_class.internal_record_id == change_payload.get("internal_record_id")
                    )
                )
            ).scalar()

            if change_payload.get("edit_action") == ChangeActionEnum.UPDATE.value and existing:
                mapper = inspect(register_class)
                for key, value in register_schema_instance.dict().items():
                    # Only update values in change request payload
                    if key in change_payload:
                        value = self._normalize_model_value(value, key, mapper)
                        setattr(existing, key, value)
                self._mark_record_as_last_approved(existing, change_request)
            elif change_payload.get("edit_action") == ChangeActionEnum.ADD.value:
                # Build the payload dict excluding None values from schema, then add base fields
                schema_dict = {k: v for k, v in register_schema_instance.dict().items() if v is not None}
                schema_dict["functional_record_id"] = change_payload.get("functional_record_id") 
                schema_dict["created_by"] = change_request.created_by
                schema_dict["created_at"] = change_request.created_at
                schema_dict["last_approved_at"] = change_request.approved_at
                schema_dict["last_approved_by"] = change_request.approved_by or "system"
                
                # Convert date strings to date objects before creating the instance
                schema_dict = self._convert_date_strings_to_objects(schema_dict, register_class)
                
                new_instance = register_class(**schema_dict)
                session.add(new_instance)
            elif change_payload.get("edit_action") == ChangeActionEnum.DELETE.value and existing:
                await session.delete(existing)
            else:
                self._raise_unknown_change_payload_action(change_payload, change_request.change_request_id)

    async def reject_change_request(
        self,
        change_request_id: str,
        reason: str,
        rejected_by: str | None = None,
    ):
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            change_request = await self.validate_change_request_exists(change_request_id, session)
            _logger.info("Validated change request for rejection: %s", change_request)
            self._set_change_request_approval_state(
                change_request,
                approval_status=ApprovalStatusEnum.REJECTED.value,
                actor_name=rejected_by,
                session=session,
            )
            change_request.rejection_reason = reason
            await session.commit()
            await session.refresh(change_request)
            return change_request

    async def validate_change_request_core(
        self,
        change_request: G2PRegisterChangeRequest,
        session,
        skip_verification: bool = False,
        skip_sequence_check: bool = False,
    ) -> G2PRegisterSection:
        register_section = await self.validate_change_request_section(change_request, session)
        # Validate whether verifications are done
        if not skip_verification:
            await self.validate_change_request_verifications(change_request, session)
        # Ensure there are no earlier change requests for the internal_record_id pending approval
        if not skip_sequence_check:
            await self.validate_change_request_sequence(change_request, session)
        return register_section

    async def validate_change_request_section(self, g2p_register_change_request: G2PRegisterChangeRequest, session) -> G2PRegisterSection:
        register_section: G2PRegisterSection = (
            await session.execute(
                select(G2PRegisterSection).where(
                    G2PRegisterSection.section_id == g2p_register_change_request.section_id
                )
            )
        ).scalar()
        if not register_section:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SECTION_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.SECTION_NOT_FOUND.value[0]
            )
        # Note: internal_record_id is already set during change request creation in construct_change_request
        # Do not generate a new one here during approval
        return register_section

    async def validate_change_request_exists(self, change_request_id: str, session) -> G2PRegisterChangeRequest:
        _logger.info(f"Validating change request exists for ID: {change_request_id}")
        change_request: G2PRegisterChangeRequest = (
            await session.execute(
                select(G2PRegisterChangeRequest).where(
                    G2PRegisterChangeRequest.change_request_id == change_request_id
                )
            )
        ).scalar()
        if not change_request:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_FOUND.value[0]
            )
        if change_request.approval_status != ApprovalStatusEnum.PENDING.value:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_IN_PENDING_STATE.value[1],
                message=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_IN_PENDING_STATE.value[0]
            )
        return change_request

    async def validate_change_request_verifications(self, change_request: G2PRegisterChangeRequest, session) -> None:
        # Count only approved verifications
        approved_verifications_count = (
            await session.execute(
                select(func.count()).select_from(G2PRegisterVerification).where(
                    G2PRegisterVerification.change_request_id == change_request.change_request_id,
                    G2PRegisterVerification.is_approved
                )
            )
        ).scalar_one()
        if approved_verifications_count < (change_request.no_of_verifications_required or 0):
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.VERIFICATIONS_PENDING.value[1],
                message=G2PRegistryErrorCodes.VERIFICATIONS_PENDING.value[0]
            )

    async def _count_earlier_pending_change_requests(
        self, change_request: G2PRegisterChangeRequest, session
    ) -> int:
        return (
            await session.execute(
                select(func.count()).select_from(G2PRegisterChangeRequest).where(
                    G2PRegisterChangeRequest.internal_record_id == change_request.internal_record_id,
                    G2PRegisterChangeRequest.approval_status == ApprovalStatusEnum.PENDING.value,
                    G2PRegisterChangeRequest.created_at < change_request.created_at,
                )
            )
        ).scalar_one()

    async def validate_change_request_sequence(
        self, change_request: G2PRegisterChangeRequest, session
    ) -> None:
        if await self._count_earlier_pending_change_requests(change_request, session) > 0:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REQUEST_VALIDATION_ERROR.value[1],
                message="There are earlier pending change requests for this record",
            )

    async def insert_into_register_history(self, change_request: G2PRegisterChangeRequest, session) -> None:
        history_service = G2PRegisterHistoryService.get_component() or G2PRegisterHistoryService()
        await history_service.insert_into_register_history(change_request, session)

    def _set_change_request_approval_state(
        self,
        change_request: G2PRegisterChangeRequest,
        approval_status: str,
        actor_name: str | None,
        session,
    ) -> None:
        change_request.approval_status = approval_status
        change_request.approved_by = actor_name or "system"
        change_request.approved_at = datetime.now()
        session.add(change_request)

    async def _run_pre_approve_hook(
        self,
        register_id: str,
        change_request: G2PRegisterChangeRequest,
        session,
    ) -> None:
        register_definition = await self.validate_register_definition(register_id, session)
        domain_service = self._get_required_domain_service(register_definition.register_mnemonic)
        await domain_service.pre_approve(change_request, session)

    async def _run_post_approve_hook(
        self,
        register_id: str,
        change_request: G2PRegisterChangeRequest,
        session,
    ) -> None:
        register_definition = await self.validate_register_definition(register_id, session)
        domain_service = self._get_required_domain_service(register_definition.register_mnemonic)
        await domain_service.post_approve(change_request, session)

    def _convert_date_strings_to_objects(self, data_dict: dict, model_class) -> dict:
        """Helper method to convert date, boolean, and numeric strings for SQLAlchemy columns"""
        mapper = inspect(model_class)
        converted_dict = data_dict.copy()
        
        for key, value in converted_dict.items():
            if value is None or key not in mapper.columns:
                continue
            if isinstance(value, (list, tuple)):
                # JSON/JSONB/ARRAY columns natively hold lists — keep them.
                if type(mapper.columns[key].type).__name__.upper() in {"JSON", "JSONB", "ARRAY"}:
                    continue
                converted_dict[key] = ",".join(str(v) for v in value if v is not None)
                continue
            column = mapper.columns[key]
            if isinstance(column.type, SQLDate):
                if isinstance(value, str):
                    val_str = value.strip()
                    if not val_str:
                        converted_dict[key] = None
                        continue
                    parsed = None
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                        try:
                            parsed = datetime.strptime(val_str, fmt).date()
                            break
                        except (ValueError, TypeError):
                            continue
                    if parsed:
                        converted_dict[key] = parsed
                elif isinstance(value, datetime):
                    converted_dict[key] = value.date()
            elif isinstance(column.type, Boolean):
                if isinstance(value, str):
                    if value.lower() in ("true", "t", "yes", "1"):
                        converted_dict[key] = True
                    elif value.lower() in ("false", "f", "no", "0", ""):
                        converted_dict[key] = False
            elif isinstance(column.type, (Numeric, Float)):
                if isinstance(value, str):
                    if not value.strip():
                        converted_dict[key] = None
                    else:
                        try:
                            converted_dict[key] = float(value.replace("%", "").strip())
                        except (TypeError, ValueError):
                            converted_dict[key] = None
            elif isinstance(column.type, Integer):
                if isinstance(value, str):
                    if not value.strip():
                        converted_dict[key] = None
                    else:
                        try:
                            converted_dict[key] = int(value.strip())
                        except (TypeError, ValueError):
                            converted_dict[key] = None
        
        return converted_dict

    async def _check_functional_record_id_generation_required(
        self, register_definition: G2PRegisterDefinition
    ) -> bool:
        return (
            bool(register_definition)
            and register_definition.functional_id_generation_required is True
            and register_definition.register_purpose == RegisterPurposeEnum.REGISTER.value
        )

    async def _handle_functional_record_id_generation(
        self, register_id: str, internal_record_id: str, session
    ) -> None:
        queue_record = G2PFunctionalIdGenerationQueue(
            register_id=register_id,
            internal_record_id=internal_record_id,
        )
        session.add(queue_record)

    async def insert_into_register(self, change_request: G2PRegisterChangeRequest, session) -> None:
        # Resolve register model class dynamically based on register mnemonic
        register_definition: G2PRegisterDefinition = (
            await session.execute(
                select(G2PRegisterDefinition).where(
                    G2PRegisterDefinition.register_id == change_request.section_register_id
                )
            )
        ).scalar()
        module = importlib.import_module(_DOMAIN_MODELS_MODULE)
        register_class_prefix = "G2PRegister"
        implementation_class_name = f"{register_class_prefix}{register_definition.register_mnemonic}"
        register_class = getattr(module, implementation_class_name)

        schema_module = importlib.import_module(_DOMAIN_SCHEMAS_MODULE)
        schema_class_prefix = "G2PRegisterSchema"
        schema_class_name = f"{schema_class_prefix}{register_definition.register_mnemonic}"
        schema_class = getattr(schema_module, schema_class_name)

        # Fetch the payload from the database
        payload_result = await session.execute(
            select(G2PRegisterChangeRequestPayload).where(
                G2PRegisterChangeRequestPayload.change_request_id == change_request.change_request_id
            )
        )
        payload = payload_result.scalar()

        # change_payload is now always a list
        if payload.change_payload:
            for change_payload in payload.change_payload:
                await self._create_or_update_register_record(
                    change_request=change_request,
                    change_payload=change_payload,
                    schema_class=schema_class,
                    register_class=register_class,
                    session=session
                )

    # TODO: _create_or_update_child_register_record

    async def _create_or_update_register_record(self, change_request: G2PRegisterChangeRequest, change_payload: ChangePayload,  schema_class, register_class, session) -> None:
        """Helper method to create or update a register record"""
        if change_payload.get("edit_action") == ChangeActionEnum.NO_CHANGE.value:
            _logger.info(f"No change action for change request '{change_request.change_request_id}', skipping register update.")
            return

        # Serialize change request payload to register schema for validation
        register_schema_instance = schema_class(**(change_payload or {}))
        
        existing = (
            await session.execute(
                select(register_class).where(
                    register_class.internal_record_id == change_payload.get("internal_record_id")
                )
            )
        ).scalar()

        if change_payload.get("edit_action") == ChangeActionEnum.UPDATE.value and existing:
            mapper = inspect(register_class)
            for key, value in register_schema_instance.dict().items():
                # Only update values in change request payload
                if key in change_payload:
                    value = self._normalize_model_value(value, key, mapper)
                    setattr(existing, key, value)
            self._mark_record_as_last_approved(existing, change_request)
        elif change_payload.get("edit_action") == ChangeActionEnum.ADD.value:
            # Build the payload dict excluding None values from schema, then add base fields
            schema_dict = {k: v for k, v in register_schema_instance.dict().items() if v is not None}
            schema_dict["functional_record_id"] = change_payload.get("functional_record_id") 
            schema_dict["created_by"] = change_request.created_by
            schema_dict["created_at"] = change_request.created_at
            schema_dict["last_approved_at"] = change_request.approved_at
            schema_dict["last_approved_by"] = change_request.approved_by or "system"
            
            # Convert date strings to date objects before creating the instance
            schema_dict = self._convert_date_strings_to_objects(schema_dict, register_class)
            
            new_instance = register_class(**schema_dict)
            session.add(new_instance)
        elif change_payload.get("edit_action") == ChangeActionEnum.DELETE.value and existing:
            await session.delete(existing)
        else:
            self._raise_unknown_change_payload_action(change_payload, change_request.change_request_id)

    # Validation methods
    async def validate_register_definition(self, register_id: str, session: AsyncSession) -> G2PRegisterDefinition:
        register_definition: G2PRegisterDefinition = (
            await session.execute(
                select(G2PRegisterDefinition).where(
                    G2PRegisterDefinition.register_id == register_id
                )
            )
        ).scalar()
        if not register_definition:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTER_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.REGISTER_NOT_FOUND.value[0]
            )
        return register_definition

    async def validate_section(self, section_id: str, session: AsyncSession) -> G2PRegisterSection:
        register_section: G2PRegisterSection =(
                await session.execute(
                select(G2PRegisterSection).where(
                    G2PRegisterSection.section_id == section_id
                )
            )
        ).scalar()
        if not register_section:
            raise G2PRegistryException(
                code="SECTION_NOT_FOUND",
                message="Section not found"
            )
        return register_section

    async def validate_tab(self, tab_id: str, session: AsyncSession) -> G2PRegisterUITab:
        register_tab: G2PRegisterUITab = (
            await session.execute(
                select(G2PRegisterUITab).where(
                    G2PRegisterUITab.tab_id == tab_id
                )
            )
        ).scalar()
        if not register_tab:
            raise G2PRegistryException(
                code="TAB_NOT_FOUND",
                message="Tab not found"
            )
        return register_tab

    async def validate_change_request_creation(
        self,
        payload: ChangeRequestRequestPayload,
        register_definition: G2PRegisterDefinition,
        section: G2PRegisterSection,
        section_register_definition: G2PRegisterDefinition,
    ) -> None:
        if register_definition.register_purpose != RegisterPurposeEnum.REGISTER.value:
            raise self._invalid_request("Change request must belong to a register")
        # TODO: remove redundancy if register_id removed from request payload
        if section.register_id != payload.register_id:
            raise self._invalid_request("Section does not belong to the specified register")
        # TODO: remove redundancy if section_register_id removed in request payload
        if section.section_register_id != payload.section_register_id:
            raise self._invalid_request("Section Register does not match the one specified in the payload")
        if not payload.internal_record_id:
            raise self._invalid_request("Change request must have an internal_record_id to identify the subject record")

        section_register_purpose = section_register_definition.register_purpose
        if section_register_purpose == RegisterPurposeEnum.REGISTER.value and section.section_register_id != payload.register_id:
            raise self._invalid_request("Cross-register change requests are not allowed")

        allowed_actions = (
            {ChangeActionEnum.UPDATE.value, ChangeActionEnum.NO_CHANGE.value}
            if section_register_purpose == RegisterPurposeEnum.REGISTER.value
            else {
                ChangeActionEnum.ADD.value,
                ChangeActionEnum.UPDATE.value,
                ChangeActionEnum.DELETE.value,
                ChangeActionEnum.NO_CHANGE.value,
            }
        )
        change_payloads = payload.change_payload or []
        if not change_payloads:
            raise self._invalid_request("change_payload must contain at least one item.")
        for change_payload in change_payloads:
            action = change_payload.edit_action
            if section_register_purpose == RegisterPurposeEnum.REGISTER.value and action == ChangeActionEnum.ADD.value:
                action = ChangeActionEnum.UPDATE.value
                change_payload.edit_action = ChangeActionEnum.UPDATE.value
            if action not in allowed_actions:
                raise self._invalid_request(f"Action {action} is not allowed for this change request.")
            if section_register_purpose == RegisterPurposeEnum.TABLE.value:
                if action in {ChangeActionEnum.UPDATE.value, ChangeActionEnum.DELETE.value} and not change_payload.internal_record_id:
                    raise self._invalid_request(f"internal_record_id is required for table {action} payloads.")
                if action == ChangeActionEnum.ADD.value and not getattr(change_payload, "link_internal_record_id", None):
                    raise self._invalid_request(f"link_internal_record_id is required for table {action} payloads.")

    async def _get_change_request_payload(self, change_request_id: str, session) -> G2PRegisterChangeRequestPayload:
        payload = (
            await session.execute(
                select(G2PRegisterChangeRequestPayload).where(
                    G2PRegisterChangeRequestPayload.change_request_id == change_request_id
                )
            )
        ).scalar()
        if not payload:
            raise self._invalid_request(f"Change request payload not found for {change_request_id}.")
        return payload

    async def _fanout_outgest_for_change_request(self, change_request: G2PRegisterChangeRequest, session) -> None:
        register_definition, register_class, _ = await self._get_register_class_and_schema(
            change_request.register_id, session
        )
        register_row = await self._get_existing_record(
            register_class, change_request.internal_record_id, session
        )
        if not register_row:
            _logger.warning(
                "Skipping outgest fanout — no register row for change_request_id=%s, internal_record_id=%s",
                change_request.change_request_id,
                change_request.internal_record_id,
            )
            return

        await fanout_outgest_rows(
            register_definition,
            register_row,
            session,
            change_request_id=change_request.change_request_id,
            changed_by=change_request.created_by,
            changed_at=change_request.created_at,
            approved_by=change_request.approved_by,
            approved_at=change_request.approved_at,
            changed_by_partner_id=change_request.source_partner_id,
        )

    async def _get_register_class_and_schema(self, register_id: str, session):
        register_definition = await self.validate_register_definition(register_id, session)
        model_module = importlib.import_module(_DOMAIN_MODELS_MODULE)
        schema_module = importlib.import_module(_DOMAIN_SCHEMAS_MODULE)
        register_class = getattr(model_module, f"{_REGISTER_CLASS_PREFIX}{register_definition.register_mnemonic}")
        schema_class = getattr(schema_module, f"{_REGISTER_SCHEMA_CLASS_PREFIX}{register_definition.register_mnemonic}")
        return register_definition, register_class, schema_class

    async def _ensure_subject_record_readable(
        self,
        subject_register_id: str,
        subject_record_id: str,
        policy_mnemonics: list[str] | None,
        session: AsyncSession,
    ) -> None:
        """Raise if the subject register record is missing or blocked by data policy."""
        _, register_class, _ = await self._get_register_class_and_schema(subject_register_id, session)
        await G2PRegisterService.get_component()._ensure_register_record_readable(
            subject_register_id,
            subject_record_id,
            register_class,
            policy_mnemonics,
            session,
        )

    async def _ensure_change_request_readable(
        self,
        change_request_id: str,
        policy_mnemonics: list[str] | None,
        session: AsyncSession,
    ) -> G2PRegisterChangeRequest:
        """Raise if the change request is missing or its subject record is blocked by data policy."""
        change_request = (
            await session.execute(
                select(G2PRegisterChangeRequest).where(
                    G2PRegisterChangeRequest.change_request_id == change_request_id
                )
            )
        ).scalar_one_or_none()
        if change_request is None:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_FOUND.value[0],
            )
        await self._ensure_subject_record_readable(
            change_request.register_id,
            change_request.internal_record_id,
            policy_mnemonics,
            session,
        )
        return change_request

    async def _build_change_request_search_policy_condition(
        self,
        policy_mnemonics: list[str] | None,
        session: AsyncSession,
    ):
        """OR across registers: CR visible when its subject record passes that register's policy."""
        if not policy_mnemonics:
            return None

        register_definitions = (
            await session.execute(select(G2PRegisterDefinition))
        ).scalars().all()
        if not register_definitions:
            return None

        register_service = G2PRegisterService.get_component()
        model_module = importlib.import_module(_DOMAIN_MODELS_MODULE)
        register_clauses = []

        for register_definition in register_definitions:
            try:
                implementation_class = getattr(
                    model_module,
                    f"{_REGISTER_CLASS_PREFIX}{register_definition.register_mnemonic}",
                )
            except AttributeError:
                _logger.warning(
                    "Could not resolve register model for mnemonic %s; excluding from change request search",
                    register_definition.register_mnemonic,
                )
                continue

            policy_condition = await register_service._build_register_policy_condition(
                register_definition.register_id,
                implementation_class,
                policy_mnemonics,
                session,
            )

            if policy_condition is not None:
                readable_subject = exists(
                    select(1).select_from(implementation_class).where(
                        implementation_class.internal_record_id == G2PRegisterChangeRequest.internal_record_id,
                        policy_condition,
                    )
                )
                register_clauses.append(
                    and_(
                        G2PRegisterChangeRequest.register_id == register_definition.register_id,
                        readable_subject,
                    )
                )
            else:
                register_clauses.append(
                    G2PRegisterChangeRequest.register_id == register_definition.register_id
                )

        if not register_clauses:
            return None
        return or_(*register_clauses)

    async def _get_existing_record(self, register_class, internal_record_id: str, session):
        return (
            await session.execute(
                select(register_class).where(register_class.internal_record_id == internal_record_id)
            )
        ).scalar()

    def _normalize_model_value(self, value, key: str, mapper):
        if value is None or key not in mapper.columns:
            return value
        if isinstance(value, (list, tuple)):
            # JSON/JSONB/ARRAY columns natively hold lists — keep them.
            if type(mapper.columns[key].type).__name__.upper() in {"JSON", "JSONB", "ARRAY"}:
                return value
            return ",".join(str(v) for v in value if v is not None)
        column = mapper.columns[key]
        if isinstance(column.type, SQLDate):
            if isinstance(value, str):
                val_str = value.strip()
                if not val_str:
                    return None
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                    try:
                        return datetime.strptime(val_str, fmt).date()
                    except (ValueError, TypeError):
                        continue
                return value
            if isinstance(value, datetime):
                return value.date()
        return value

    def _build_record_data(self, schema_data: dict, change_payload: dict, model_class) -> dict:
        mapper = inspect(model_class)
        record_data = {
            key: value
            for key, value in schema_data.items()
            if value is not None and key in mapper.columns and key != "edit_action"
        }
        for key, value in change_payload.items():
            if key in mapper.columns and key not in record_data and key != "edit_action":
                record_data[key] = value
        return self._convert_date_strings_to_objects(record_data, model_class)

    def _update_existing_record(self, existing, schema_data: dict, change_payload: dict, model_class) -> None:
        mapper = inspect(model_class)
        for key, value in schema_data.items():
            if key not in change_payload or key in {"internal_record_id", "edit_action"} or key not in mapper.columns:
                continue
            value = self._normalize_model_value(value, key, mapper)
            setattr(existing, key, value)

    def _mark_record_as_last_approved(self, record, change_request: G2PRegisterChangeRequest) -> None:
        setattr(record, "last_approved_at", change_request.approved_at)
        setattr(record, "last_approved_by", change_request.approved_by or "system")

    def _set_if_column(self, record, column_name: str, value) -> None:
        if column_name in inspect(record.__class__).columns:
            setattr(record, column_name, value)

    def _set_data_if_column(self, record_data: dict, model_class, column_name: str, value) -> None:
        if column_name in inspect(model_class).columns:
            record_data[column_name] = value

    def _invalid_request(self, message: str) -> G2PRegistryException:
        return G2PRegistryException(
            code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
            message=message,
        )

    def _raise_unknown_change_payload_action(self, change_payload: dict, change_request_id: str) -> None:
        _logger.error(
            "Unknown edit action '%s' for change request '%s'",
            change_payload.get("edit_action"),
            change_request_id,
        )
        raise G2PRegistryException(
            code=G2PRegistryErrorCodes.UNKNOWN_CHANGE_REQUEST_ACTION.value[1],
            message=G2PRegistryErrorCodes.UNKNOWN_CHANGE_REQUEST_ACTION.value[0]
        )

    def _register_row_to_metadata_dict(self, existing_record) -> dict:
        """ORM row → plain dict for merging into change payloads (display metadata only)."""
        mapper = inspect(existing_record.__class__)
        base_fields: set[str] = {"search_text"}
        row_dict: dict = {}
        for column in mapper.columns:
            column_name = column.name
            if column_name in base_fields:
                continue
            value = getattr(existing_record, column_name, None)
            if value is not None and hasattr(value, "isoformat"):
                value = value.isoformat()
            row_dict[column_name] = value
        return row_dict

    async def _payloads_for_display_metadata(
        self,
        session: AsyncSession | None,
        section_register_id: str | None,
        serialized_payloads: list[dict],
    ) -> list[dict]:
        """Merge live register rows into UPDATE payloads so record_name/search_text match UI-sized data."""
        if not session or not section_register_id or not serialized_payloads:
            return serialized_payloads

        merged: list[dict] = []
        register_class = None
        for payload_dict in serialized_payloads:
            if not isinstance(payload_dict, dict):
                merged.append(payload_dict)
                continue
            if payload_dict.get("edit_action") != ChangeActionEnum.UPDATE.value:
                merged.append(payload_dict)
                continue
            internal_record_id = payload_dict.get("internal_record_id")
            if not internal_record_id:
                merged.append(payload_dict)
                continue
            if register_class is None:
                try:
                    _, register_class, _ = await self._get_register_class_and_schema(section_register_id, session)
                except Exception as error:
                    _logger.warning("Could not resolve register class for display metadata merge: %s", error)
                    return serialized_payloads
            existing = await self._get_existing_record(register_class, internal_record_id, session)
            if not existing:
                merged.append(payload_dict)
                continue
            row_dict = self._register_row_to_metadata_dict(existing)
            merged.append({**row_dict, **payload_dict})
        return merged

    async def construct_change_request(
        self,
        change_request_request_payload: ChangeRequestRequestPayload,
        register_section: G2PRegisterSection,
        register_mnemonic: str,
        section_register_mnemonic: str,
        source_partner_id: str = None,
        created_by: str | None = None,
        change_request_source_override: str | None = None,
        session: AsyncSession | None = None,
    ) -> G2PRegisterChangeRequest:
        change_request_id = str(uuid.uuid4())
        internal_record_id: str = change_request_request_payload.internal_record_id

        serialized_payloads: list[dict] = [item.model_dump() for item in change_request_request_payload.change_payload] if change_request_request_payload.change_payload else []

        register_domain_service: G2PRegisterDomainService | None = self._get_domain_service_by_register_mnemonic(section_register_mnemonic)

        display_payloads = await self._payloads_for_display_metadata(
            session,
            change_request_request_payload.section_register_id,
            serialized_payloads,
        )

        constructed_record_name = self._construct_record_name_for_change_request(register_domain_service, display_payloads)

        constructed_search_text = self._construct_search_text_for_change_request(
            register_domain_service,
            display_payloads,
            constructed_record_name,
        )

        # Create the payload object - change_payload is now always a list
        change_request_payload_obj = G2PRegisterChangeRequestPayload(
            change_request_id=change_request_id,
            change_payload=serialized_payloads,
            search_text=constructed_search_text,
        )

        change_request_source = (
            change_request_source_override
            or ChangeRequestSourceEnum.STAFF_PORTAL.value
        )
        no_of_verifications_required = register_section.no_of_verifications_required if register_section else 0
        actor_name = created_by or source_partner_id or "system"

        # Create the change request object
        g2p_register_change_request = G2PRegisterChangeRequest(
            change_request_id=change_request_id,
            record_name=constructed_record_name,
            register_id=change_request_request_payload.register_id,
            tab_id=change_request_request_payload.tab_id,
            internal_record_id=internal_record_id,
            section_id=change_request_request_payload.section_id,
            section_register_id=change_request_request_payload.section_register_id,
            source_partner_id=source_partner_id or "system",
            change_request_source=change_request_source,
            created_by=actor_name,
            created_at=datetime.now(),
            no_of_verifications_required=no_of_verifications_required,
            no_of_verifications_done=0,
            approval_status=ApprovalStatusEnum.PENDING.value,
        )

        # Add both objects to session so they're persisted together
        # The payload will be added when the change request is added
        g2p_register_change_request._payload = change_request_payload_obj
        return g2p_register_change_request

    async def _fetch_change_request_summary_data(
        self,
        session,
        policy_mnemonics: list[str] | None = None,
    ) -> ChangeRequestSummaryData:
        total_count: int = await self._count_all_change_requests(None, session, policy_mnemonics)
        approved_count: int = await self._count_all_change_requests(
            ApprovalStatusEnum.APPROVED.value, session, policy_mnemonics
        )
        pending_count: int = await self._count_all_change_requests(
            ApprovalStatusEnum.PENDING.value, session, policy_mnemonics
        )

        change_request_summary_data: ChangeRequestSummaryData = ChangeRequestSummaryData(
            total_count=total_count,
            approved_count=approved_count,
            pending_count=pending_count
        )

        return change_request_summary_data

    async def _count_all_change_requests(
        self,
        approval_status: str | None,
        session,
        policy_mnemonics: list[str] | None = None,
    ) -> int:
        conditions = []
        if approval_status is not None:
            conditions.append(G2PRegisterChangeRequest.approval_status == approval_status)
        policy_condition = await self._build_change_request_search_policy_condition(
            policy_mnemonics, session
        )
        if policy_condition is not None:
            conditions.append(policy_condition)

        query = select(func.count()).select_from(G2PRegisterChangeRequest)
        if conditions:
            query = query.where(*conditions)
        result = await session.execute(query)
        return result.scalar_one()

    async def _count_change_requests_for_register(self, register_id: str, approval_status: str | None, session) -> int:
        query = select(func.count()).select_from(G2PRegisterChangeRequest).where(
            G2PRegisterChangeRequest.register_id == register_id
        )
        if approval_status is not None:
            query = query.where(G2PRegisterChangeRequest.approval_status == approval_status)

        count: int = (await session.execute(query)).scalar_one()
        return count

    async def search_in_change_request(
        self,
        search_text: str,
        current_page: int = 1,
        page_size: int = 10,
        sort_by: str = None,
        filter_by: dict = None,
        *,
        policy_mnemonics: list[str] | None = None,
    ) -> tuple[list[ChangeRequestSearchResultData], int]:
        """Search in change requests using search_text field with pagination"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            search_results, total_items = await self._search_in_change_request(
                search_text, current_page, page_size, filter_by, session, sort_by, policy_mnemonics
            )
            return search_results, total_items

    async def _search_in_change_request(
        self,
        search_text: str,
        current_page: int,
        page_size: int,
        filter_by: dict,
        session,
        sort_by: str = None,
        policy_mnemonics: list[str] | None = None,
    ) -> tuple[list[ChangeRequestSearchResultData], int]:
        """Helper method to search in change requests with pagination"""
        search_query = f"%{search_text}%"

        search_conditions = [G2PRegisterChangeRequestPayload.search_text.ilike(search_query)]
        policy_condition = await self._build_change_request_search_policy_condition(
            policy_mnemonics, session
        )
        if policy_condition is not None:
            search_conditions.append(policy_condition)

        # Build base query
        base_query = select(G2PRegisterChangeRequest, G2PRegisterChangeRequestPayload).join(
            G2PRegisterChangeRequestPayload,
            G2PRegisterChangeRequest.change_request_id == G2PRegisterChangeRequestPayload.change_request_id
        ).where(*search_conditions)

        # Apply sorting
        if sort_by:
            if ":" in sort_by:
                sort_field, sort_dir = sort_by.split(":")
            else:
                sort_field, sort_dir = sort_by, "desc"

            if hasattr(G2PRegisterChangeRequest, sort_field):
                sort_column = getattr(G2PRegisterChangeRequest, sort_field)
            elif hasattr(G2PRegisterChangeRequestPayload, sort_field):
                sort_column = getattr(G2PRegisterChangeRequestPayload, sort_field)
            else:
                sort_column = G2PRegisterChangeRequest.created_at

            if sort_dir.lower() == "desc":
                base_query = base_query.order_by(sort_column.desc())
            else:
                base_query = base_query.order_by(sort_column.asc())
        else:
            base_query = base_query.order_by(G2PRegisterChangeRequest.created_at.desc())

        # Get total count
        count_result = await session.execute(select(func.count()).select_from(G2PRegisterChangeRequest).join(
            G2PRegisterChangeRequestPayload,
            G2PRegisterChangeRequest.change_request_id == G2PRegisterChangeRequestPayload.change_request_id
        ).where(*search_conditions))
        total_items = count_result.scalar() or 0

        # Apply pagination
        offset = (current_page - 1) * page_size
        query = base_query.offset(offset).limit(page_size)

        result = await session.execute(query)
        search_results = result.all()

        search_results_list: list[ChangeRequestSearchResultData] = []

        # Convert ORM objects to ChangeRequestSearchResultData while still in session context
        for change_request, payload in search_results:
            # Convert datetime objects to strings
            created_at_str = str(change_request.created_at.isoformat()) if change_request.created_at and hasattr(change_request.created_at, 'isoformat') else None
            approved_at_str = str(change_request.approved_at.isoformat()) if change_request.approved_at and hasattr(change_request.approved_at, 'isoformat') else None

            # Get change_payload from the payload object
            change_payload = payload.change_payload if payload else None

            # Get register mnemonic from the register object
            register_metadata = await self._get_register_definition(change_request.register_id, session)
            section_metadata = await self._get_section(change_request.section_id, session)
            tab_metadata = await self._get_tab(change_request.tab_id, session)

            if isinstance(register_metadata, dict):
                register_metadata = G2PRegisterDefinition(**register_metadata)
            if isinstance(section_metadata, dict):
                section_metadata = G2PRegisterSection(**section_metadata)
            if isinstance(tab_metadata, dict):
                tab_metadata = G2PRegisterUITab(**tab_metadata)

            # Create ChangeRequestSearchResultData object
            change_request_search_result: ChangeRequestSearchResultData = ChangeRequestSearchResultData(
                change_request_id=change_request.change_request_id,
                record_name=change_request.record_name,
                register_id=change_request.register_id,
                register_mnemonic=register_metadata.register_mnemonic,
                tab_id=change_request.tab_id,
                tab_label=tab_metadata.tab_label,
                internal_record_id=change_request.internal_record_id,
                section_id=change_request.section_id,
                section_mnemonic=section_metadata.section_mnemonic,
                source_partner_id=change_request.source_partner_id,
                created_by=change_request.created_by,
                created_at=created_at_str,
                no_of_verifications_required=change_request.no_of_verifications_required,
                no_of_verifications_done=change_request.no_of_verifications_done,
                approval_status=change_request.approval_status,
                approved_by=change_request.approved_by,
                approved_at=approved_at_str,
                change_payload=change_payload
            )
            search_results_list.append(change_request_search_result)

        return search_results_list, total_items

    async def get_number_of_pending_change_requests(self, subject_register_id: str, subject_record_id: str, tab_id: str) -> NumberOfPendingChangeRequestsData:
        """Get the number of pending change requests for a given register, internal_record_id and tab_id"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self.validate_register_definition(subject_register_id, session)

            # Count pending change requests for the given internal_record_id and tab_id
            count_result = await session.execute(
                select(func.count()).select_from(G2PRegisterChangeRequest).where(
                    (G2PRegisterChangeRequest.register_id == subject_register_id) &
                    (G2PRegisterChangeRequest.internal_record_id == subject_record_id) &
                    (G2PRegisterChangeRequest.tab_id == tab_id) &
                    (G2PRegisterChangeRequest.approval_status == ApprovalStatusEnum.PENDING.value)
                )
            )
            number_of_pending_change_requests = count_result.scalar_one()

            return NumberOfPendingChangeRequestsData(
                subject_register_id=subject_register_id,
                subject_record_id=subject_record_id,
                tab_id=tab_id,
                number_of_pending_change_requests=number_of_pending_change_requests
            )

    async def get_number_of_cross_register_changes(self, subject_register_id: str, subject_record_id: str) -> NumberOfCrossRegisterChangesData:
        """Get the number of cross-register pending change requests by searching subject_record_id in search_text of G2PRegisterChangeRequestPayload"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self.validate_register_definition(subject_register_id, session)

            # Count pending change requests where search_text contains subject_record_id
            # Join G2PRegisterChangeRequest with G2PRegisterChangeRequestPayload and search in search_text
            count_result = await session.execute(
                select(func.count()).select_from(G2PRegisterChangeRequest).join(
                    G2PRegisterChangeRequestPayload,
                    G2PRegisterChangeRequest.change_request_id == G2PRegisterChangeRequestPayload.change_request_id
                ).where(
                    (G2PRegisterChangeRequest.approval_status == ApprovalStatusEnum.PENDING.value) &
                    (G2PRegisterChangeRequestPayload.search_text.ilike(f"%{subject_record_id}%"))
                )
            )
            number_of_cross_register_changes = count_result.scalar_one()

            return NumberOfCrossRegisterChangesData(
                subject_register_id=subject_register_id,
                subject_record_id=subject_record_id,
                number_of_cross_register_changes=number_of_cross_register_changes
            )

    async def get_cross_register_changes(self, subject_register_id: str, subject_record_id: str) -> list[CrossRegisterChangeRequestData]:
        """Get the list of cross-register pending change requests by searching subject_record_id in search_text of G2PRegisterChangeRequestPayload"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self.validate_register_definition(subject_register_id, session)

            # Fetch pending change requests where search_text contains subject_record_id
            # Join G2PRegisterChangeRequest with G2PRegisterChangeRequestPayload, G2PRegisterDefinition, and G2PRegisterUITab
            result = await session.execute(
                select(
                    G2PRegisterChangeRequest,
                    G2PRegisterDefinition.register_mnemonic,
                    G2PRegisterUITab.tab_label
                ).join(
                    G2PRegisterChangeRequestPayload,
                    G2PRegisterChangeRequest.change_request_id == G2PRegisterChangeRequestPayload.change_request_id
                ).join(
                    G2PRegisterDefinition,
                    G2PRegisterChangeRequest.register_id == G2PRegisterDefinition.register_id
                ).join(
                    G2PRegisterUITab,
                    G2PRegisterChangeRequest.tab_id == G2PRegisterUITab.tab_id
                ).where(
                    (G2PRegisterChangeRequest.approval_status == ApprovalStatusEnum.PENDING.value) &
                    (G2PRegisterChangeRequestPayload.search_text.ilike(f"%{subject_record_id}%"))
                ).order_by(G2PRegisterChangeRequest.created_at.desc())
            )
            rows = result.all()

            cross_register_changes: list[CrossRegisterChangeRequestData] = []
            for row in rows:
                change_request = row[0]
                register_mnemonic = row[1]
                tab_label = row[2]
                cross_register_changes.append(CrossRegisterChangeRequestData(
                    change_request_id=change_request.change_request_id,
                    record_name=change_request.record_name,
                    register_id=change_request.register_id,
                    register_mnemonic=register_mnemonic,
                    tab_id=change_request.tab_id,
                    tab_label=tab_label,
                    internal_record_id=change_request.internal_record_id,
                    section_id=change_request.section_id,
                    source_partner_id=change_request.source_partner_id,
                    created_by=change_request.created_by,
                    created_at=change_request.created_at.isoformat() if change_request.created_at else None,
                    no_of_verifications_required=change_request.no_of_verifications_required,
                    no_of_verifications_done=change_request.no_of_verifications_done,
                    approval_status=change_request.approval_status,
                    approved_by=change_request.approved_by,
                    approved_at=change_request.approved_at.isoformat() if change_request.approved_at else None
                ))

            return cross_register_changes

    async def _fetch_change_requests(self, subject_register_id: str, subject_record_id: str, tab_id: str, current_page: int, page_size: int, sort_by: str, filter_by: dict, session) -> tuple[list[ChangeRequestData], int]:
        """Helper method to fetch all change requests for a specific internal record and tab with pagination"""
        # Build base query
        base_query = select(G2PRegisterChangeRequest, G2PRegisterChangeRequestPayload).join(
            G2PRegisterChangeRequestPayload,
            G2PRegisterChangeRequest.change_request_id == G2PRegisterChangeRequestPayload.change_request_id
        ).where(
            (G2PRegisterChangeRequest.register_id == subject_register_id) &
            (G2PRegisterChangeRequest.internal_record_id == subject_record_id) &
            (G2PRegisterChangeRequest.tab_id == tab_id)
        ).order_by(G2PRegisterChangeRequest.created_at.desc())

        # Get total count
        count_result = await session.execute(select(func.count()).select_from(G2PRegisterChangeRequest).where(
            (G2PRegisterChangeRequest.register_id == subject_register_id) &
            (G2PRegisterChangeRequest.internal_record_id == subject_record_id) &
            (G2PRegisterChangeRequest.tab_id == tab_id)
        ))
        total_items = count_result.scalar() or 0

        # Apply pagination
        offset = (current_page - 1) * page_size
        query = base_query.offset(offset).limit(page_size)

        result = await session.execute(query)
        change_requests = result.all()

        change_requests_list: list[ChangeRequestData] = []

        # Batch-fetch attached documents for all change requests in the page
        from .g2p_document_service import G2PDocumentService

        cr_documents_map = await G2PDocumentService.get_component().get_change_request_documents_map(
            session,
            [change_request.change_request_id for change_request, _ in change_requests],
        )

        # Convert ORM objects to ChangeRequestData while still in session context
        for change_request, payload in change_requests:
            # Convert datetime objects to strings
            created_at_str = str(change_request.created_at.isoformat()) if change_request.created_at and hasattr(change_request.created_at, 'isoformat') else None
            approved_at_str = str(change_request.approved_at.isoformat()) if change_request.approved_at and hasattr(change_request.approved_at, 'isoformat') else None

            # Get change_payload from the payload object
            change_payload = payload.change_payload if payload else None

            # Create ChangeRequestData object
            # Note: current_register_data is not populated in list view for performance reasons
            change_request_data: ChangeRequestData = ChangeRequestData(
                change_request_id=change_request.change_request_id,
                record_name=change_request.record_name,
                register_id=change_request.register_id,
                tab_id=change_request.tab_id,
                internal_record_id=change_request.internal_record_id,
                section_id=change_request.section_id,
                section_mnemonic=change_request.section_mnemonic,
                section_register_id=change_request.section_register_id,
                source_partner_id=change_request.source_partner_id,
                created_by=change_request.created_by,
                created_at=created_at_str,
                no_of_verifications_required=change_request.no_of_verifications_required,
                no_of_verifications_done=change_request.no_of_verifications_done,
                approval_status=change_request.approval_status,
                approved_by=change_request.approved_by,
                approved_at=approved_at_str,
                change_payload=change_payload,
                current_register_data=None,
                documents=cr_documents_map.get(change_request.change_request_id, [])
            )
            change_requests_list.append(change_request_data)

        return change_requests_list, total_items

    async def _fetch_change_request(self, change_request_id: str, session) -> ChangeRequestData:
        """Helper method to fetch a single change request by ID"""
        # Join G2PRegisterChangeRequest with G2PRegisterChangeRequestPayload
        result = await session.execute(
            select(G2PRegisterChangeRequest, G2PRegisterChangeRequestPayload).join(
                G2PRegisterChangeRequestPayload,
                G2PRegisterChangeRequest.change_request_id == G2PRegisterChangeRequestPayload.change_request_id
            ).where(
                G2PRegisterChangeRequest.change_request_id == change_request_id
            )
        )
        change_request_row = result.first()

        if not change_request_row:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.CHANGE_REQUEST_NOT_FOUND.value[0]
            )

        change_request, change_request_payload = change_request_row

        if change_request.awe_request_id:
            await reconcile_artifact_status_summary(
                session,
                artifact_type=REGISTRY_CHANGE_REQUEST_ARTIFACT,
                artifact_id=change_request.change_request_id,
            )

        # Convert datetime objects to strings
        created_at_str = str(change_request.created_at.isoformat()) if change_request.created_at and hasattr(change_request.created_at, 'isoformat') else None
        approved_at_str = str(change_request.approved_at.isoformat()) if change_request.approved_at and hasattr(change_request.approved_at, 'isoformat') else None

        # Get change_payload from the payload object
        change_payloads: list[ChangePayload] = change_request_payload.change_payload if change_request_payload else None

        # Fetch existing register data (old values) for current_register_data
        current_register_data = None
        current_register_data_list = []
        try:
            # Get the register definition to find the implementation class
            register_definition: G2PRegisterDefinition = (
                await session.execute(
                    select(G2PRegisterDefinition).where(
                        G2PRegisterDefinition.register_id == change_request.section_register_id
                    )
                )
            ).scalar()

            if register_definition:
                # Get the implementation class for this register
                try:
                    module = importlib.import_module(_DOMAIN_MODELS_MODULE)

                    # If approval_status is APPROVED, fetch previous history (before this change was applied)
                    if change_request.approval_status == ApprovalStatusEnum.APPROVED.value:
                        # Fetch from history table - get the previous record before this change request
                        history_class_name: str = f"{_REGISTER_HISTORY_CLASS_PREFIX}{register_definition.register_mnemonic}"
                        history_class = getattr(module, history_class_name)

                        # Get internal_record_ids from change_payloads
                        internal_record_ids = [
                            cp.get("internal_record_id") for cp in change_payloads
                            if cp.get("internal_record_id")
                        ]

                        # Base history fields to exclude from current_register_data
                        history_base_fields: set = {
                            'history_record_id', 'change_request_id', 'tab_id', 'section_id',
                            'submission_id', 'change_request_source', 'is_primary_section',
                            'created_by', 'created_at', 'approved_by', 'approved_at', 'search_text'
                        }

                        # For each internal_record_id, fetch the previous history record
                        for internal_record_id in internal_record_ids:
                            previous_history = (
                                await session.execute(
                                    select(history_class).where(
                                        history_class.internal_record_id == internal_record_id,
                                        history_class.approved_at < change_request.approved_at
                                    ).order_by(history_class.approved_at.desc()).limit(1)
                                )
                            ).scalar()

                            if previous_history:
                                # Convert ORM object to dict for current_register_data
                                mapper = inspect(previous_history.__class__)
                                current_register_data = {}

                                for column in mapper.columns:
                                    column_name: str = column.name
                                    if column_name not in history_base_fields:
                                        value = getattr(previous_history, column_name, None)

                                        # Convert datetime objects to strings
                                        if value is not None and hasattr(value, 'isoformat'):
                                            value = value.isoformat()

                                        current_register_data[column_name] = value
                                current_register_data_list.append(current_register_data)
                    else:
                        # For PENDING/REJECTED, fetch from live register table
                        implementation_class_name: str = f"{_REGISTER_CLASS_PREFIX}{register_definition.register_mnemonic}"
                        implementation_class = getattr(module, implementation_class_name)

                        internal_record_ids = [change_payload.get("internal_record_id") for change_payload in change_payloads if change_payload.get("internal_record_id")]
                        # Fetch the existing record by internal_record_id
                        existing_records = (
                            await session.execute(
                                select(implementation_class).where(
                                    implementation_class.internal_record_id.in_(internal_record_ids)
                                )
                            )
                        ).scalars().all()

                        for existing_record in existing_records:
                            if existing_record:
                                # Convert ORM object to dict for current_register_data
                                mapper = inspect(existing_record.__class__)
                                current_register_data = {}

                                # Base fields to exclude from current_register_data
                                base_fields: set = {'search_text'}

                                for column in mapper.columns:
                                    column_name: str = column.name
                                    if column_name not in base_fields:
                                        value = getattr(existing_record, column_name, None)

                                        # Convert datetime objects to strings
                                        if value is not None and hasattr(value, 'isoformat'):
                                            value = value.isoformat()

                                        current_register_data[column_name] = value
                                current_register_data_list.append(current_register_data)

                except (AttributeError, ModuleNotFoundError) as error:
                    _logger.warning(f"Could not fetch old register data for change request {change_request_id}: {str(error)}")
        except Exception as error:
            _logger.warning(f"Error fetching old register data for change request {change_request_id}: {str(error)}")

        register_section: G2PRegisterSection = (
            await session.execute(
                select(G2PRegisterSection).where(
                    G2PRegisterSection.section_id == change_request.section_id
                )
            )
        ).scalar()

        from .g2p_document_service import G2PDocumentService

        document_service = G2PDocumentService.get_component()
        records = [*(change_payloads or []), *current_register_data_list]
        record_image_urls = await document_service.get_document_urls(
            session,
            [r.get("record_image_document_id") for r in records],
        )
        for record in records:
            document_id = record.get("record_image_document_id")
            if document_id:
                record["record_image_url"] = record_image_urls.get(document_id)

        # Create ChangeRequestData object
        change_request_data: ChangeRequestData = ChangeRequestData(
            change_request_id=change_request.change_request_id,
            record_name=change_request.record_name,
            register_id=change_request.register_id,
            tab_id=change_request.tab_id,
            internal_record_id=change_request.internal_record_id,
            section_id=change_request.section_id,
            section_mnemonic=register_section.section_mnemonic,
            is_list=register_section.is_list,
            section_register_id=change_request.section_register_id,
            source_partner_id=change_request.source_partner_id,
            created_by=change_request.created_by,
            created_at=created_at_str,
            no_of_verifications_required=change_request.no_of_verifications_required,
            no_of_verifications_done=change_request.no_of_verifications_done,
            approval_status=change_request.approval_status,
            approved_by=change_request.approved_by,
            approved_at=approved_at_str,
            awe_request_id=change_request.awe_request_id,
            awe_request_status_summary=change_request.awe_request_status_summary,
            change_payload=change_payloads,
            current_register_data=current_register_data_list,
            documents=(
                await document_service.get_change_request_documents_with_session(
                    session, change_request.change_request_id
                )
            ).documents,
        )

        return change_request_data

    async def _fetch_change_requests_flattened(self, subject_register_id: str, subject_record_id: str, tab_id: str, current_page: int, page_size: int, sort_by: str, filter_by: dict, session) -> tuple[list[ChangeRequestFlattenedData], int]:
        """Helper method to fetch all change requests with flattened change_payload fields"""
        # Build base query
        base_query = select(G2PRegisterChangeRequest, G2PRegisterChangeRequestPayload).join(
            G2PRegisterChangeRequestPayload,
            G2PRegisterChangeRequest.change_request_id == G2PRegisterChangeRequestPayload.change_request_id
        ).where(
            (G2PRegisterChangeRequest.register_id == subject_register_id) &
            (G2PRegisterChangeRequest.internal_record_id == subject_record_id) &
            (G2PRegisterChangeRequest.tab_id == tab_id)
        ).order_by(G2PRegisterChangeRequest.created_at.desc())

        # Get total count
        count_result = await session.execute(select(func.count()).select_from(G2PRegisterChangeRequest).where(
            (G2PRegisterChangeRequest.register_id == subject_register_id) &
            (G2PRegisterChangeRequest.internal_record_id == subject_record_id) &
            (G2PRegisterChangeRequest.tab_id == tab_id)
        ))
        total_items = count_result.scalar() or 0

        # Apply pagination
        offset = (current_page - 1) * page_size
        query = base_query.offset(offset).limit(page_size)

        result = await session.execute(query)
        change_requests = result.all()

        change_requests_list: list[ChangeRequestFlattenedData] = []

        # Convert ORM objects to ChangeRequestFlattenedData with flattened fields
        for change_request, payload in change_requests:
            # Convert datetime objects to strings
            created_at_str = str(change_request.created_at.isoformat()) if change_request.created_at and hasattr(change_request.created_at, 'isoformat') else None
            approved_at_str = str(change_request.approved_at.isoformat()) if change_request.approved_at and hasattr(change_request.approved_at, 'isoformat') else None

            # Get change_payload from the payload object
            change_payload = payload.change_payload if payload else {}

            # Get section to retrieve section_mnemonic
            register_section: G2PRegisterSection = (
                await session.execute(
                    select(G2PRegisterSection).where(
                        G2PRegisterSection.section_id == change_request.section_id
                    )
                )
            ).scalar()

            # Create base ChangeRequestFlattenedData object
            change_request_data_dict = {
                "change_request_id": change_request.change_request_id,
                "record_name": change_request.record_name,
                "register_id": change_request.register_id,
                "tab_id": change_request.tab_id,
                "internal_record_id": change_request.internal_record_id,
                "section_id": change_request.section_id,
                "section_mnemonic": register_section.section_mnemonic,
                "source_partner_id": change_request.source_partner_id,
                "created_by": change_request.created_by,
                "created_at": created_at_str,
                "no_of_verifications_required": change_request.no_of_verifications_required,
                "no_of_verifications_done": change_request.no_of_verifications_done,
                "approval_status": change_request.approval_status,
                "approved_by": change_request.approved_by,
                "approved_at": approved_at_str,
            }

            # Flatten change_payload fields into the main object
            if change_payload and isinstance(change_payload, dict):
                # Exclude internal_record_id from flattening as it's already in the main object
                for key, value in change_payload.items():
                    if key != "internal_record_id":
                        change_request_data_dict[key] = value

            # Create ChangeRequestFlattenedData object with flattened fields
            change_request_data: ChangeRequestFlattenedData = ChangeRequestFlattenedData(**change_request_data_dict)
            change_requests_list.append(change_request_data)

        return change_requests_list, total_items

    async def get_verifications_for_change_request(self, change_request_id: str, current_page: int = 1, page_size: int = 10, sort_by: str = None, filter_by: dict = None) -> tuple[list[VerificationData], int]:
        """Deprecated delegator. Use G2PRegisterVerificationService directly."""
        from .g2p_verification_service import G2PRegisterVerificationService

        verification_service = G2PRegisterVerificationService.get_component()
        return await verification_service.get_verifications(
            change_request_id=change_request_id,
            submission_id=None,
            current_page=current_page,
            page_size=page_size,
            sort_by=sort_by,
            filter_by=filter_by,
        )

    async def add_verification_for_change_request(
        self,
        payload: AddVerificationPayload
    ) -> VerificationData:
        """Deprecated delegator. Use G2PRegisterVerificationService directly."""
        from .g2p_verification_service import G2PRegisterVerificationService

        verification_service = G2PRegisterVerificationService.get_component()
        return await verification_service.add_verification(payload)

    async def _handle_documents_on_approval(
        self,
        change_request: G2PRegisterChangeRequest,
        section: G2PRegisterSection,
        session
    ) -> None:
        """
        Promote change-request documents to live section documents.

        Key live docs by the section register row ID(s) from change_payload
        (e.g. household / child), not the subject CR.internal_record_id
        (e.g. individual), so get_tab_records can resolve them.
        """
        docs_result = await session.execute(
            select(G2PRegisterChangeRequestDocument).where(
                G2PRegisterChangeRequestDocument.change_request_id == change_request.change_request_id
            )
        )
        change_request_documents = docs_result.scalars().all()

        if not change_request_documents:
            _logger.info(f"No documents to process for change request {change_request.change_request_id}")
            return

        payload = await self._get_change_request_payload(change_request.change_request_id, session)
        skip_actions = {
            ChangeActionEnum.DELETE.value,
            ChangeActionEnum.NO_CHANGE.value,
        }
        target_record_ids: list[str] = []
        for change_payload in payload.change_payload or []:
            action = change_payload.get("edit_action", ChangeActionEnum.ADD.value)
            if action in skip_actions:
                continue
            record_id = change_payload.get("internal_record_id")
            if record_id and record_id not in target_record_ids:
                target_record_ids.append(record_id)

        if not target_record_ids:
            target_record_ids = [change_request.internal_record_id]

        section_id = section.section_id
        for cr_doc in change_request_documents:
            doc_section_id = cr_doc.section_id or section_id
            for record_id in target_record_ids:
                session.add(
                    G2PRegisterDocumentHistory(
                        internal_record_id=record_id,
                        section_id=doc_section_id,
                        document_id=cr_doc.document_id,
                        label=cr_doc.label,
                        change_request_id=change_request.change_request_id,
                        change_request_source=change_request.change_request_source,
                        created_by=change_request.created_by,
                        created_at=change_request.created_at,
                        approved_by=change_request.approved_by or "system",
                        approved_at=change_request.approved_at or datetime.now(),
                    )
                )

                existing_doc = (
                    await session.execute(
                        select(G2PRegisterSectionDocument).where(
                            (G2PRegisterSectionDocument.internal_record_id == record_id)
                            & (G2PRegisterSectionDocument.document_id == cr_doc.document_id)
                        )
                    )
                ).scalar()

                if existing_doc:
                    existing_doc.section_id = doc_section_id
                    existing_doc.label = cr_doc.label
                    _logger.info(
                        f"Document {cr_doc.document_id} already linked to record {record_id}"
                    )
                else:
                    session.add(
                        G2PRegisterSectionDocument(
                            internal_record_id=record_id,
                            document_id=cr_doc.document_id,
                            section_id=doc_section_id,
                            label=cr_doc.label,
                        )
                    )
                    _logger.info(
                        f"Linked document {cr_doc.document_id} to record {record_id}"
                    )
    # =============================================================================
    # Registry Configuration Methods
    # =============================================================================

    @staticmethod
    def _records_from_change_request_payload(payload: ChangeRequestRequestPayload) -> list[dict]:
        return [
            item.model_dump() if hasattr(item, "model_dump") else dict(item)
            for item in (payload.change_payload or [])
        ]

    async def _validate_domain_attributes(
        self,
        records: list[dict],
        section_register_mnemonic: str,
        session=None,
    ) -> None:
        domain_service = self._get_domain_service_by_register_mnemonic(section_register_mnemonic)
        if domain_service:
            await domain_service.validate_domain_attributes(records, session=session)

    def _get_required_domain_service(self, register_mnemonic: str) -> G2PRegisterDomainService:
        domain_service = self._get_domain_service_by_register_mnemonic(register_mnemonic)
        if not domain_service:
            raise Exception(f"No domain service found for register mnemonic '{register_mnemonic}'")
        return domain_service

    def _get_domain_service_by_register_mnemonic(self, register_mnemonic: str) -> G2PRegisterDomainService | None:
        """Resolve the domain service for a given register mnemonic via the domain factory."""
        try:
            module = importlib.import_module(_DOMAIN_FACTORY_MODULE)
            domain_factory_class = getattr(module, _DOMAIN_FACTORY_CLASS)
            g2p_registry_domain_factory = domain_factory_class.get_component()
            if not g2p_registry_domain_factory:
                g2p_registry_domain_factory = domain_factory_class()
            return g2p_registry_domain_factory.get_domain_service(register_mnemonic)
        except Exception as error:
            _logger.warning(
                f"Unable to resolve domain service for register mnemonic '{register_mnemonic}': {error}"
            )
            return None

    def _construct_record_name_for_change_request(
        self,
        register_domain_service: G2PRegisterDomainService | None,
        payload: list[dict],
    ) -> str | None:
        """Construct the record_name for a change request using the domain service."""
        if not register_domain_service:
            return None
        for payload_dict in payload:
            if not isinstance(payload_dict, dict):
                continue
            try:
                record_name = register_domain_service.construct_record_name(payload_dict)
                if record_name:
                    return record_name
            except NotImplementedError:
                _logger.info("construct_record_name not implemented for change request domain service.")
                return None
            except Exception as error:
                _logger.warning(f"Could not construct change request record_name: {error}")
                return None
        return None

    def _construct_search_text_for_change_request(
        self,
        register_domain_service: G2PRegisterDomainService | None,
        serialized_payloads: list[dict],
        *args,
    ) -> str:
        """Construct the search_text for a change request payload using the domain service.

        Mirrors the pattern used in G2PIntakeFormService._construct_search_text.
        Extra positional args (e.g. record_name, change_request_id) are forwarded
        to the domain service's construct_search_text as the `extra` list.
        """
        if not serialized_payloads or not register_domain_service:
            return ""
        search_tokens: list[str] = []
        for payload_dict in serialized_payloads:
            if not isinstance(payload_dict, dict):
                continue
            try:
                search_text = register_domain_service.construct_search_text(payload_dict, list(args))
                if search_text:
                    search_tokens.append(search_text.strip())
            except NotImplementedError:
                _logger.info("construct_search_text not implemented for change request domain service.")
                return ""
            except Exception as error:
                _logger.warning(f"Could not construct change request search_text: {error}")
        return " ".join(search_tokens).strip()
