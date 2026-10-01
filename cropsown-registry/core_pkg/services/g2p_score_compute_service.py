import importlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, delete, desc, func, inspect as sqlalchemy_inspect, select
from sqlalchemy.orm import Session

from openg2p_fastapi_common.service import BaseService

from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..models import (
    ChangeActionEnum,
    G2PRegisterChangeRequest,
    G2PRegisterChangeRequestPayload,
    G2PRegisterDefinition,
    G2PRegisterScore,
    G2PRegisterScoreContributingAttribute,
    G2PRegisterScoreDefinition,
    G2PRegisterScoreHistory,
    G2PScoreComputeQueue,
    RegisterPurposeEnum,
)
from ..schemas import (
    ScoreContributingAttributeData,
    ScoreContributingAttributeInput,
    ScoreDefinitionData,
    ScoreData,
    ScoreHistoryData,
)
from ..models.g2p_score_compute_queue import ProcessStatusEnum as QueueProcessStatus

_logger = logging.getLogger("g2p-score-compute-service")

# Metadata keys that appear in change payloads but are not field paths.
_CHANGE_PAYLOAD_METADATA_KEYS = frozenset(
    {
        "edit_action",
        "internal_record_id",
        "link_internal_record_id",
    }
)


class G2PScoreComputeService(BaseService):
    """
    Core infrastructure for score computation.

    Responsibilities:
    - Score-definition CRUD (create / read / update / delete).
    - Populating ``G2PScoreComputeQueue`` when a Change Request or an Intake
      submission is approved.
    """

    # ------------------------------------------------------------------ #
    # Score-compute-queue triggers                                       #
    # ------------------------------------------------------------------ #

    async def enqueue_score_computations_for_change_request(
        self,
        change_request: G2PRegisterChangeRequest,
        session: Session,
    ) -> None:
        """
        Upsert PENDING queue rows triggered by an approved Change Request.

        A row is upserted only when ALL of the following hold:
        1. The CR targets the same register mnemonic as the subject record
           (not a child / section register).
        2. The change payload touches at least one contributing-attribute path.
        3. The touched contributing values differ from the last COMPLETED
           snapshot for that record + score-type pair (prevents spurious
           re-computation when a fat payload resends unchanged fields).
        """
        _logger.info(
            "enqueue_score_computations_for_change_request called — "
            "change_request_id=%s section_register_id=%s",
            change_request.change_request_id,
            change_request.section_register_id,
        )

        subject_register = await session.get(
            G2PRegisterDefinition, change_request.register_id
        )
        section_register = await session.get(
            G2PRegisterDefinition, change_request.section_register_id
        )

        if not self._registers_share_mnemonic(subject_register, section_register):
            _logger.info(
                "Skipping score queue for CR %s: section is not on the subject register "
                "(subject mnemonic=%s, section mnemonic=%s)",
                change_request.change_request_id,
                getattr(subject_register, "register_mnemonic", None),
                getattr(section_register, "register_mnemonic", None),
            )
            return

        touched_leaf_paths = await self._resolve_touched_leaf_paths_for_change_request(
            change_request.change_request_id, session
        )
        if not touched_leaf_paths:
            _logger.info(
                "Skipping score queue for CR %s: no non-NO_CHANGE field paths in change payload",
                change_request.change_request_id,
            )
            return

        candidate_rows = await self._build_contributing_snapshots_for_change_request(
            change_request, session
        )

        for score_definition, register_id, contributing_values in candidate_rows:
            contributing_paths = list(contributing_values.keys())

            if not self._any_contributing_path_overlaps_touched_leaves(
                contributing_paths, touched_leaf_paths
            ):
                _logger.info(
                    "Skipping score queue for CR %s: payload does not touch contributing "
                    "attributes (score_type=%s)",
                    change_request.change_request_id,
                    score_definition.score_type,
                )
                continue

            paths_that_were_touched = [
                p
                for p in contributing_paths
                if self._contributing_path_overlaps_touched_leaves(p, touched_leaf_paths)
            ]
            if not any(
                self._value_is_present(contributing_values[p])
                for p in paths_that_were_touched
            ):
                _logger.info(
                    "Skipping score queue for CR %s: touched contributing paths all have "
                    "absent values (score_type=%s)",
                    change_request.change_request_id,
                    score_definition.score_type,
                )
                continue

            last_completed_snapshot = await self._fetch_latest_completed_snapshot(
                session,
                link_internal_record_id=change_request.internal_record_id,
                score_type=score_definition.score_type,
            )
            if last_completed_snapshot is not None and self._touched_values_match_snapshot(
                last_completed_snapshot, contributing_values, paths_that_were_touched
            ):
                _logger.info(
                    "Skipping score queue for CR %s: touched contributing values match last "
                    "completed compute (score_type=%s)",
                    change_request.change_request_id,
                    score_definition.score_type,
                )
                continue

            await self._upsert_pending_queue_row(
                session=session,
                register_id=register_id,
                link_internal_record_id=change_request.internal_record_id,
                change_request_id=change_request.change_request_id or "",
                submission_id="",
                score_definition_id=score_definition.score_definition_id,
                score_type=score_definition.score_type,
                contributing_attribute_values=contributing_values,
            )

    async def enqueue_score_computations_for_intake_submission(
        self,
        submission_id: str,
        section_register_ids: List[str],
        session: Session,
    ) -> None:
        """
        Upsert PENDING queue rows after an intake submission is approved.

        A row is upserted only when at least one contributing attribute on the
        saved register row resolves to a present (non-empty) value.

        Args:
            submission_id: The approved intake submission ID.
            section_register_ids: Register-definition IDs from the intake submission.
            session: Active database session.
        """
        _logger.info(
            "enqueue_score_computations_for_intake_submission called — "
            "submission_id=%s section_register_ids=%s",
            submission_id,
            section_register_ids,
        )

        for section_register_id in section_register_ids:
            register_definition = await session.get(
                G2PRegisterDefinition, section_register_id
            )
            if not register_definition:
                _logger.warning(
                    "Register definition '%s' not found, skipping", section_register_id
                )
                continue

            if register_definition.register_purpose != RegisterPurposeEnum.REGISTER.value:
                _logger.info(
                    "Register '%s' purpose is not REGISTER, skipping", section_register_id
                )
                continue

            enabled_score_definitions = (
                await session.execute(
                    select(G2PRegisterScoreDefinition).where(
                        G2PRegisterScoreDefinition.register_mnemonic
                        == register_definition.register_mnemonic,
                        G2PRegisterScoreDefinition.is_enabled.is_(True),
                    )
                )
            ).scalars().all()

            if not enabled_score_definitions:
                _logger.info(
                    "No enabled score definitions for register '%s', skipping",
                    section_register_id,
                )
                continue

            register_model_class = self._load_domain_model(
                register_mnemonic=register_definition.register_mnemonic,
                class_prefix="G2PRegister",
            )
            intake_model_class = self._load_domain_model(
                register_mnemonic=register_definition.register_mnemonic,
                class_prefix="G2PIntakeForm",
            )
            if register_model_class is None or intake_model_class is None:
                continue

            intake_rows = (
                await session.execute(
                    select(intake_model_class).where(
                        intake_model_class.submission_id == submission_id
                    )
                )
            ).scalars().all()

            if not intake_rows:
                _logger.info(
                    "No intake rows found for submission '%s' in register '%s', skipping",
                    submission_id,
                    section_register_id,
                )
                continue

            for intake_row in intake_rows:
                await self._enqueue_for_intake_record(
                    session=session,
                    intake_row=intake_row,
                    register_definition=register_definition,
                    register_model_class=register_model_class,
                    enabled_score_definitions=enabled_score_definitions,
                    submission_id=submission_id,
                )

    async def _enqueue_for_intake_record(
        self,
        session: Session,
        intake_row: Any,
        register_definition: G2PRegisterDefinition,
        register_model_class: Any,
        enabled_score_definitions: List[G2PRegisterScoreDefinition],
        submission_id: str,
    ) -> None:
        """Evaluate and enqueue a single intake record against all enabled score definitions."""
        link_internal_record_id = intake_row.internal_record_id
        if not link_internal_record_id:
            _logger.warning(
                "No internal_record_id on intake row for register '%s', skipping",
                register_definition.register_id,
            )
            return

        register_record = await session.get(register_model_class, link_internal_record_id)
        if not register_record:
            _logger.warning(
                "Register record '%s' not found for register '%s', skipping",
                link_internal_record_id,
                register_definition.register_id,
            )
            return

        record_dict = self._orm_instance_to_dict(register_record)

        for score_definition in enabled_score_definitions:
            contributing_paths = await self._fetch_contributing_attribute_paths(
                session,
                register_mnemonic=score_definition.register_mnemonic,
                score_type=score_definition.score_type,
            )
            if not contributing_paths:
                continue

            contributing_values: Dict[str, Any] = {
                path: self._resolve_dot_path(record_dict, path)
                for path in contributing_paths
            }

            if not self._any_contributing_value_is_present(contributing_paths, record_dict):
                _logger.info(
                    "Skipping score queue for submission %s: no present contributing values "
                    "(link_internal_record_id=%s, score_type=%s)",
                    submission_id,
                    link_internal_record_id,
                    score_definition.score_type,
                )
                continue

            await self._upsert_pending_queue_row(
                session=session,
                register_id=register_definition.register_id,
                link_internal_record_id=link_internal_record_id,
                change_request_id="",
                submission_id=submission_id,
                score_definition_id=score_definition.score_definition_id,
                score_type=score_definition.score_type,
                contributing_attribute_values=contributing_values,
            )

    # ------------------------------------------------------------------ #
    # Queue upsert                                                       #
    # ------------------------------------------------------------------ #

    async def _upsert_pending_queue_row(
        self,
        session: Session,
        register_id: str,
        link_internal_record_id: str,
        change_request_id: str,
        submission_id: Optional[str] = None,
        score_definition_id: str = "",
        score_type: str = "",
        contributing_attribute_values: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Insert or update a single PENDING row in the score-compute queue.

        At most one PENDING row exists per (internal_record_id, score_type) pair.
        When one already exists it is reset so the worker always processes the
        freshest snapshot.
        """
        existing_pending_row: Optional[G2PScoreComputeQueue] = (
            await session.execute(
                select(G2PScoreComputeQueue).where(
                    G2PScoreComputeQueue.link_internal_record_id == link_internal_record_id,
                    G2PScoreComputeQueue.score_type == score_type,
                    G2PScoreComputeQueue.compute_status == QueueProcessStatus.PENDING.value,
                )
            )
        ).scalar()

        if existing_pending_row:
            existing_pending_row.change_request_id = change_request_id
            existing_pending_row.submission_id = submission_id
            existing_pending_row.link_internal_record_id = link_internal_record_id
            existing_pending_row.contributing_attribute_values = contributing_attribute_values
            existing_pending_row.compute_no_of_attempts = 0
            existing_pending_row.compute_latest_timestamp = None
            existing_pending_row.compute_latest_error_code = None
            existing_pending_row.compute_status = QueueProcessStatus.PENDING.value
            session.add(existing_pending_row)
            return

        new_queue_row = G2PScoreComputeQueue(
            register_id=register_id,
            link_internal_record_id=link_internal_record_id,
            score_definition_id=score_definition_id,
            score_type=score_type,
            change_request_id=change_request_id,
            submission_id=submission_id,
            contributing_attribute_values=contributing_attribute_values,
            compute_status=QueueProcessStatus.PENDING.value,
        )
        session.add(new_queue_row)

    # ------------------------------------------------------------------ #
    # Score and history reads                                            #
    # ------------------------------------------------------------------ #

    async def get_scores_for_record(
        self, link_internal_record_id: str, session: Session
    ) -> List[ScoreData]:
        """Return all current scores for a registry record."""
        score_rows: List[G2PRegisterScore] = (
            await session.execute(
                select(G2PRegisterScore).where(
                    G2PRegisterScore.link_internal_record_id == link_internal_record_id
                )
            )
        ).scalars().all()

        return [
            ScoreData(
                score_type=row.score_type,
                computed_score=row.computed_score,
                computed_at=str(row.computed_at) if row.computed_at else None,
                triggered_by_cr_id=row.triggered_by_cr_id,
                triggered_by_submission_id=row.triggered_by_submission_id,
            )
            for row in score_rows
        ]

    async def get_score_history_for_record(
        self, link_internal_record_id: str, score_type: str, session: Session
    ) -> List[ScoreHistoryData]:
        """Return the full computation history for one record + score-type pair."""
        history_rows: List[G2PRegisterScoreHistory] = (
            await session.execute(
                select(G2PRegisterScoreHistory).where(
                    G2PRegisterScoreHistory.link_internal_record_id == link_internal_record_id,
                    G2PRegisterScoreHistory.score_type == score_type,
                )
            )
        ).scalars().all()

        return [
            ScoreHistoryData(
                computed_score=row.computed_score,
                computed_at=str(row.computed_at) if row.computed_at else None,
                triggered_by_cr_id=row.triggered_by_cr_id,
                triggered_by_submission_id=row.triggered_by_submission_id,
            )
            for row in history_rows
        ]

    # ------------------------------------------------------------------ #
    # Score-definition CRUD                                              #
    # ------------------------------------------------------------------ #

    async def get_score_definitions_for_register(
        self,
        register_id: str,
        *,
        page_number: int,
        page_size: int,
        session: Session,
    ) -> Tuple[List[ScoreDefinitionData], int]:
        """
        Return a page of score definitions whose mnemonic matches ``register_id``.

        Returns:
            (page of score definition headers, total matching row count)
        """
        register_definition = await session.get(G2PRegisterDefinition, register_id)
        if not register_definition:
            return [], 0

        mnemonic_filter = (
            G2PRegisterScoreDefinition.register_mnemonic
            == register_definition.register_mnemonic
        )

        total = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(G2PRegisterScoreDefinition)
                    .where(mnemonic_filter)
                )
            ).scalar()
            or 0
        )

        page_rows: List[G2PRegisterScoreDefinition] = (
            await session.execute(
                select(G2PRegisterScoreDefinition)
                .where(mnemonic_filter)
                .order_by(G2PRegisterScoreDefinition.score_type)
                .offset((page_number - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()

        return [self._score_definition_orm_to_data(row) for row in page_rows], total

    async def create_score_definition(
        self,
        *,
        register_id: str,
        score_type: str,
        session: Session,
    ) -> ScoreDefinitionData:
        """Create a score definition, or re-enable one if it already exists."""
        register_definition = await session.get(G2PRegisterDefinition, register_id)
        if (
            not register_definition
            or register_definition.register_purpose != RegisterPurposeEnum.REGISTER.value
        ):
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SCORE_DEFINITION_NOT_ALLOWED_FOR_REGISTER_PURPOSE.value[1],
                message="Score definitions are only allowed for registers with register_purpose = REGISTER",
            )

        mnemonic = register_definition.register_mnemonic

        existing_definition: Optional[G2PRegisterScoreDefinition] = (
            await session.execute(
                select(G2PRegisterScoreDefinition).where(
                    G2PRegisterScoreDefinition.register_mnemonic == mnemonic,
                    G2PRegisterScoreDefinition.score_type == score_type,
                )
            )
        ).scalar()

        if existing_definition:
            existing_definition.is_enabled = True
            session.add(existing_definition)
            await session.flush()
            return self._score_definition_orm_to_data(existing_definition)

        new_definition = G2PRegisterScoreDefinition(
            register_mnemonic=mnemonic,
            score_type=score_type,
            is_enabled=True,
        )
        session.add(new_definition)
        await session.flush()
        return self._score_definition_orm_to_data(new_definition)

    async def update_score_definition(
        self,
        *,
        score_definition_id: str,
        is_enabled: Optional[bool],
        session: Session,
    ) -> ScoreDefinitionData:
        """Update header-level fields on a score definition."""
        score_definition = await session.get(
            G2PRegisterScoreDefinition, score_definition_id
        )
        if not score_definition:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SCORE_DEFINITION_NOT_FOUND.value[1],
                message=f"Score definition not found: {score_definition_id}",
            )

        await self._assert_register_purpose_is_register(
            session, score_definition.register_mnemonic
        )

        if is_enabled is not None:
            score_definition.is_enabled = is_enabled

        session.add(score_definition)
        await session.flush()
        return self._score_definition_orm_to_data(score_definition)

    async def delete_score_definition(
        self, *, score_definition_id: str, session: Session
    ) -> str:
        """
        Delete a score definition along with its contributing attributes and
        any pending queue items referencing it.
        """
        score_definition = await session.get(
            G2PRegisterScoreDefinition, score_definition_id
        )
        if not score_definition:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SCORE_DEFINITION_NOT_FOUND.value[1],
                message=f"Score definition not found: {score_definition_id}",
            )

        await self._assert_register_purpose_is_register(
            session, score_definition.register_mnemonic
        )

        await session.execute(
            delete(G2PRegisterScoreContributingAttribute).where(
                and_(
                    G2PRegisterScoreContributingAttribute.register_mnemonic
                    == score_definition.register_mnemonic,
                    G2PRegisterScoreContributingAttribute.score_type
                    == score_definition.score_type,
                )
            )
        )
        await session.execute(
            delete(G2PScoreComputeQueue).where(
                G2PScoreComputeQueue.score_definition_id == score_definition_id
            )
        )
        await session.delete(score_definition)
        await session.flush()
        return score_definition_id

    # ------------------------------------------------------------------ #
    # Contributing-attribute CRUD                                        #
    # ------------------------------------------------------------------ #

    async def get_score_contributing_attributes_for_definition(
        self,
        *,
        score_definition_id: str,
        page_number: int,
        page_size: int,
        session: Session,
    ) -> Tuple[List[ScoreContributingAttributeData], int]:
        score_definition = await session.get(
            G2PRegisterScoreDefinition, score_definition_id
        )
        if not score_definition:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SCORE_DEFINITION_NOT_FOUND.value[1],
                message=f"Score definition not found: {score_definition_id}",
            )
        await self._assert_register_purpose_is_register(
            session, score_definition.register_mnemonic
        )

        row_filter = and_(
            G2PRegisterScoreContributingAttribute.register_mnemonic
            == score_definition.register_mnemonic,
            G2PRegisterScoreContributingAttribute.score_type == score_definition.score_type,
        )

        total = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(G2PRegisterScoreContributingAttribute)
                    .where(row_filter)
                )
            ).scalar()
            or 0
        )

        page_rows = (
            await session.execute(
                select(G2PRegisterScoreContributingAttribute)
                .where(row_filter)
                .order_by(G2PRegisterScoreContributingAttribute.attribute_name)
                .offset((page_number - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()

        return [self._contributing_attribute_orm_to_data(row) for row in page_rows], total

    async def create_score_contributing_attribute(
        self,
        *,
        score_definition_id: str,
        attribute: ScoreContributingAttributeInput,
        session: Session,
    ) -> ScoreContributingAttributeData:
        score_definition = await session.get(
            G2PRegisterScoreDefinition, score_definition_id
        )
        if not score_definition:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SCORE_DEFINITION_NOT_FOUND.value[1],
                message=f"Score definition not found: {score_definition_id}",
            )
        await self._assert_register_purpose_is_register(
            session, score_definition.register_mnemonic
        )
        self._validate_contributing_attribute_input(attribute)

        attribute_name = attribute.attribute_name.strip()
        if await self._contributing_attribute_name_exists(
            session,
            register_mnemonic=score_definition.register_mnemonic,
            score_type=score_definition.score_type,
            attribute_name=attribute_name,
            exclude_contributing_attribute_id=None,
        ):
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SCORE_DEFINITION_CONTRIBUTING_ATTRIBUTES_INVALID.value[1],
                message=f"Contributing attribute already exists for name: {attribute_name}",
            )

        new_row = G2PRegisterScoreContributingAttribute(
            register_mnemonic=score_definition.register_mnemonic,
            score_type=score_definition.score_type,
            attribute_name=attribute_name,
            attribute_computation_required=attribute.attribute_computation_required,
            attribute_computation_value=attribute.attribute_computation_value,
            attribute_weightage=attribute.attribute_weightage,
        )
        session.add(new_row)
        await session.flush()
        return self._contributing_attribute_orm_to_data(new_row)

    async def update_score_contributing_attribute(
        self,
        *,
        contributing_attribute_id: str,
        attribute_name: Optional[str],
        attribute_computation_required: Optional[bool],
        attribute_computation_value: Optional[Dict[str, Any]],
        attribute_weightage: Optional[float],
        session: Session,
    ) -> ScoreContributingAttributeData:
        row: Optional[G2PRegisterScoreContributingAttribute] = await session.get(
            G2PRegisterScoreContributingAttribute, contributing_attribute_id
        )
        if not row:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SCORE_CONTRIBUTING_ATTRIBUTE_NOT_FOUND.value[1],
                message=f"Score contributing attribute not found: {contributing_attribute_id}",
            )
        await self._assert_register_purpose_is_register(session, row.register_mnemonic)

        if all(
            field is None
            for field in (
                attribute_name,
                attribute_computation_required,
                attribute_computation_value,
                attribute_weightage,
            )
        ):
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SCORE_VALIDATION_ERROR.value[1],
                message="At least one field must be provided to update",
            )

        new_name = attribute_name.strip() if attribute_name is not None else row.attribute_name
        if not new_name:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SCORE_DEFINITION_CONTRIBUTING_ATTRIBUTES_INVALID.value[1],
                message="attribute_name cannot be empty",
            )

        if attribute_name is not None:
            if await self._contributing_attribute_name_exists(
                session,
                register_mnemonic=row.register_mnemonic,
                score_type=row.score_type,
                attribute_name=new_name,
                exclude_contributing_attribute_id=contributing_attribute_id,
            ):
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.SCORE_DEFINITION_CONTRIBUTING_ATTRIBUTES_INVALID.value[1],
                    message=f"Contributing attribute already exists for name: {new_name}",
                )
            row.attribute_name = new_name

        if attribute_computation_required is not None:
            row.attribute_computation_required = attribute_computation_required
        if attribute_computation_value is not None:
            row.attribute_computation_value = attribute_computation_value
        if attribute_weightage is not None:
            row.attribute_weightage = attribute_weightage

        session.add(row)
        await session.flush()
        return self._contributing_attribute_orm_to_data(row)

    async def delete_score_contributing_attribute(
        self, *, contributing_attribute_id: str, session: Session
    ) -> str:
        row: Optional[G2PRegisterScoreContributingAttribute] = await session.get(
            G2PRegisterScoreContributingAttribute, contributing_attribute_id
        )
        if not row:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SCORE_CONTRIBUTING_ATTRIBUTE_NOT_FOUND.value[1],
                message=f"Score contributing attribute not found: {contributing_attribute_id}",
            )
        await self._assert_register_purpose_is_register(session, row.register_mnemonic)
        await session.delete(row)
        await session.flush()
        return contributing_attribute_id

    # ------------------------------------------------------------------ #
    # Guard helpers                                                      #
    # ------------------------------------------------------------------ #

    async def _assert_register_purpose_is_register(
        self, session: Session, register_mnemonic: str
    ) -> None:
        """Raise if no REGISTER-purpose definition exists for the given mnemonic."""
        match = (
            await session.execute(
                select(G2PRegisterDefinition)
                .where(
                    G2PRegisterDefinition.register_mnemonic == register_mnemonic,
                    G2PRegisterDefinition.register_purpose
                    == RegisterPurposeEnum.REGISTER.value,
                )
                .limit(1)
            )
        ).scalar()
        if not match:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SCORE_DEFINITION_NOT_ALLOWED_FOR_REGISTER_PURPOSE.value[1],
                message="Score definitions are only allowed for registers with register_purpose = REGISTER",
            )

    @staticmethod
    def _registers_share_mnemonic(
        subject: Optional[G2PRegisterDefinition],
        section: Optional[G2PRegisterDefinition],
    ) -> bool:
        """True when both definitions exist and share the same register mnemonic."""
        return (
            subject is not None
            and section is not None
            and subject.register_mnemonic == section.register_mnemonic
        )

    # ------------------------------------------------------------------ #
    # Change-request payload introspection                               #
    # ------------------------------------------------------------------ #

    async def _resolve_touched_leaf_paths_for_change_request(
        self, change_request_id: str, session: Session
    ) -> set:
        """
        Return dot-paths for every field actually changed in the CR payload,
        excluding metadata keys and NO_CHANGE items.
        """
        payload_row = (
            await session.execute(
                select(G2PRegisterChangeRequestPayload).where(
                    G2PRegisterChangeRequestPayload.change_request_id == change_request_id
                )
            )
        ).scalar_one_or_none()

        if not payload_row or payload_row.change_payload is None:
            return set()

        payload_items = payload_row.change_payload
        if isinstance(payload_items, dict):
            payload_items = [payload_items]
        elif not isinstance(payload_items, list):
            return set()

        touched_paths: set = set()
        for item in payload_items:
            if not isinstance(item, dict):
                continue
            if item.get("edit_action") == ChangeActionEnum.NO_CHANGE.value:
                continue
            self._collect_leaf_paths(item, touched_paths)
        return touched_paths

    def _collect_leaf_paths(
        self, item: Dict[str, Any], accumulator: set, *, prefix: str = ""
    ) -> None:
        """Recursively collect all leaf-level dot-paths from a change-payload item."""
        for key, value in item.items():
            if key in _CHANGE_PAYLOAD_METADATA_KEYS:
                continue
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                if value:
                    self._collect_leaf_paths(value, accumulator, prefix=path)
                else:
                    accumulator.add(path)
            else:
                accumulator.add(path)

    # ------------------------------------------------------------------ #
    # Contributing-attribute snapshot helpers                            #
    # ------------------------------------------------------------------ #

    async def _build_contributing_snapshots_for_change_request(
        self,
        change_request: G2PRegisterChangeRequest,
        session: Session,
    ) -> List[Tuple[G2PRegisterScoreDefinition, str, Dict[str, Any]]]:
        """
        Build (score_definition, register_id, contributing_values) tuples for
        every enabled score definition on this section register.

        Returns an empty list when the section is ineligible.
        """
        snapshots: List[Tuple[G2PRegisterScoreDefinition, str, Dict[str, Any]]] = []

        register_definition = await session.get(
            G2PRegisterDefinition, change_request.section_register_id
        )
        if not register_definition:
            return snapshots
        if register_definition.register_purpose != RegisterPurposeEnum.REGISTER.value:
            return snapshots

        enabled_score_definitions = (
            await session.execute(
                select(G2PRegisterScoreDefinition).where(
                    G2PRegisterScoreDefinition.register_mnemonic
                    == register_definition.register_mnemonic,
                    G2PRegisterScoreDefinition.is_enabled.is_(True),
                )
            )
        ).scalars().all()

        if not enabled_score_definitions:
            return snapshots

        register_model_class = self._load_register_model(
            register_mnemonic=register_definition.register_mnemonic
        )
        if register_model_class is None:
            return snapshots

        register_record = (
            await session.execute(
                select(register_model_class).where(
                    register_model_class.internal_record_id
                    == change_request.internal_record_id
                )
            )
        ).scalar()
        if not register_record:
            return snapshots

        record_dict = self._orm_instance_to_dict(register_record)

        for score_definition in enabled_score_definitions:
            contributing_paths = await self._fetch_contributing_attribute_paths(
                session,
                register_mnemonic=score_definition.register_mnemonic,
                score_type=score_definition.score_type,
            )
            if not contributing_paths:
                continue

            contributing_values: Dict[str, Any] = {
                path: self._resolve_dot_path(record_dict, path)
                for path in contributing_paths
            }
            snapshots.append(
                (score_definition, register_definition.register_id, contributing_values)
            )
        return snapshots

    async def _fetch_latest_completed_snapshot(
        self,
        session: Session,
        *,
        link_internal_record_id: str,
        score_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Return the contributing_attribute_values from the most recent COMPLETED queue row."""
        completed_row = (
            await session.execute(
                select(G2PScoreComputeQueue)
                .where(
                    G2PScoreComputeQueue.link_internal_record_id == link_internal_record_id,
                    G2PScoreComputeQueue.score_type == score_type,
                    G2PScoreComputeQueue.compute_status == QueueProcessStatus.COMPLETED.value,
                )
                .order_by(desc(G2PScoreComputeQueue.compute_latest_timestamp))
                .limit(1)
            )
        ).scalar_one_or_none()

        if completed_row is None or completed_row.contributing_attribute_values is None:
            return None

        snap = completed_row.contributing_attribute_values
        return dict(snap) if isinstance(snap, dict) else None

    def _touched_values_match_snapshot(
        self,
        last_snapshot: Dict[str, Any],
        current_values: Dict[str, Any],
        touched_paths: List[str],
    ) -> bool:
        """
        Return True when every touched contributing path is present in the prior
        snapshot with an identical serialized value (new keys or value diffs → False).
        """
        for path in touched_paths:
            if path not in last_snapshot:
                return False
            if not self._values_are_equal(current_values.get(path), last_snapshot.get(path)):
                return False
        return True

    @staticmethod
    def _values_are_equal(a: Any, b: Any) -> bool:
        """JSON-serialization equality check (order-insensitive for dicts)."""
        return json.dumps(a, sort_keys=True, default=str) == json.dumps(
            b, sort_keys=True, default=str
        )

    # ------------------------------------------------------------------ #
    # Path-overlap helpers                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _contributing_path_overlaps_touched_leaves(
        contributing_path: str, touched_leaves: set
    ) -> bool:
        """
        True when the contributing dot-path is the same as, a parent of, or a
        descendant of any touched payload leaf path.
        """
        if contributing_path in touched_leaves:
            return True
        prefix = contributing_path + "."
        if any(leaf.startswith(prefix) for leaf in touched_leaves):
            return True
        if any(contributing_path.startswith(leaf + ".") for leaf in touched_leaves):
            return True
        return False

    def _any_contributing_path_overlaps_touched_leaves(
        self, contributing_paths: List[str], touched_leaves: set
    ) -> bool:
        return any(
            self._contributing_path_overlaps_touched_leaves(p, touched_leaves)
            for p in contributing_paths
        )

    # ------------------------------------------------------------------ #
    # Value-presence helpers                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _value_is_present(value: Any) -> bool:
        """Return True when value is non-None, non-empty-string, and non-empty collection."""
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        if isinstance(value, (list, tuple, dict)) and len(value) == 0:
            return False
        return True

    def _any_contributing_value_is_present(
        self,
        contributing_paths: List[str],
        record_dict: Dict[str, Any],
    ) -> bool:
        """Return True when at least one contributing path resolves to a present value."""
        return any(
            self._value_is_present(self._resolve_dot_path(record_dict, path))
            for path in contributing_paths
        )

    # ------------------------------------------------------------------ #
    # Database fetch helpers                                             #
    # ------------------------------------------------------------------ #

    async def _fetch_contributing_attribute_paths(
        self, session: Session, *, register_mnemonic: str, score_type: str
    ) -> List[str]:
        """Return all attribute_name values for the given mnemonic + score_type."""
        rows: List[G2PRegisterScoreContributingAttribute] = (
            await session.execute(
                select(G2PRegisterScoreContributingAttribute).where(
                    G2PRegisterScoreContributingAttribute.register_mnemonic == register_mnemonic,
                    G2PRegisterScoreContributingAttribute.score_type == score_type,
                )
            )
        ).scalars().all()
        return [row.attribute_name for row in rows]

    async def _contributing_attribute_name_exists(
        self,
        session: Session,
        *,
        register_mnemonic: str,
        score_type: str,
        attribute_name: str,
        exclude_contributing_attribute_id: Optional[str],
    ) -> bool:
        stmt = select(
            G2PRegisterScoreContributingAttribute.contributing_attribute_id
        ).where(
            G2PRegisterScoreContributingAttribute.register_mnemonic == register_mnemonic,
            G2PRegisterScoreContributingAttribute.score_type == score_type,
            G2PRegisterScoreContributingAttribute.attribute_name == attribute_name,
        )
        if exclude_contributing_attribute_id:
            stmt = stmt.where(
                G2PRegisterScoreContributingAttribute.contributing_attribute_id
                != exclude_contributing_attribute_id
            )
        found = (await session.execute(stmt.limit(1))).scalar()
        return found is not None

    # ------------------------------------------------------------------ #
    # Model-loading helpers                                              #
    # ------------------------------------------------------------------ #

    def _load_register_model(self, *, register_mnemonic: str) -> Optional[Any]:
        """Load the domain register model class (``G2PRegister<Mnemonic>``)."""
        return self._load_domain_model(
            register_mnemonic=register_mnemonic, class_prefix="G2PRegister"
        )

    @staticmethod
    def _load_domain_model(
        *, register_mnemonic: str, class_prefix: str
    ) -> Optional[Any]:
        """
        Import a domain model class from the extensions package.

        Args:
            register_mnemonic: The register mnemonic (e.g. ``"Farmer"``).
            class_prefix: Prefix used to compose the class name
                          (e.g. ``"G2PRegister"`` or ``"G2PIntakeForm"``).

        Returns:
            The class object, or ``None`` if the import fails.
        """
        class_name = f"{class_prefix}{register_mnemonic}"
        try:
            import os
            ext_mod = os.environ.get("REGISTRY_EXTENSION_MODULE", "openg2p_registry_extensions")
            module = importlib.import_module(
                f"{ext_mod}.register_domain.models"
            )
            return getattr(module, class_name)
        except (AttributeError, ModuleNotFoundError) as exc:
            _logger.error(
                "Unable to load domain model '%s': %s", class_name, exc
            )
            return None

    # ------------------------------------------------------------------ #
    # ORM / dict helpers                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _orm_instance_to_dict(record: Any) -> Dict[str, Any]:
        """
        Convert a SQLAlchemy model instance to a plain dict keyed by column name.
        JSON columns are left as dicts to support subsequent dot-path traversal.
        """
        mapper = sqlalchemy_inspect(record).mapper
        return {col.key: getattr(record, col.key) for col in mapper.columns}

    @staticmethod
    def _resolve_dot_path(root: Dict[str, Any], path: str) -> Any:
        """
        Traverse a dot-separated path through nested dicts (or objects).

        Returns ``None`` for any missing segment rather than raising.
        """
        current: Any = root
        for segment in (path.split(".") if path else []):
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(segment)
            else:
                current = getattr(current, segment, None)
        return current

    # ------------------------------------------------------------------ #
    # Data-class converters                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _score_definition_orm_to_data(
        row: G2PRegisterScoreDefinition,
    ) -> ScoreDefinitionData:
        return ScoreDefinitionData(
            score_definition_id=row.score_definition_id,
            register_mnemonic=row.register_mnemonic,
            score_type=row.score_type,
            is_enabled=row.is_enabled,
        )

    @staticmethod
    def _contributing_attribute_orm_to_data(
        row: G2PRegisterScoreContributingAttribute,
    ) -> ScoreContributingAttributeData:
        return ScoreContributingAttributeData(
            contributing_attribute_id=row.contributing_attribute_id,
            attribute_name=row.attribute_name,
            attribute_computation_required=row.attribute_computation_required,
            attribute_computation_value=row.attribute_computation_value,
            attribute_weightage=float(row.attribute_weightage),
        )

    @staticmethod
    def _validate_contributing_attribute_input(
        attribute: ScoreContributingAttributeInput,
    ) -> None:
        if not attribute.attribute_name or not str(attribute.attribute_name).strip():
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SCORE_DEFINITION_CONTRIBUTING_ATTRIBUTES_INVALID.value[1],
                message="attribute_name must be non-empty",
            )