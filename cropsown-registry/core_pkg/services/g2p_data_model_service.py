import logging
import uuid

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..models.enum import DocumentBucket
from ..models import DataModel, G2PRegistryDocument
from ..schemas import DataModelData, DataModelPayload, DataModelUpdatePayload

_logger = logging.getLogger("g2p-data-model-service")


class G2PDataModelService(BaseService):
    async def create_data_model(self, data_model_payload: DataModelPayload) -> DataModelData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._ensure_data_model_mnemonic_not_exists(
                session, data_model_payload.data_model_mnemonic
            )
            if data_model_payload.response_template_document_id:
                await self._validate_template_document_id(
                    session, data_model_payload.response_template_document_id
                )

            data_model = DataModel(
                data_model_id=data_model_payload.data_model_id or str(uuid.uuid4()),
                data_model_mnemonic=data_model_payload.data_model_mnemonic,
                pattern_for_data_model=data_model_payload.pattern_for_data_model,
                response_template_document_id=data_model_payload.response_template_document_id,
                is_active=data_model_payload.is_active,
            )
            session.add(data_model)
            await session.commit()
            await session.refresh(data_model)
            return DataModelData.model_validate(data_model)

    async def get_data_model(self, data_model_id: str) -> DataModelData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            data_model = await self._get_data_model(session, data_model_id)
            return DataModelData.model_validate(data_model)

    async def get_all_data_models(
        self, current_page: int, page_size: int
    ) -> tuple[list[DataModelData], int, int]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            offset = (current_page - 1) * page_size
            total_items_result = await session.execute(
                select(func.count()).select_from(DataModel)
            )
            total_items = total_items_result.scalar_one() or 0

            result = await session.execute(
                select(DataModel)
                .order_by(DataModel.data_model_id)
                .offset(offset)
                .limit(page_size)
            )
            data_models = result.scalars().all()
            number_of_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
            return [DataModelData.model_validate(data_model) for data_model in data_models], total_items, number_of_pages

    async def update_data_model(
        self, data_model_id: str, data_model_payload: DataModelUpdatePayload
    ) -> DataModelData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            data_model = await self._get_data_model(session, data_model_id)

            if (
                data_model_payload.data_model_mnemonic is not None
                and data_model_payload.data_model_mnemonic != data_model.data_model_mnemonic
            ):
                await self._ensure_data_model_mnemonic_not_exists(
                    session, data_model_payload.data_model_mnemonic
                )
                data_model.data_model_mnemonic = data_model_payload.data_model_mnemonic

            if data_model_payload.pattern_for_data_model is not None:
                data_model.pattern_for_data_model = data_model_payload.pattern_for_data_model
            if data_model_payload.response_template_document_id is not None:
                if data_model_payload.response_template_document_id:
                    await self._validate_template_document_id(
                        session, data_model_payload.response_template_document_id
                    )
                if (
                    data_model.response_template_document_id
                    and data_model.response_template_document_id
                    != data_model_payload.response_template_document_id
                ):
                    await self._delete_template_if_exists(
                        session, data_model.response_template_document_id
                    )
                data_model.response_template_document_id = data_model_payload.response_template_document_id
            if data_model_payload.is_active is not None:
                data_model.is_active = data_model_payload.is_active

            await session.commit()
            await session.refresh(data_model)
            return DataModelData.model_validate(data_model)

    async def delete_data_model(self, data_model_id: str) -> DataModelData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            data_model = await self._get_data_model(session, data_model_id)
            data_model_data = DataModelData.model_validate(data_model)
            if data_model.response_template_document_id:
                await self._delete_template_if_exists(
                    session, data_model.response_template_document_id
                )
            await session.delete(data_model)
            await session.commit()
            return data_model_data

    async def _delete_template_if_exists(
        self, session: AsyncSession, document_id: str
    ) -> None:
        from ..helpers.document import get_document_handler

        result = await session.execute(
            select(G2PRegistryDocument).where(
                G2PRegistryDocument.document_id == document_id,
                G2PRegistryDocument.bucket == DocumentBucket.TEMPLATES,
            )
        )
        template_document_obj = result.scalar_one_or_none()
        if not template_document_obj:
            return

        get_document_handler().delete(
            template_document_obj.document_store_id,
            template_document_obj.bucket,
        )
        await session.delete(template_document_obj)

    async def _validate_template_document_id(self, session, document_id: str) -> None:
        from .g2p_document_service import G2PDocumentService

        await G2PDocumentService.get_component().validate_template_documents_exist(
            session, [document_id]
        )

    async def _ensure_data_model_mnemonic_not_exists(self, session, data_model_mnemonic: str) -> None:
        existing = await session.execute(
            select(DataModel).where(DataModel.data_model_mnemonic == data_model_mnemonic)
        )
        if existing.scalar_one_or_none():
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.DATA_MODEL_ALREADY_EXISTS.value[1],
                message=G2PRegistryErrorCodes.DATA_MODEL_ALREADY_EXISTS.value[0],
            )

    async def _get_data_model(self, session, data_model_id: str) -> DataModel:
        data_model = await session.execute(
            select(DataModel).where(DataModel.data_model_id == data_model_id)
        )
        data_model_obj = data_model.scalar_one_or_none()
        if not data_model_obj:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.DATA_MODEL_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.DATA_MODEL_NOT_FOUND.value[0],
            )
        return data_model_obj
