import importlib
import logging
from datetime import datetime
from typing import Optional

from openg2p_fastapi_common.service import BaseService
from openg2p_fastapi_common.context import dbengine

from sqlalchemy import select, inspect as sa_inspect
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..models import (
    G2PCompletionScoreComputationQueue,
    G2PRegisterDefinition,
    G2PRegisterSection,
    G2PRegisterSectionCompletionScore,
    RegisterPurposeEnum,
)
from ..models.g2p_functional_id_generation_queue import ProcessStatusEnum
from ..schemas import (
    IdealRegisterScoreData,
    IdealSectionScoreData,
    SectionCompletionScoreData,
    RecordCompletionScoreData,
)
from ..errors import G2PRegistryErrorCodes, G2PRegistryException

_logger = logging.getLogger("g2p-completion-score-service")

# Columns that must not be counted towards completion
_EXCLUDED_COLUMNS = {
    "internal_record_id",
    "link_internal_record_id",
    "link_foundational_id",
    "functional_record_id",
    "created_at",
    "created_by",
    "last_approved_at",
    "last_approved_by",
    "record_status",
}


class G2PCompletionScoreService(BaseService):
    """Computes and serves register completion scores."""

    # ---------- Domain class resolution ----------

    def _get_register_class(self, register_mnemonic: str):
        import os
        ext_mod = os.environ.get("REGISTRY_EXTENSION_MODULE", "openg2p_registry_extensions")
        module = importlib.import_module(f"{ext_mod}.register_domain.models")
        class_name = f"G2PRegister{register_mnemonic}"
        return getattr(module, class_name)

    # ---------- Enqueue (trigger) ----------

    async def enqueue_completion_score_computations(
        self,
        register_id: str,
        internal_record_id: str,
        session,
        change_request_id: Optional[str] = None,
        submission_id: Optional[str] = None,
        section_id: Optional[str] = None,
    ) -> None:
        """
        Enqueue PENDING completion-score rows gated by register.completion_score_required
        and register_purpose == REGISTER. PARENT-REGISTER sections are excluded.

        If section_id is provided, enqueue only that section. Otherwise, enqueue every
        non-PARENT-REGISTER section of the register.
        """
        register_definition: G2PRegisterDefinition = (
            await session.execute(
                select(G2PRegisterDefinition).where(
                    G2PRegisterDefinition.register_id == register_id
                )
            )
        ).scalar()

        if not register_definition or not register_definition.completion_score_required:
            return

        register_purpose = (
            register_definition.register_purpose.value
            if hasattr(register_definition.register_purpose, "value")
            else register_definition.register_purpose
        )
        if register_purpose != RegisterPurposeEnum.REGISTER.value:
            return

        stmt = select(G2PRegisterSection).where(
            G2PRegisterSection.register_id == register_id
        )
        if section_id:
            stmt = stmt.where(G2PRegisterSection.section_id == section_id)
        sections = (await session.execute(stmt)).scalars().all()

        for section in sections:
            # Exclude cross-register parent references; list sections are allowed
            if section.section_register_id != register_id and not section.is_list:
                continue
            queue_row = G2PCompletionScoreComputationQueue(
                register_id=register_id,
                internal_record_id=internal_record_id,
                section_id=section.section_id,
                change_request_id=change_request_id,
                submission_id=submission_id,
                compute_status=ProcessStatusEnum.PENDING.value,
                compute_number_of_attempts=0,
            )
            session.add(queue_row)

    async def enqueue_completion_score_computations_for_submissions(
        self,
        submission_id: str,
        section_register_ids: list[str],
        session,
    ) -> None:
        """
        Enqueue completion score computations for all records created by an intake form submission.
        Mirrors enqueue_score_computations_for_intake_submission() in G2PScoreComputeService.
        """
        _logger.info(
            f"enqueue_completion_score_computations_for_submissions called for submission_id: {submission_id}, "
            f"section_register_ids: {section_register_ids}"
        )
        import os
        ext_mod = os.environ.get("REGISTRY_EXTENSION_MODULE", "openg2p_registry_extensions")
        module = importlib.import_module(f"{ext_mod}.register_domain.models")

        for section_register_id in section_register_ids:
            register_definition: G2PRegisterDefinition = (
                await session.execute(
                    select(G2PRegisterDefinition).where(
                        G2PRegisterDefinition.register_id == section_register_id
                    )
                )
            ).scalar()

            if not register_definition:
                _logger.warning(f"Register definition '{section_register_id}' not found, skipping")
                continue

            register_purpose = (
                register_definition.register_purpose.value
                if hasattr(register_definition.register_purpose, "value")
                else register_definition.register_purpose
            )
            if register_purpose != RegisterPurposeEnum.REGISTER.value:
                _logger.info(f"Register '{section_register_id}' is not a REGISTER, skipping completion score")
                continue

            try:
                intake_class = getattr(module, f"G2PIntakeForm{register_definition.register_mnemonic}")
            except AttributeError:
                _logger.warning(
                    f"Intake form class 'G2PIntakeForm{register_definition.register_mnemonic}' not found, skipping"
                )
                continue

            intake_rows = (
                (await session.execute(select(intake_class).where(intake_class.submission_id == submission_id)))
                .scalars()
                .all()
            )

            if not intake_rows:
                _logger.info(f"No intake rows found for submission '{submission_id}' in register '{section_register_id}'")
                continue

            for intake_row in intake_rows:
                internal_record_id = intake_row.internal_record_id
                if not internal_record_id:
                    _logger.warning(f"No internal_record_id on intake row for register '{section_register_id}', skipping")
                    continue

                await self.enqueue_completion_score_computations(
                    register_id=section_register_id,
                    internal_record_id=internal_record_id,
                    session=session,
                    submission_id=submission_id,
                )

        _logger.info(f"Completion score enqueue complete for submission {submission_id}")

    # ---------- Compute ----------

    def _count_filled(self, record, columns) -> tuple[int, int]:
        total = 0
        filled = 0
        for col in columns:
            if col.key in _EXCLUDED_COLUMNS or col.primary_key:
                continue
            total += 1
            value = getattr(record, col.key, None)
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            filled += 1
        return filled, total

    async def compute_section_score(
        self,
        section: G2PRegisterSection,
        session,
    ) -> Optional[float]:
        """
        Compute section completion score for (register_id, internal_record_id, section_id)
        located on the queue row. Returns None if section record(s) not resolvable.
        """
        # section.section_register_id equals the register owning the data.
        section_register_definition: G2PRegisterDefinition = (
            await session.execute(
                select(G2PRegisterDefinition).where(
                    G2PRegisterDefinition.register_id == section.section_register_id
                )
            )
        ).scalar()
        if not section_register_definition:
            return None

        register_class = self._get_register_class(
            section_register_definition.register_mnemonic
        )
        mapper = sa_inspect(register_class)
        columns = list(mapper.columns)

        return register_class, columns

    async def compute_and_store(
        self,
        queue_id: str,
    ) -> float:
        """
        Worker-facing entry point. Loads the queue row, resolves section + record(s),
        computes score, upserts g2p_register_section_completion_score, marks queue COMPLETED.
        Raises on failure so the worker can apply retry logic.
        """
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            queue_row: G2PCompletionScoreComputationQueue = await session.get(
                G2PCompletionScoreComputationQueue, queue_id
            )
            if not queue_row:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.COMPLETION_SCORE_QUEUE_ITEM_NOT_FOUND.value[1],
                    message=G2PRegistryErrorCodes.COMPLETION_SCORE_QUEUE_ITEM_NOT_FOUND.value[0],
                )

            section: G2PRegisterSection = await session.get(
                G2PRegisterSection, queue_row.section_id
            )
            if not section:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.COMPLETION_SCORE_COMPUTE_FAILED.value[1],
                    message=f"Section {queue_row.section_id} not found",
                )

            resolved = await self.compute_section_score(section, session)
            if resolved is None:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.COMPLETION_SCORE_COMPUTE_FAILED.value[1],
                    message=f"Could not resolve section register for section {section.section_id}",
                )
            register_class, columns = resolved

            total_fields = 0
            filled_fields = 0

            if section.is_list:
                # list section: aggregate across child records linked via link_internal_record_id
                children = (
                    (
                        await session.execute(
                            select(register_class).where(
                                register_class.link_internal_record_id
                                == queue_row.internal_record_id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                for child in children:
                    f, t = self._count_filled(child, columns)
                    filled_fields += f
                    total_fields += t
            else:
                record = (
                    await session.execute(
                        select(register_class).where(
                            register_class.internal_record_id
                            == queue_row.internal_record_id
                        )
                    )
                ).scalar()
                if record is None:
                    raise G2PRegistryException(
                        code=G2PRegistryErrorCodes.COMPLETION_SCORE_COMPUTE_FAILED.value[1],
                        message=(
                            f"Record {queue_row.internal_record_id} not found for "
                            f"section {section.section_id}"
                        ),
                    )
                filled_fields, total_fields = self._count_filled(record, columns)

            ratio = (filled_fields / total_fields) if total_fields > 0 else 0.0
            weightage = section.section_weightage or 0.0
            score = ratio * weightage

            # Upsert into g2p_register_section_completion_score
            existing = (
                await session.execute(
                    select(G2PRegisterSectionCompletionScore).where(
                        G2PRegisterSectionCompletionScore.register_id == queue_row.register_id,
                        G2PRegisterSectionCompletionScore.internal_record_id == queue_row.internal_record_id,
                        G2PRegisterSectionCompletionScore.section_id == queue_row.section_id,
                    )
                )
            ).scalar()

            now = datetime.utcnow()
            if existing:
                existing.computed_section_completion_score = score
                existing.computed_timestamp = now
            else:
                session.add(
                    G2PRegisterSectionCompletionScore(
                        register_id=queue_row.register_id,
                        internal_record_id=queue_row.internal_record_id,
                        section_id=queue_row.section_id,
                        computed_section_completion_score=score,
                        computed_timestamp=now,
                    )
                )

            queue_row.compute_status = ProcessStatusEnum.COMPLETED.value
            queue_row.compute_processed_timestamp = now
            queue_row.compute_latest_error_code = None

            await session.commit()
            _logger.info(
                f"Computed completion score {score} for record={queue_row.internal_record_id} "
                f"section={queue_row.section_id}"
            )
            return score

    async def mark_failure(self, queue_id: str, error_code: str) -> None:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            queue_row: G2PCompletionScoreComputationQueue = await session.get(
                G2PCompletionScoreComputationQueue, queue_id
            )
            if not queue_row:
                return
            queue_row.compute_number_of_attempts = (
                queue_row.compute_number_of_attempts or 0
            ) + 1
            queue_row.compute_latest_error_code = error_code
            queue_row.compute_processed_timestamp = datetime.utcnow()
            queue_row.compute_status = ProcessStatusEnum.FAILED.value
            await session.commit()

    # ---------- Query APIs ----------

    async def get_ideal_completion_score_for_register(
        self, register_id: str
    ) -> IdealRegisterScoreData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            sections = (
                (
                    await session.execute(
                        select(G2PRegisterSection).where(
                            G2PRegisterSection.register_id == register_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            ideal = 0.0
            for s in sections:
                if s.section_register_id != register_id and not s.is_list:
                    continue
                ideal += s.section_weightage or 0.0
            return IdealRegisterScoreData(
                register_id=register_id, ideal_completion_score=ideal
            )

    async def get_ideal_completion_score_for_section(
        self, section_id: str
    ) -> IdealSectionScoreData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            section: G2PRegisterSection = await session.get(
                G2PRegisterSection, section_id
            )
            if not section:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.SECTION_NOT_FOUND.value[1],
                    message=G2PRegistryErrorCodes.SECTION_NOT_FOUND.value[0],
                )
            return IdealSectionScoreData(
                section_id=section_id, section_weightage=section.section_weightage or 0.0
            )

    async def get_computed_completion_score_for_section(
        self, register_id: str, internal_record_id: str, section_id: str
    ) -> SectionCompletionScoreData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            row: G2PRegisterSectionCompletionScore = (
                await session.execute(
                    select(G2PRegisterSectionCompletionScore).where(
                        G2PRegisterSectionCompletionScore.register_id == register_id,
                        G2PRegisterSectionCompletionScore.internal_record_id == internal_record_id,
                        G2PRegisterSectionCompletionScore.section_id == section_id,
                    )
                )
            ).scalar()
            if not row:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.COMPLETION_SCORE_NOT_FOUND.value[1],
                    message=G2PRegistryErrorCodes.COMPLETION_SCORE_NOT_FOUND.value[0],
                )
            section: G2PRegisterSection = await session.get(
                G2PRegisterSection, section_id
            )
            return SectionCompletionScoreData(
                register_id=row.register_id,
                internal_record_id=row.internal_record_id,
                section_id=row.section_id,
                computed_section_completion_score=row.computed_section_completion_score,
                section_weightage=(section.section_weightage if section else 0.0) or 0.0,
                computed_timestamp=row.computed_timestamp.isoformat() if row.computed_timestamp else None,
            )

    async def get_computed_completion_score_for_record(
        self, register_id: str, internal_record_id: str
    ) -> RecordCompletionScoreData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            section_rows = (
                (
                    await session.execute(
                        select(G2PRegisterSectionCompletionScore).where(
                            G2PRegisterSectionCompletionScore.register_id == register_id,
                            G2PRegisterSectionCompletionScore.internal_record_id == internal_record_id,
                        )
                    )
                )
                .scalars()
                .all()
            )

            sections_by_id: dict[str, G2PRegisterSection] = {}
            if section_rows:
                ids = list({r.section_id for r in section_rows})
                fetched = (
                    (
                        await session.execute(
                            select(G2PRegisterSection).where(
                                G2PRegisterSection.section_id.in_(ids)
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                sections_by_id = {s.section_id: s for s in fetched}

            section_data: list[SectionCompletionScoreData] = []
            actual_score = 0.0
            for r in section_rows:
                sec = sections_by_id.get(r.section_id)
                section_data.append(
                    SectionCompletionScoreData(
                        register_id=r.register_id,
                        internal_record_id=r.internal_record_id,
                        section_id=r.section_id,
                        computed_section_completion_score=r.computed_section_completion_score,
                        section_weightage=(sec.section_weightage if sec else 0.0) or 0.0,
                        computed_timestamp=r.computed_timestamp.isoformat() if r.computed_timestamp else None,
                    )
                )
                actual_score += r.computed_section_completion_score or 0.0

            ideal = (
                await self.get_ideal_completion_score_for_register(register_id)
            ).ideal_completion_score

            return RecordCompletionScoreData(
                register_id=register_id,
                internal_record_id=internal_record_id,
                section_scores=section_data,
                actual_score=actual_score,
                ideal_score=ideal,
            )
