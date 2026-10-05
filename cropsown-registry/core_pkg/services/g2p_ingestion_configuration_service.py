import logging
import uuid
from typing import Optional
import httpx

from openg2p_fastapi_common.service import BaseService
from openg2p_fastapi_common.context import dbengine

from openg2p_registry_core.models.g2p_intake_form_metadata import G2PIntakeFormDefinition
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select, func

from ..models import (
    IncomingModelKeyPath,
    IncomingModelRegisterSemanticPattern,
    IncomingModelSemanticPattern,
    IncomingTemplate,
    DataModel,
    SubscriptionActivityLog,
    G2PRegisterDefinition,
    G2PRegisterSection,
)
from ..schemas import (
    IncomingModelKeyPathPayload,
    IncomingModelKeyPathUpdatePayload,
    IncomingModelKeyPathData,
    IncomingModelKeyPathListData,
    IncomingModelSemanticPatternPayload,
    IncomingModelSemanticPatternUpdatePayload,
    IncomingModelSemanticPatternData,
    IncomingModelRegisterSemanticPatternPayload,
    IncomingModelRegisterSemanticPatternUpdatePayload,
    IncomingModelRegisterSemanticPatternData,
    IncomingTemplatePayload,
    IncomingTemplateUpdatePayload,
    IncomingTemplateData,
    SubscriptionActivityLogPayload,
    SubscriptionActivityLogData,
)
from .g2p_template_service import G2PTemplateService
from ..errors import G2PRegistryErrorCodes, G2PRegistryException

_logger = logging.getLogger("g2p-ingestion-configuration-service")


class G2PIngestionConfigurationService(BaseService):

    # IncomingModelKeyPath Methods
    async def create_incoming_key_path(
        self, pattern_payload: IncomingModelKeyPathPayload
    ) -> IncomingModelKeyPathData:
        """Create a new incoming key path"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._check_incoming_key_path_id_exists(
                session, pattern_payload.key_path_id
            )
            await self._validate_data_model_id_exists(
                session, pattern_payload.data_model_id
            )
            await self._check_incoming_key_path_data_model_exists(
                session, pattern_payload.data_model_id
            )
            pattern = IncomingModelKeyPath(
                data_model_id=pattern_payload.data_model_id,
                key_path_for_message_id=pattern_payload.key_path_for_message_id,
                key_path_for_sender=pattern_payload.key_path_for_sender,
                key_path_for_signature=pattern_payload.key_path_for_signature,
                key_path_for_signature_payload=pattern_payload.key_path_for_signature_payload,
                is_list=pattern_payload.is_list,
                key_path_for_list_elements=pattern_payload.key_path_for_list_elements,
            )
            session.add(pattern)
            await session.commit()
            await session.refresh(pattern)
            return IncomingModelKeyPathData.model_validate(pattern)


    async def get_all_incoming_key_paths(
        self, current_page: int, page_size: int
    ) -> tuple[list[IncomingModelKeyPathListData], int, int]:
        """Get paginated incoming key paths with data_model_mnemonic."""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            offset = (current_page - 1) * page_size
            total_items_result = await session.execute(
                select(func.count()).select_from(IncomingModelKeyPath)
            )
            total_items = total_items_result.scalar_one() or 0

            result = await session.execute(
                select(IncomingModelKeyPath)
                .order_by(IncomingModelKeyPath.key_path_id)
                .offset(offset)
                .limit(page_size)
            )
            key_paths = result.scalars().all()

            # Build list with data_model_mnemonic
            key_path_list: list[IncomingModelKeyPathListData] = []
            for key_path in key_paths:
                # Get data model to retrieve mnemonic
                data_model_result = await session.execute(
                    select(DataModel).where(DataModel.data_model_id == key_path.data_model_id)
                )
                data_model = data_model_result.scalar_one_or_none()
                data_model_mnemonic = data_model.data_model_mnemonic if data_model else ""

                key_path_list.append(IncomingModelKeyPathListData(
                    key_path_id=key_path.key_path_id,
                    data_model_id=key_path.data_model_id,
                    data_model_mnemonic=data_model_mnemonic,
                    is_list=key_path.is_list,
                ))
            number_of_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
            return key_path_list, total_items, number_of_pages

    async def get_incoming_key_path(self, key_path_id: str) -> IncomingModelKeyPathData:
        """Get incoming key path by ID"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            pattern_obj = await self._get_incoming_key_path(session, key_path_id)
            return IncomingModelKeyPathData.model_validate(pattern_obj)

    async def update_incoming_key_path(
        self, key_path_id: str, pattern_payload: IncomingModelKeyPathUpdatePayload
    ) -> IncomingModelKeyPathData:
        """Update incoming key path - only updates provided fields"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            pattern_obj = await self._get_incoming_key_path(session, key_path_id)

            if pattern_payload.key_path_for_message_id is not None:
                pattern_obj.key_path_for_message_id = pattern_payload.key_path_for_message_id
            if pattern_payload.key_path_for_sender is not None:
                pattern_obj.key_path_for_sender = pattern_payload.key_path_for_sender
            if pattern_payload.key_path_for_signature is not None:
                pattern_obj.key_path_for_signature = pattern_payload.key_path_for_signature
            if pattern_payload.key_path_for_signature_payload is not None:
                pattern_obj.key_path_for_signature_payload = (
                    pattern_payload.key_path_for_signature_payload
                )
            if pattern_payload.is_list is not None:
                pattern_obj.is_list = pattern_payload.is_list
            if pattern_payload.key_path_for_list_elements is not None:
                pattern_obj.key_path_for_list_elements = (
                    pattern_payload.key_path_for_list_elements
                )

            await session.commit()
            await session.refresh(pattern_obj)
            return IncomingModelKeyPathData.model_validate(pattern_obj)

    async def delete_incoming_key_path(self, key_path_id: str) -> IncomingModelKeyPathData:
        """Delete incoming key path and return deleted data."""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            pattern_obj = await self._get_incoming_key_path(session, key_path_id)
            deleted_pattern_data = IncomingModelKeyPathData.model_validate(pattern_obj)
            await session.delete(pattern_obj)
            await session.commit()
            return deleted_pattern_data

    async def _get_incoming_key_path(
        self, session: AsyncSession, key_path_id: str
    ) -> IncomingModelKeyPath:
        """Get incoming key path by ID - helper method"""
        pattern = await session.execute(
            select(IncomingModelKeyPath).where(
                IncomingModelKeyPath.key_path_id == key_path_id
            )
        )
        pattern_obj = pattern.scalar_one_or_none()
        if not pattern_obj:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.PATTERN_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.PATTERN_NOT_FOUND.value[0],
            )
        return pattern_obj

    async def _check_incoming_key_path_id_exists(
        self, session: AsyncSession, key_path_id: Optional[str]
    ) -> None:
        """Raise an exception when a provided key_path_id already exists."""
        if not key_path_id:
            return

        existing = await session.execute(
            select(IncomingModelKeyPath).where(
                IncomingModelKeyPath.key_path_id == key_path_id
            )
        )
        if existing.scalar_one_or_none():
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.PATTERN_ALREADY_EXISTS.value[1],
                message=G2PRegistryErrorCodes.PATTERN_ALREADY_EXISTS.value[0],
            )

    async def _validate_data_model_id_exists(
        self, session: AsyncSession, data_model_id: str
    ) -> DataModel:
        """Validate and return the data model for a given data_model_id."""
        existing = await session.execute(
            select(DataModel).where(DataModel.data_model_id == data_model_id)
        )
        existing = existing.scalar_one_or_none()
        if not existing:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.DATA_MODEL_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.DATA_MODEL_NOT_FOUND.value[0],
            )
        return existing
    
    async def _validate_register_id_exists(
        self, session: AsyncSession, register_id: str
    ) -> G2PRegisterDefinition:
        """Validate and return the register definition for a given register_id."""
        existing = await session.execute(
            select(G2PRegisterDefinition).where(G2PRegisterDefinition.register_id == register_id)
        )
        existing = existing.scalar_one_or_none()
        if not existing:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTER_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.REGISTER_NOT_FOUND.value[0],
            )
        return existing
    
    async def _validate_section_for_register(
        self, session: AsyncSession, section_id: str, register_id: str
    ) -> G2PRegisterSection:
        sec = (
            await session.execute(
                select(G2PRegisterSection).where(G2PRegisterSection.section_id == section_id)
            )
        ).scalar_one_or_none()
        if not sec or sec.register_id != register_id:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                message="Section not found or does not belong to the specified register.",
            )
        return sec

    async def _validate_intake_form_id_exists(
        self, session: AsyncSession, intake_form_id: str
    ) -> G2PIntakeFormDefinition:
        """Validate and return the intake form for a given intake_form_id."""
        existing = await session.execute(
            select(G2PIntakeFormDefinition).where(
                G2PIntakeFormDefinition.form_id == intake_form_id
            )
        )
        existing = existing.scalar_one_or_none()
        if not existing:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INTAKE_FORM_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.INTAKE_FORM_NOT_FOUND.value[0],
            )
        return existing

    async def _check_incoming_key_path_data_model_exists(
        self, session: AsyncSession, data_model_id: str
    ) -> None:
        """Raise an exception if an IncomingModelKeyPath already exists for the data model."""
        existing = await session.execute(
            select(IncomingModelKeyPath).where(
                IncomingModelKeyPath.data_model_id == data_model_id
            )
        )
        if existing.scalar_one_or_none():
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.PATTERN_ALREADY_EXISTS_FOR_DATA_MODEL.value[1],
                message=G2PRegistryErrorCodes.PATTERN_ALREADY_EXISTS_FOR_DATA_MODEL.value[0],
            )

    # IncomingModelSemanticPattern Methods
    async def create_semantic_pattern(
        self, pattern_payload: IncomingModelSemanticPatternPayload
    ) -> IncomingModelSemanticPatternData:
        """Create a new semantic pattern"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._validate_data_model_id_exists(session, pattern_payload.data_model_id)
            await self._validate_register_id_exists(session, pattern_payload.register_id)
            await self._validate_intake_form_id_exists(session, pattern_payload.intake_form_id)
            if pattern_payload.section_id:
                await self._validate_section_for_register(
                    session, pattern_payload.section_id, pattern_payload.register_id
                )
            enricher = pattern_payload.raw_payload_enricher_class or ""
            pattern = IncomingModelSemanticPattern(
                data_model_id=pattern_payload.data_model_id,
                register_id=pattern_payload.register_id,
                intake_form_id=pattern_payload.intake_form_id,
                section_id=pattern_payload.section_id,
                pattern_for_register=pattern_payload.pattern_for_register,
                pattern_for_intake_form=pattern_payload.pattern_for_intake_form,
                pattern_for_section=pattern_payload.pattern_for_section,
                key_path_for_business_payload=pattern_payload.key_path_for_business_payload,
                raw_payload_enricher_class=enricher,
            )
            session.add(pattern)
            await session.commit()
            await session.refresh(pattern)
            return await self._build_semantic_pattern_data_with_mnemonics(session, pattern)

    async def get_semantic_pattern(
        self, semantic_pattern_id: str
    ) -> IncomingModelSemanticPatternData:
        """Get semantic pattern by ID"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            pattern_obj = await self._get_semantic_pattern(session, semantic_pattern_id)
            return await self._build_semantic_pattern_data_with_mnemonics(session, pattern_obj)

    async def get_all_semantic_patterns(
        self, current_page: int, page_size: int
    ) -> tuple[list[IncomingModelSemanticPatternData], int, int]:
        """Get paginated semantic patterns."""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            offset = (current_page - 1) * page_size
            total_items_result = await session.execute(
                select(func.count()).select_from(IncomingModelSemanticPattern)
            )
            total_items = total_items_result.scalar_one() or 0

            result = await session.execute(
                select(IncomingModelSemanticPattern)
                .order_by(IncomingModelSemanticPattern.semantic_pattern_id)
                .offset(offset)
                .limit(page_size)
            )
            patterns = result.scalars().all()
            semantic_patterns: list[IncomingModelSemanticPatternData] = []
            for pattern in patterns:
                semantic_patterns.append(
                    await self._build_semantic_pattern_data_with_mnemonics(session, pattern)
                )
            number_of_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
            return semantic_patterns, total_items, number_of_pages

    async def update_semantic_pattern(
        self, semantic_pattern_id: str, pattern_payload: IncomingModelSemanticPatternUpdatePayload
    ) -> IncomingModelSemanticPatternData:
        """Update semantic pattern - only updates provided fields"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            pattern_obj = await self._get_semantic_pattern(session, semantic_pattern_id)

            if pattern_payload.section_id is not None:
                if pattern_payload.section_id:
                    await self._validate_section_for_register(
                        session, pattern_payload.section_id, pattern_obj.register_id
                    )
                pattern_obj.section_id = pattern_payload.section_id
            if pattern_payload.pattern_for_register is not None:
                pattern_obj.pattern_for_register = pattern_payload.pattern_for_register
            if pattern_payload.pattern_for_intake_form is not None:
                pattern_obj.pattern_for_intake_form = pattern_payload.pattern_for_intake_form
            if pattern_payload.pattern_for_section is not None:
                pattern_obj.pattern_for_section = pattern_payload.pattern_for_section
            if pattern_payload.key_path_for_business_payload is not None:
                pattern_obj.key_path_for_business_payload = pattern_payload.key_path_for_business_payload
            if pattern_payload.raw_payload_enricher_class is not None:
                pattern_obj.raw_payload_enricher_class = pattern_payload.raw_payload_enricher_class

            await session.commit()
            await session.refresh(pattern_obj)
            return await self._build_semantic_pattern_data_with_mnemonics(session, pattern_obj)

    async def delete_semantic_pattern(self, semantic_pattern_id: str) -> IncomingModelSemanticPatternData:
        """Delete semantic pattern by ID and return deleted data."""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            pattern_obj = await self._get_semantic_pattern(session, semantic_pattern_id)
            deleted_pattern_data = await self._build_semantic_pattern_data_with_mnemonics(
                session, pattern_obj
            )
            await session.delete(pattern_obj)
            await session.commit()
            return deleted_pattern_data

    async def _get_semantic_pattern(
        self, session: AsyncSession, semantic_pattern_id: str
    ) -> IncomingModelSemanticPattern:
        """Get semantic pattern by ID - helper method"""
        pattern = await session.execute(
            select(IncomingModelSemanticPattern).where(
                IncomingModelSemanticPattern.semantic_pattern_id == semantic_pattern_id
            )
        )
        pattern_obj = pattern.scalar_one_or_none()
        if not pattern_obj:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SEMANTIC_PATTERN_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.SEMANTIC_PATTERN_NOT_FOUND.value[0],
            )
        return pattern_obj

    async def _build_semantic_pattern_data_with_mnemonics(
        self, session: AsyncSession, pattern_obj: IncomingModelSemanticPattern
    ) -> IncomingModelSemanticPatternData:
        """Build semantic pattern response with related mnemonics."""
        data_model_obj = await self._validate_data_model_id_exists(
            session, pattern_obj.data_model_id
        )
        register_obj = await self._validate_register_id_exists(
            session, pattern_obj.register_id
        )
        intake_form_obj = await self._validate_intake_form_id_exists(
            session, pattern_obj.intake_form_id
        )
        section_mnemonic: str | None = None
        if pattern_obj.section_id:
            section_obj = await self._validate_section_for_register(
                session, pattern_obj.section_id, pattern_obj.register_id
            )
            section_mnemonic = section_obj.section_mnemonic

        return IncomingModelSemanticPatternData(
            semantic_pattern_id=pattern_obj.semantic_pattern_id,
            data_model_id=pattern_obj.data_model_id,
            data_model_mnemonic=data_model_obj.data_model_mnemonic,
            register_id=pattern_obj.register_id,
            register_mnemonic=register_obj.register_mnemonic,
            intake_form_id=pattern_obj.intake_form_id,
            intake_form_mnemonic=intake_form_obj.form_mnemonic,
            section_id=pattern_obj.section_id,
            section_mnemonic=section_mnemonic,
            pattern_for_register=pattern_obj.pattern_for_register,
            pattern_for_intake_form=pattern_obj.pattern_for_intake_form,
            pattern_for_section=pattern_obj.pattern_for_section,
            key_path_for_business_payload=pattern_obj.key_path_for_business_payload,
            raw_payload_enricher_class=pattern_obj.raw_payload_enricher_class,
        )

    async def create_register_semantic_pattern(
        self, pattern_payload: IncomingModelRegisterSemanticPatternPayload
    ) -> IncomingModelRegisterSemanticPatternData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._validate_data_model_id_exists(session, pattern_payload.data_model_id)
            await self._validate_register_id_exists(session, pattern_payload.register_id)
            pattern = IncomingModelRegisterSemanticPattern(
                data_model_id=pattern_payload.data_model_id,
                register_id=pattern_payload.register_id,
                pattern_for_register=pattern_payload.pattern_for_register,
                key_path_for_record_identifier=pattern_payload.key_path_for_record_identifier,
            )
            session.add(pattern)
            await session.commit()
            await session.refresh(pattern)
            return await self._build_register_semantic_pattern_data(session, pattern)

    async def get_register_semantic_pattern(
        self, register_semantic_pattern_id: str
    ) -> IncomingModelRegisterSemanticPatternData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            pattern_obj = await self._get_register_semantic_pattern(session, register_semantic_pattern_id)
            return await self._build_register_semantic_pattern_data(session, pattern_obj)

    async def get_all_register_semantic_patterns(
        self, current_page: int, page_size: int
    ) -> tuple[list[IncomingModelRegisterSemanticPatternData], int, int]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            offset = (current_page - 1) * page_size
            total_items_result = await session.execute(
                select(func.count()).select_from(IncomingModelRegisterSemanticPattern)
            )
            total_items = total_items_result.scalar_one() or 0
            result = await session.execute(
                select(IncomingModelRegisterSemanticPattern)
                .order_by(IncomingModelRegisterSemanticPattern.register_semantic_pattern_id)
                .offset(offset)
                .limit(page_size)
            )
            patterns = result.scalars().all()
            out: list[IncomingModelRegisterSemanticPatternData] = []
            for pattern in patterns:
                out.append(await self._build_register_semantic_pattern_data(session, pattern))
            number_of_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
            return out, total_items, number_of_pages

    async def update_register_semantic_pattern(
        self, pattern_payload: IncomingModelRegisterSemanticPatternUpdatePayload
    ) -> IncomingModelRegisterSemanticPatternData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            pattern_obj = await self._get_register_semantic_pattern(
                session, pattern_payload.register_semantic_pattern_id
            )
            if pattern_payload.pattern_for_register is not None:
                pattern_obj.pattern_for_register = pattern_payload.pattern_for_register
            if pattern_payload.key_path_for_record_identifier is not None:
                pattern_obj.key_path_for_record_identifier = pattern_payload.key_path_for_record_identifier
            await session.commit()
            await session.refresh(pattern_obj)
            return await self._build_register_semantic_pattern_data(session, pattern_obj)

    async def delete_register_semantic_pattern(
        self, register_semantic_pattern_id: str
    ) -> IncomingModelRegisterSemanticPatternData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            pattern_obj = await self._get_register_semantic_pattern(session, register_semantic_pattern_id)
            deleted = await self._build_register_semantic_pattern_data(session, pattern_obj)
            await session.delete(pattern_obj)
            await session.commit()
            return deleted

    async def _get_register_semantic_pattern(
        self, session: AsyncSession, register_semantic_pattern_id: str
    ) -> IncomingModelRegisterSemanticPattern:
        pattern = await session.execute(
            select(IncomingModelRegisterSemanticPattern).where(
                IncomingModelRegisterSemanticPattern.register_semantic_pattern_id
                == register_semantic_pattern_id
            )
        )
        pattern_obj = pattern.scalar_one_or_none()
        if not pattern_obj:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SEMANTIC_PATTERN_NOT_FOUND.value[1],
                message="Register semantic pattern not found.",
            )
        return pattern_obj

    async def _build_register_semantic_pattern_data(
        self, session: AsyncSession, pattern_obj: IncomingModelRegisterSemanticPattern
    ) -> IncomingModelRegisterSemanticPatternData:
        data_model_obj = await self._validate_data_model_id_exists(session, pattern_obj.data_model_id)
        register_obj = await self._validate_register_id_exists(session, pattern_obj.register_id)
        return IncomingModelRegisterSemanticPatternData(
            register_semantic_pattern_id=pattern_obj.register_semantic_pattern_id,
            data_model_id=pattern_obj.data_model_id,
            data_model_mnemonic=data_model_obj.data_model_mnemonic,
            register_id=pattern_obj.register_id,
            register_mnemonic=register_obj.register_mnemonic,
            pattern_for_register=pattern_obj.pattern_for_register,
            key_path_for_record_identifier=pattern_obj.key_path_for_record_identifier,
        )

    # IncomingTemplate Methods
    async def create_template(
        self, template_payload: IncomingTemplatePayload
    ) -> IncomingTemplateData:
        """Create a new template (stores pre-uploaded template_document_id)."""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._validate_register_id_exists(session, template_payload.register_id)
            await self._validate_data_model_id_exists(session, template_payload.data_model_id)
            await self._check_incoming_template_exists(session, template_payload)
            await self._validate_template_document_id(
                session, template_payload.template_document_id
            )

            template: IncomingTemplate = IncomingTemplate(
                register_id=template_payload.register_id,
                data_model_id=template_payload.data_model_id,
                template_document_id=template_payload.template_document_id,
                jsonld_expansion_required=template_payload.jsonld_expansion_required,
            )
            session.add(template)
            await session.commit()
            await session.refresh(template)
            return await self._build_template_data_with_mnemonics(session, template)

    async def get_template(self, template_id: str) -> IncomingTemplateData:
        """Get template by ID"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            template_obj: IncomingTemplate = await self._get_incoming_template(session, template_id)
            return await self._build_template_data_with_mnemonics(session, template_obj)

    async def get_all_templates(
        self, current_page: int, page_size: int
    ) -> tuple[list[IncomingTemplateData], int, int]:
        """Get paginated templates."""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            offset = (current_page - 1) * page_size
            total_items_result = await session.execute(
                select(func.count()).select_from(IncomingTemplate)
            )
            total_items = total_items_result.scalar_one() or 0

            result = await session.execute(
                select(IncomingTemplate)
                .order_by(IncomingTemplate.template_id)
                .offset(offset)
                .limit(page_size)
            )
            templates = result.scalars().all()

            template_data_list: list[IncomingTemplateData] = []
            for template in templates:
                template_data_list.append(
                    await self._build_template_data_with_mnemonics(session, template)
                )
            number_of_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
            return template_data_list, total_items, number_of_pages

    async def update_template(
        self, template_update_payload: IncomingTemplateUpdatePayload
    ) -> IncomingTemplateData:
        """Update template - only updates provided fields"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            template_obj: IncomingTemplate = await self._get_incoming_template(
                session, template_update_payload.template_id
            )

            if template_update_payload.template_document_id is not None:
                await self._validate_template_document_id(
                    session, template_update_payload.template_document_id
                )
                old_document_id = template_obj.template_document_id
                if (
                    old_document_id
                    and old_document_id != template_update_payload.template_document_id
                ):
                    await self._delete_template_file(old_document_id)
                template_obj.template_document_id = template_update_payload.template_document_id
            if template_update_payload.jsonld_expansion_required is not None:
                template_obj.jsonld_expansion_required = (
                    template_update_payload.jsonld_expansion_required
                )

            await session.commit()
            await session.refresh(template_obj)
            return await self._build_template_data_with_mnemonics(session, template_obj)

    async def delete_template(self, template_id: str) -> IncomingTemplateData:
        """Delete template by ID and return deleted data."""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            template_obj: IncomingTemplate = await self._get_incoming_template(session, template_id)
            deleted_template_data = await self._build_template_data_with_mnemonics(
                session, template_obj
            )
            document_id = template_obj.template_document_id
            await session.delete(template_obj)
            await session.commit()
            if document_id:
                await self._delete_template_file(document_id)
            return deleted_template_data

    async def _get_incoming_template(self, session: AsyncSession, template_id: str) -> IncomingTemplate:
        """Get incoming template by ID - helper method"""
        if not template_id:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                message=G2PRegistryErrorCodes.INVALID_REQUEST.value[0],
            )
        template = await session.execute(
            select(IncomingTemplate).where(IncomingTemplate.template_id == template_id)
        )
        template_obj: Optional[IncomingTemplate] = template.scalar_one_or_none()
        if not template_obj:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.TEMPLATE_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.TEMPLATE_NOT_FOUND.value[0],
            )
        return template_obj

    async def _check_incoming_template_exists(
        self, session: AsyncSession, template_payload: IncomingTemplatePayload
    ) -> None:
        """Check if template with same data_model_id and register_id already exists."""
        if not template_payload.data_model_id or not template_payload.register_id:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                message=G2PRegistryErrorCodes.INVALID_REQUEST.value[0],
            )
        existing_template = await session.execute(
            select(IncomingTemplate).where(
                IncomingTemplate.data_model_id == template_payload.data_model_id,
                IncomingTemplate.register_id == template_payload.register_id,
            )
        )
        existing_template_obj: Optional[IncomingTemplate] = existing_template.scalar_one_or_none()
        if existing_template_obj:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.TEMPLATE_ALREADY_EXISTS.value[1],
                message=G2PRegistryErrorCodes.TEMPLATE_ALREADY_EXISTS.value[0],
            )

    async def _build_template_data_with_mnemonics(
        self, session: AsyncSession, template_obj: IncomingTemplate
    ) -> IncomingTemplateData:
        """Build incoming template response with register and data model mnemonics."""
        register_obj = await self._validate_register_id_exists(session, template_obj.register_id)
        data_model_obj = await self._validate_data_model_id_exists(session, template_obj.data_model_id)

        return IncomingTemplateData(
            template_id=template_obj.template_id,
            register_id=template_obj.register_id,
            register_mnemonic=register_obj.register_mnemonic,
            data_model_id=template_obj.data_model_id,
            data_model_mnemonic=data_model_obj.data_model_mnemonic,
            template_document_id=template_obj.template_document_id,
            jsonld_expansion_required=template_obj.jsonld_expansion_required,
        )

    # SubscriptionActivityLog Methods
    async def create_subscription_activity_log(
        self, subscription_activity_log_payload: SubscriptionActivityLogPayload
    ) -> SubscriptionActivityLogData:
        """Create a new subscription activity log after calling the subscription URL"""
        # Call the subscription URL with header and payload
        response_data = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    subscription_activity_log_payload.subscription_url,
                    headers=subscription_activity_log_payload.header or {},
                    json=subscription_activity_log_payload.payload or {},
                    timeout=30.0
                )
                response.raise_for_status()  # Raise exception for non-2xx status codes
                response_data = response.json() if response.text else None
        except Exception as error:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.SUBSCRIPTION_CALL_FAILED.value[1],
                message=f"Failed to call subscription URL: {str(error)}"
            )

        # Only store the activity log if the call was successful
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            activity_log = SubscriptionActivityLog(
                is_unsubscribe=subscription_activity_log_payload.is_unsubscribe,
                description=subscription_activity_log_payload.description,
                partner_id=subscription_activity_log_payload.partner_id,
                subscription_url=subscription_activity_log_payload.subscription_url,
                registry_callback_url=subscription_activity_log_payload.registry_callback_url,
                header=subscription_activity_log_payload.header,
                payload=subscription_activity_log_payload.payload,
                response=response_data,
            )
            session.add(activity_log)
            await session.commit()
            await session.refresh(activity_log)
            return SubscriptionActivityLogData.model_validate(activity_log)

    async def get_subscription_activity_logs_by_partner(
        self, partner_id: str
    ) -> list[SubscriptionActivityLogData]:
        """Get all subscription activity logs for a partner"""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            result = await session.execute(
                select(SubscriptionActivityLog).where(
                    SubscriptionActivityLog.partner_id == partner_id
                ).order_by(SubscriptionActivityLog.date_time.desc())
            )
            activity_logs = result.scalars().all()
            return [SubscriptionActivityLogData.model_validate(log) for log in activity_logs]

    async def get_all_subscription_activity_logs(
        self, current_page: int, page_size: int
    ) -> tuple[list[SubscriptionActivityLogData], int, int]:
        """Get paginated subscription activity logs."""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            offset = (current_page - 1) * page_size
            total_items_result = await session.execute(
                select(func.count()).select_from(SubscriptionActivityLog)
            )
            total_items = total_items_result.scalar_one() or 0

            result = await session.execute(
                select(SubscriptionActivityLog).order_by(
                    SubscriptionActivityLog.date_time.desc()
                )
                .offset(offset)
                .limit(page_size)
            )
            activity_logs = result.scalars().all()
            number_of_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
            return [SubscriptionActivityLogData.model_validate(log) for log in activity_logs], total_items, number_of_pages

    async def _delete_template_file(self, template_document_id: str) -> None:
        g2p_template_service = G2PTemplateService.get_component()
        return await g2p_template_service.delete_template_file(template_document_id)

    async def _validate_template_document_id(self, session, document_id: str) -> None:
        from .g2p_document_service import G2PDocumentService

        await G2PDocumentService.get_component().validate_template_documents_exist(
            session, [document_id]
        )
