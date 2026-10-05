import logging
import importlib
from typing import Optional, Any

from openg2p_fastapi_common.service import BaseService
from openg2p_fastapi_common.context import dbengine

from sqlalchemy import select, inspect as sa_inspect
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..models import G2PRegisterDefinition, G2PRegisterSection, G2PRegisterUITabSection, G2PRegisterSectionCompletionScore, RegisterPurposeEnum
from ..schemas import RecordData, RegisterTabRecordData, AllowedParentsData, AllowedParentRecordData
from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..repositories import RegisterRecordRepository
from .g2p_data_policy_service import G2PDataPolicyService

_logger = logging.getLogger('g2p-register-hierarchical-service')


class G2PRegisterHierarchicalService(BaseService):
    """
    Service for handling hierarchical register operations.
    Supports traversing master-child relationships between registers.
    """

    async def get_section_records(
        self,
        subject_register_id: str,
        subject_record_id: str,
        section_register_id: str,
        policy_mnemonics: list[str] | None = None,
    ) -> list[RecordData]:
        """
        Get records from section_register that are linked to subject_record.
        Handles both ancestor (traverse down) and descendant (traverse up) relationships.
        If subject_register_id == section_register_id, returns the subject record directly.

        Args:
            subject_register_id: The register we're starting from
            subject_record_id: The specific record (internal_record_id)
            section_register_id: The register we want records from

        Returns:
            List of RecordData from the section register
        """
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            # Validate both registers exist
            subject_register: G2PRegisterDefinition = await self._validate_register_definition(
                subject_register_id, session
            )

            section_register: G2PRegisterDefinition = await self._validate_register_definition(
                section_register_id, session
            )

            # Check if section_register is CORE_TABLE - if so, return filtered records directly
            # if section_register.register_purpose == RegisterPurposeEnum.CORE_TABLE.value:
            #     impl_class = self._get_implementation_class(section_register.register_mnemonic, section_register.register_purpose)
            #     result = await session.execute(
            #         select(impl_class).where(
            #             impl_class.internal_record_id == subject_record_id
            #         )
            #     )
            #     records = result.scalars().all()
            #     return [self._convert_record_to_record_data(r) for r in records]

            # If same register, return the subject record directly
            if subject_register_id == section_register_id:
                return await self._get_same_register_record(
                    subject_register, subject_record_id, session, policy_mnemonics
                )

            # Build hierarchy path and determine direction
            path: list[G2PRegisterDefinition] = []
            path, direction = await self._build_register_hierarchy_path(
                subject_register_id, section_register_id, session
            )

            if direction == "DOWN":
                # Subject is ancestor, traverse DOWN to get section records
                return await self._traverse_down_hierarchy(
                    subject_register, subject_record_id, path, session, policy_mnemonics
                )
            elif direction == "UP":
                # Subject is descendant, traverse UP to get section record
                return await self._traverse_up_hierarchy(
                    subject_register, subject_record_id, path, session, policy_mnemonics
                )
            elif direction == "PEER":
                # Subject and section are peers, traverse both directions
                return await self._traverse_peer_hierarchy(
                    subject_register, subject_record_id, path, session, policy_mnemonics
                )

            else:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.REGISTER_NOT_FOUND.value[1],
                    message=f"Register with id {section_register_id} not found"
                )

    async def _build_register_policy_condition(
        self,
        register_id: str,
        implementation_class,
        policy_mnemonics: list[str] | None,
        session,
    ):
        if not policy_mnemonics:
            return None

        merged_expression = await G2PDataPolicyService.get_component().resolve_register_record_policy(
            register_id, policy_mnemonics, session
        )
        if not merged_expression:
            return None

        return RegisterRecordRepository(implementation_class).build_policy_condition(merged_expression)

    async def _ensure_subject_record_readable(
        self,
        register: G2PRegisterDefinition,
        record_id: str,
        policy_mnemonics: list[str] | None,
        session,
    ) -> None:
        """Raise if the subject record is missing or blocked by data policy."""
        impl_class = self._get_implementation_class(register.register_mnemonic, register.register_purpose)
        filter_conditions = [impl_class.internal_record_id == record_id]
        policy_condition = await self._build_register_policy_condition(
            register.register_id, impl_class, policy_mnemonics, session
        )
        if policy_condition is not None:
            filter_conditions.append(policy_condition)

        record = (
            await session.execute(select(impl_class).where(*filter_conditions))
        ).scalar()

        if record is not None:
            return

        if policy_condition is not None:
            exists = (
                await session.execute(
                    select(impl_class).where(impl_class.internal_record_id == record_id)
                )
            ).scalar()
            if exists:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.RECORD_ACCESS_DENIED.value[1],
                    message=G2PRegistryErrorCodes.RECORD_ACCESS_DENIED.value[0],
                )

        raise G2PRegistryException(
            code=G2PRegistryErrorCodes.REGISTER_DATA_NOT_FOUND.value[1],
            message=f"Record {record_id} not found in register {register.register_mnemonic}",
        )

    async def _get_same_register_record(
        self,
        register: G2PRegisterDefinition,
        record_id: str,
        session,
        policy_mnemonics: list[str] | None = None,
    ) -> list[RecordData]:
        """
        Get a record from the same register (no hierarchy traversal needed).

        Args:
            register: The register definition
            record_id: The record's internal_record_id
            session: Database session

        Returns:
            List containing single RecordData
        """
        impl_class = self._get_implementation_class(register.register_mnemonic, register.register_purpose)
        filter_conditions = [impl_class.internal_record_id == record_id]
        policy_condition = await self._build_register_policy_condition(
            register.register_id, impl_class, policy_mnemonics, session
        )
        if policy_condition is not None:
            filter_conditions.append(policy_condition)

        result = await session.execute(select(impl_class).where(*filter_conditions))
        record = result.scalar()

        if not record:
            if policy_condition is not None:
                exists = (
                    await session.execute(
                        select(impl_class).where(impl_class.internal_record_id == record_id)
                    )
                ).scalar()
                if exists:
                    raise G2PRegistryException(
                        code=G2PRegistryErrorCodes.RECORD_ACCESS_DENIED.value[1],
                        message=G2PRegistryErrorCodes.RECORD_ACCESS_DENIED.value[0],
                    )
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTER_DATA_NOT_FOUND.value[1],
                message=f"Record {record_id} not found in register {register.register_mnemonic}"
            )

        return [await self._convert_record_to_record_data(record, session)]

    async def _validate_register_definition(
        self,
        register_id: str,
        session
    ) -> G2PRegisterDefinition:
        """Validate that a register definition exists."""
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
                message=f"Register with id {register_id} not found"
            )

        return register_definition

    async def _build_register_hierarchy_path(
        self,
        subject_register_id: str,
        section_register_id: str,
        session
    ) -> tuple[list[G2PRegisterDefinition], str]:
        """
        Build the path between two registers and determine direction.

        Returns:
            (path, direction) where direction is "UP" or "DOWN"
            - DOWN: subject is ancestor of section (path goes from section up to subject)
            - UP: subject is descendant of section (path goes from subject up to section)
        """
        # Try finding path going UP from section to subject (subject is ancestor)
        path_from_section: list[G2PRegisterDefinition] | None = await self._find_path_to_ancestor(
            section_register_id, subject_register_id, session
        )
        if path_from_section:
            return (path_from_section, "DOWN")

        # Try finding path going UP from subject to section (subject is descendant)
        path_from_subject: list[G2PRegisterDefinition] | None = await self._find_path_to_ancestor(
            subject_register_id, section_register_id, session
        )
        if path_from_subject:
            return (path_from_subject, "UP")

        # If no path found, try peers
        path_from_peer: list[G2PRegisterDefinition] | None = await self._find_path_to_peer(
            subject_register_id, section_register_id, session
        )
        if path_from_peer:
            return (path_from_peer, "PEER")

        raise G2PRegistryException(
            code=G2PRegistryErrorCodes.REGISTER_DATA_NOT_FOUND.value[1],
            message=f"No hierarchy path found between registers {subject_register_id} and {section_register_id}"
        )
    async def _find_path_to_peer(
        self,
        subject_register_id: str,
        section_register_id: str,
        session,
    ) -> list[G2PRegisterDefinition] | None:
        """
        Find path from start_register up to target_register via master_register_id.
        In case of DOWN, start_register is section_register_id, target_register_id is subject_register_id.
        In case of UP, start_register is subject_register_id, target_register_id is section_register_id.
        """
        subject_register: G2PRegisterDefinition | None = await session.get(G2PRegisterDefinition, subject_register_id)
        section_register: G2PRegisterDefinition | None = await session.get(G2PRegisterDefinition, section_register_id)

        if subject_register.master_register_id == section_register.master_register_id:
            return [section_register]

        return None

    async def _find_path_to_ancestor(
        self,
        start_register_id: str,
        target_register_id: str,
        session,
        max_depth: int = 20
    ) -> list[G2PRegisterDefinition] | None:
        """
        Find path from start_register up to target_register via master_register_id.
        In case of DOWN, start_register is section_register_id, target_register_id is subject_register_id.
        In case of UP, start_register is subject_register_id, target_register_id is section_register_id.
        
        Args:
            start_register_id: Starting register
            target_register_id: Target ancestor register
            session: Database session
            max_depth: Maximum hierarchy depth to prevent infinite loops
            
        Returns:
            List of register definitions from start to target, or None if not found
        """
        path: list[G2PRegisterDefinition] = []
        current_id: str | None = start_register_id
        depth: int = 0

        while current_id and depth < max_depth:
            register_definition: G2PRegisterDefinition = (
                await session.execute(
                    select(G2PRegisterDefinition).where(
                        G2PRegisterDefinition.register_id == current_id
                    )
                )
            ).scalar()

            if not register_definition:
                return None

            path.append(register_definition)

            if current_id == target_register_id:
                return path

            current_id = register_definition.master_register_id
            depth += 1

        return None

    def _get_implementation_class(self, register_mnemonic: str, register_purpose: str = None):
        """
        Get the implementation class for a register based on its mnemonic.
        
        Args:
            register_mnemonic: The register mnemonic (e.g., "Farmer", "Score")
            register_purpose: The register purpose (e.g., "CORE_TABLE", "REGISTER")
                          If None, will try extensions first, then core
            
        Returns:
            The SQLAlchemy model class for the register
        """
        _logger.info(f"Looking for implementation class for register_mnemonic='{register_mnemonic}' with purpose={register_purpose}")
        
        # If register_purpose is CORE_TABLE, look in core models first
        if register_purpose == RegisterPurposeEnum.CORE_TABLE.value:
            try:
                module = importlib.import_module("openg2p_registry_core.models")
                implementation_class_name = f"G2PRegister{register_mnemonic}"
                
                if hasattr(module, implementation_class_name):
                    implementation_class = getattr(module, implementation_class_name)
                    _logger.info(f"Found core implementation class {implementation_class_name} for {register_mnemonic}")
                    return implementation_class
                else:
                    raise AttributeError(f"Core class {implementation_class_name} not found")
                    
            except (AttributeError, ModuleNotFoundError) as error:
                _logger.error(f"Could not load core class for {register_mnemonic}: {str(error)}")
                raise
        
        # Try extensions for regular registers
        try:
            import os
            ext_mod = os.environ.get("REGISTRY_EXTENSION_MODULE", "openg2p_registry_extensions")
            module = importlib.import_module(f"{ext_mod}.register_domain.models")
            register_class_prefix: str = "G2PRegister"
            implementation_class_name: str = f"{register_class_prefix}{register_mnemonic}"
            implementation_class = getattr(module, implementation_class_name)
            _logger.info(f"Found extension implementation class {implementation_class_name} for {register_mnemonic}")
            return implementation_class
        except (AttributeError, ModuleNotFoundError) as error:
            _logger.error(f"Could not find register class for mnemonic {register_mnemonic}: {str(error)}")
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTER_DATA_NOT_FOUND.value[1],
                message=f"Register implementation not found for {register_mnemonic}"
            )

    async def _convert_record_to_record_data(self, record, session) -> RecordData:
        """
        Convert an ORM record object to RecordData schema.
        Extra fields from the implementation table are flattened at root level.

        Resolves record_image_document_id to a presigned record_image_url via the
        document catalog (same pattern as G2PRegisterService.get_record).
        """
        records = await self._convert_records_to_record_data([record], session)
        return records[0]

    async def _convert_records_to_record_data(
        self, records: list, session
    ) -> list[RecordData]:
        """Convert ORM records to RecordData, batch-resolving images and section documents."""
        if not records:
            return []

        from .g2p_document_service import G2PDocumentService

        document_service = G2PDocumentService.get_component()
        record_image_urls = await document_service.get_document_urls(
            session,
            [
                getattr(record, "record_image_document_id", None)
                for record in records
            ],
        )
        section_documents_map = await document_service.get_section_documents_map(
            session,
            [
                getattr(record, "internal_record_id", None)
                for record in records
            ],
        )

        result: list[RecordData] = []
        for record in records:
            mapper = sa_inspect(record.__class__)
            extra_fields: dict = {}

            for column in mapper.columns:
                column_name: str = column.name
                value = getattr(record, column_name, None)

                if value is not None and hasattr(value, "isoformat"):
                    value = value.isoformat()

                extra_fields[column_name] = value

            document_id = getattr(record, "record_image_document_id", None)
            if document_id:
                extra_fields["record_image_url"] = record_image_urls.get(document_id)

            internal_record_id = getattr(record, "internal_record_id", None)
            extra_fields["documents"] = section_documents_map.get(
                internal_record_id, []
            )

            result.append(RecordData(**extra_fields))

        return result

    async def _traverse_peer_hierarchy(
        self,
        subject_register: G2PRegisterDefinition,
        subject_record_id: str,
        path: list[G2PRegisterDefinition],
        session,
        policy_mnemonics: list[str] | None = None,
    ) -> list[RecordData]:
        
        # Get subject record from subject register
        subject_impl_class = self._get_implementation_class(subject_register.register_mnemonic, subject_register.register_purpose)
        subject_record = await session.get(subject_impl_class, subject_record_id)
        
        if not subject_record:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTER_DATA_NOT_FOUND.value[1],
                message=f"Subject record {subject_record_id} not found"
            )

        # Get records from section register where section records link_internal_record_id = subject records internal_record_id
        peer_register = path[0]
        peer_record_impl_class = self._get_implementation_class(peer_register.register_mnemonic, peer_register.register_purpose)
        filter_conditions = [
            peer_record_impl_class.link_internal_record_id == subject_record.link_internal_record_id
        ]
        policy_condition = await self._build_register_policy_condition(
            peer_register.register_id, peer_record_impl_class, policy_mnemonics, session
        )
        if policy_condition is not None:
            filter_conditions.append(policy_condition)

        peer_records = await session.execute(
            select(peer_record_impl_class).where(*filter_conditions)
        )
        peer_records = peer_records.scalars().all()

        return await self._convert_records_to_record_data(peer_records, session)


    async def _traverse_down_hierarchy(
        self,
        subject_register: G2PRegisterDefinition,
        subject_record_id: str,
        path: list[G2PRegisterDefinition],
        session,
        policy_mnemonics: list[str] | None = None,
    ) -> list[RecordData]:
        """
        Traverse DOWN from ancestor to descendant, collecting all linked records.

        Args:
            subject_register: The subject register definition (ancestor)
            subject_record_id: The starting record's internal_record_id
            path: Path from related_register (index 0) up to subject_register (last index)
            session: Database session

        Returns:
            List of RecordData from the related_register (path[0])
        """
        # Validate subject record exists
        subject_impl_class = self._get_implementation_class(subject_register.register_mnemonic, subject_register.register_purpose)
        subject_record = (
            await session.execute(
                select(subject_impl_class).where(
                    subject_impl_class.internal_record_id == subject_record_id
                )
            )
        ).scalar()

        if not subject_record:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTER_DATA_NOT_FOUND.value[1],
                message=f"Subject record {subject_record_id} not found"
            )

        # Reverse path to go from subject (top) to related (bottom)
        path_reversed: list[G2PRegisterDefinition] = list(reversed(path))

        # Start with subject record's internal_record_id
        current_record_ids: list[str] = [subject_record_id]

        # Skip first register (subject), traverse to children
        for i in range(1, len(path_reversed)):
            register_def: G2PRegisterDefinition = path_reversed[i]
            impl_class = self._get_implementation_class(register_def.register_mnemonic, register_def.register_purpose)

            # # Check if this register supports hierarchical operations
            # if not hasattr(impl_class, 'link_internal_record_id'):
            #     # For CORE_TABLE registers without link_internal_record_id, filter by internal_record_id
            #     result = await session.execute(
            #         select(impl_class).where(
            #             impl_class.internal_record_id.in_(current_record_ids)
            #         )
            #     )
            #     records = result.scalars().all()
                
            #     # If this is the last level (related_register), convert to RecordData
            #     if i == len(path_reversed) - 1:
            #         return [self._convert_record_to_record_data(r) for r in records]
                
            #     # For CORE_TABLE registers, get the internal_record_ids for the next iteration
            #     current_record_ids = [r.internal_record_id for r in records]
            #     continue

            # Find all records in this register where link_internal_record_id is in current_record_ids
            filter_conditions = [impl_class.link_internal_record_id.in_(current_record_ids)]
            if i == len(path_reversed) - 1:
                policy_condition = await self._build_register_policy_condition(
                    register_def.register_id, impl_class, policy_mnemonics, session
                )
                if policy_condition is not None:
                    filter_conditions.append(policy_condition)

            result = await session.execute(
                select(impl_class).where(*filter_conditions)
            )
            records = result.scalars().all()

            if not records:
                return []

            # If this is the last level (related_register), convert to RecordData
            if i == len(path_reversed) - 1:
                return await self._convert_records_to_record_data(records, session)

            # Otherwise, get the internal_record_ids for the next iteration
            current_record_ids = [r.internal_record_id for r in records]

        return []

    async def _traverse_up_hierarchy(
        self,
        subject_register: G2PRegisterDefinition,
        subject_record_id: str,
        path: list[G2PRegisterDefinition],
        session,
        policy_mnemonics: list[str] | None = None,
    ) -> list[RecordData]:
        """
        Traverse UP from descendant to ancestor, following link_internal_record_id.

        Args:
            subject_register: The subject register definition (descendant)
            subject_record_id: The starting record's internal_record_id
            path: Path from subject_register (index 0) up to related_register (last index)
            session: Database session

        Returns:
            List containing single RecordData from the related_register (path[-1])
        """
        current_record_id: str = subject_record_id

        # Start from subject, traverse up using link_internal_record_id
        for i in range(len(path) - 1):
            current_register: G2PRegisterDefinition = path[i]
            impl_class = self._get_implementation_class(current_register.register_mnemonic, current_register.register_purpose)

            # Get current record
            result = await session.execute(
                select(impl_class).where(
                    impl_class.internal_record_id == current_record_id
                )
            )
            record = result.scalar()

            if not record:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.REGISTER_DATA_NOT_FOUND.value[1],
                    message=f"Record {current_record_id} not found in register {current_register.register_mnemonic}"
                )

            if not record.link_internal_record_id:
                return []

            current_record_id = record.link_internal_record_id

        # Now get the final record from related_register
        related_register: G2PRegisterDefinition = path[-1]
        impl_class = self._get_implementation_class(related_register.register_mnemonic, related_register.register_purpose)
        filter_conditions = [impl_class.internal_record_id == current_record_id]
        policy_condition = await self._build_register_policy_condition(
            related_register.register_id, impl_class, policy_mnemonics, session
        )
        if policy_condition is not None:
            filter_conditions.append(policy_condition)

        result = await session.execute(
            select(impl_class).where(*filter_conditions)
        )
        record = result.scalar()

        if record:
            return [await self._convert_record_to_record_data(record, session)]

        return []

    async def get_tab_records(
        self,
        subject_register_id: str,
        subject_record_id: str,
        tab_id: str,
        policy_mnemonics: list[str] | None = None,
    ) -> list[RegisterTabRecordData]:
        """
        Get all records for a tab, grouped by unique section_register_id.
        Multiple sections with the same section_register_id are deduplicated.

        Args:
            subject_register_id: The register we're starting from
            subject_record_id: The specific record (internal_record_id)
            tab_id: The tab to fetch records for

        Returns:
            List of RegisterTabRecordData, one per unique section_register_id
        """
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            # Validate subject register exists
            subject_register: G2PRegisterDefinition = await self._validate_register_definition(subject_register_id, session)
            await self._ensure_subject_record_readable(
                subject_register, subject_record_id, policy_mnemonics, session
            )
            completion_score_required: bool = bool(subject_register.completion_score_required) if subject_register else False

            # Fetch all sections for this tab
            result = await session.execute(
                select(G2PRegisterSection)
                .join(
                    G2PRegisterUITabSection,
                    G2PRegisterUITabSection.section_id == G2PRegisterSection.section_id,
                )
                .where(
                    G2PRegisterSection.register_id == subject_register_id,
                    G2PRegisterUITabSection.register_id == subject_register_id,
                    G2PRegisterUITabSection.tab_id == tab_id,
                )
                .order_by(G2PRegisterUITabSection.section_order)
            )
            sections = result.scalars().all()

            if not sections:
                return []

            # Group sections by (section_register_id, is_list)
            sections_by_reg_id: dict[tuple[str, bool], list[G2PRegisterSection]] = {}
            for section in sections:
                key = (section.section_register_id, section.is_list)
                sections_by_reg_id.setdefault(key, []).append(section)

            # Fetch register-level completion scores for this record
            all_register_sections = (
                await session.execute(
                    select(G2PRegisterSection).where(
                        G2PRegisterSection.register_id == subject_register_id,
                    )
                )
            ).scalars().all()
            ideal_score = sum(
                s.section_weightage or 0.0
                for s in all_register_sections
                if s.section_register_id == subject_register_id or s.is_list
            )

            all_score_section_ids = [
                s.section_id for s in all_register_sections
                if s.section_register_id == subject_register_id or s.is_list
            ]
            score_rows = (
                await session.execute(
                    select(G2PRegisterSectionCompletionScore).where(
                        G2PRegisterSectionCompletionScore.register_id == subject_register_id,
                        G2PRegisterSectionCompletionScore.internal_record_id == subject_record_id,
                        G2PRegisterSectionCompletionScore.section_id.in_(all_score_section_ids),
                    )
                )
            ).scalars().all()
            actual_score = sum(
                (r.computed_section_completion_score or 0.0) for r in score_rows
            )

            # Fetch records for each unique section_register_id
            tab_records: list[RegisterTabRecordData] = []
            for (section_register_id, is_list), group_sections in sections_by_reg_id.items():
                records: list[RecordData] = await self.get_section_records(
                    subject_register_id=subject_register_id,
                    subject_record_id=subject_record_id,
                    section_register_id=section_register_id,
                    policy_mnemonics=policy_mnemonics,
                )

                # Add completion scores to each record
                for record in records:
                    record.actual_score = actual_score
                    record.ideal_score = ideal_score
                    record.completion_score_required = completion_score_required

                tab_records.append(RegisterTabRecordData(
                    section_register_id=section_register_id,
                    is_list=is_list,
                    records=records
                ))

            return tab_records

    def _to_snake_case(self, name: str) -> str:
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    async def enrich_record_hierarchy(
        self,
        register_definition: G2PRegisterDefinition,
        record: Any,
        session,
        visited_registers: set[str] = None
    ) -> dict:
        """
        Recursively enrich a record with its parent and child records.
        """
        if visited_registers is None:
            visited_registers = set()

        # Create a new set for this branch to allow revisiting nodes from different branches
        # but prevent cycles in the current path.
        current_visited = visited_registers.copy()
        
        if register_definition.register_id in current_visited:
             # Just return base record if already visited to break cycle
             return (
                 await self._convert_record_to_record_data(record, session)
             ).model_dump(exclude_unset=True)
             
        current_visited.add(register_definition.register_id)

        # Base Data
        record_data = (
            await self._convert_record_to_record_data(record, session)
        ).model_dump(exclude_unset=True)

        # 1. Fetch Children (Down)
        child_registers = (await session.execute(
            select(G2PRegisterDefinition).where(
                G2PRegisterDefinition.master_register_id == register_definition.register_id
            )
        )).scalars().all()

        for child_reg in child_registers:
            # Skip if we've already visited this register in the current path (prevents cycles/redundancy)
            if child_reg.register_id in current_visited:
                continue

            child_key = self._to_snake_case(child_reg.register_mnemonic)
            
            # Get child implementation class
            child_impl = self._get_implementation_class(child_reg.register_mnemonic, child_reg.register_purpose)
            
            # Fetch linked records
            child_records = (await session.execute(
                select(child_impl).where(
                    child_impl.link_internal_record_id == record.internal_record_id
                )
            )).scalars().all()
            
            enrich_children = []
            for child_rec in child_records:
                enriched_child = await self.enrich_record_hierarchy(
                    child_reg, child_rec, session, current_visited
                )
                enrich_children.append(enriched_child)
            
            # User example convention: list of children
            record_data[child_key] = enrich_children

        # 2. Fetch Parent (Up)
        if register_definition.master_register_id:
            parent_reg = await session.get(G2PRegisterDefinition, register_definition.master_register_id)
            if parent_reg and parent_reg.register_id not in current_visited:
                parent_key = self._to_snake_case(parent_reg.register_mnemonic)
                 
                # Get parent implementation class
                parent_impl = self._get_implementation_class(parent_reg.register_mnemonic, parent_reg.register_purpose)
                 
                # Fetch parent record
                if record.link_internal_record_id:
                    parent_rec = await session.get(parent_impl, record.link_internal_record_id)
                    if parent_rec:
                        enriched_parent = await self.enrich_record_hierarchy(
                            parent_reg, parent_rec, session, current_visited
                        )
                        record_data[parent_key] = enriched_parent

        return record_data

    async def get_allowed_parents_for_child_section(
        self,
        subject_register_id: str,
        subject_record_id: str,
        section_register_id: str
    ) -> AllowedParentsData:
        """
        Get allowed parent records for a child section.
        
        Given a subject record (e.g., FARMER) and a child section register (e.g., SEEDS),
        finds the parent register of that section (e.g., CROP) and returns all records
        from the parent register that are linked to the subject.

        Args:
            subject_register_id: The register we're starting from (e.g., FARMER)
            subject_record_id: The specific record (internal_record_id)
            section_register_id: The child section's register (e.g., SEEDS)

        Returns:
            AllowedParentsData containing parent register mnemonic and list of allowed parent records
        """
        empty_result = AllowedParentsData(
            register_mnemonic="",
            master_register_id=None,
            allowed_parents=[]
        )

        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            # 1. Validate subject register exists
            await self._validate_register_definition(subject_register_id, session)

            # 2. Get section register definition
            section_register: G2PRegisterDefinition = await self._validate_register_definition(
                section_register_id, session
            )

            # 3. Find parent register (master_register_id)
            parent_register_id = section_register.master_register_id
            if not parent_register_id:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.REGISTER_NOT_FOUND.value[1],
                    message=f"Section register {section_register_id} has no parent register"
                )

            parent_register: G2PRegisterDefinition = await self._validate_register_definition(
                parent_register_id, session
            )

            # 4. Get parent records linked to the subject using existing hierarchy traversal
            try:
                parent_records: list[RecordData] = await self.get_section_records(
                    subject_register_id,
                    subject_record_id,
                    parent_register_id,
                )
            except Exception:
                _logger.warning(
                    f"Could not retrieve parent records for subject_register_id={subject_register_id}, "
                    f"subject_record_id={subject_record_id}, parent_register_id={parent_register_id}"
                )
                return AllowedParentsData(
                    register_mnemonic=parent_register.register_mnemonic,
                    master_register_id=parent_register.master_register_id,
                    allowed_parents=[]
                )

            # 5. Transform to AllowedParentRecordData
            allowed_parents: list[AllowedParentRecordData] = []
            for record in parent_records:
                record_dict = record.model_dump()
                allowed_parents.append(
                    AllowedParentRecordData(
                        internal_record_id=record_dict.get('internal_record_id'),
                        record_name=record_dict.get('record_name')
                    )
                )

            return AllowedParentsData(
                register_mnemonic=parent_register.register_mnemonic,
                master_register_id=parent_register.master_register_id,
                allowed_parents=allowed_parents
            )
