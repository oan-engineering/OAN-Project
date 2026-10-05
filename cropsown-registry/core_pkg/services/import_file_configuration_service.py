import logging
import uuid
from typing import List, Optional, Tuple

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..models import G2PRegisterDefinition, G2PRegistryImportFileConfiguration
from ..schemas import ImportFileConfigurationData

_logger = logging.getLogger("import-file-configuration-service")


class ImportFileConfigurationService(BaseService):
    async def get_import_file_configuration_for_register(
        self,
        register_id: str,
        current_page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Tuple[List[ImportFileConfigurationData], int]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._validate_register_exists(register_id, session)

            base_query = select(G2PRegistryImportFileConfiguration).where(
                G2PRegistryImportFileConfiguration.register_id == register_id
            )
            total_items = (
                await session.execute(
                    select(func.count()).select_from(base_query.subquery())
                )
            ).scalar_one()

            query = base_query
            if current_page is not None and page_size is not None:
                offset = (current_page - 1) * page_size
                query = query.offset(offset).limit(page_size)

            import_file_configurations = (await session.execute(query)).scalars().all()

            _logger.info(
                "Got %s import-file configurations for register_id=%s (total=%s)",
                len(import_file_configurations),
                register_id,
                total_items,
            )
            return [ImportFileConfigurationData.model_validate(import_file_configuration) for import_file_configuration in import_file_configurations], total_items

    async def get_all_import_file_configurations(
        self,
        current_page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Tuple[List[ImportFileConfigurationData], int]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            base_query = select(G2PRegistryImportFileConfiguration)
            total_items = (
                await session.execute(
                    select(func.count()).select_from(base_query.subquery())
                )
            ).scalar_one()

            query = base_query
            if current_page is not None and page_size is not None:
                offset = (current_page - 1) * page_size
                query = query.offset(offset).limit(page_size)

            import_file_configurations = (await session.execute(query)).scalars().all()

            _logger.info(
                "Got %s import-file configurations (total=%s)",
                len(import_file_configurations),
                total_items,
            )
            return [ImportFileConfigurationData.model_validate(import_file_configuration) for import_file_configuration in import_file_configurations], total_items

    async def create_import_file_configuration(
        self,
        register_id: str,
        form_id: str,
        data_model_id: str,
        import_file_template_mnemonic: str,
        import_file_template_description: str,
    ) -> List[ImportFileConfigurationData]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._validate_register_exists(register_id, session)

            import_file_configuration = G2PRegistryImportFileConfiguration(
                import_file_configuration_id=str(uuid.uuid4()),
                register_id=register_id,
                form_id=form_id,
                data_model_id=data_model_id,
                import_file_template_mnemonic=import_file_template_mnemonic,
                import_file_template_description=import_file_template_description,
            )
            session.add(import_file_configuration)
            await session.commit()
            return [ImportFileConfigurationData.model_validate(import_file_configuration)]

    async def update_import_file_configuration(
        self,
        import_file_configuration_id: str,
        form_id: Optional[str] = None,
        data_model_id: Optional[str] = None,
        import_file_template_mnemonic: Optional[str] = None,
        import_file_template_description: Optional[str] = None,
    ) -> List[ImportFileConfigurationData]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            import_file_configuration = await self._get_import_file_configuration(
                import_file_configuration_id, session
            )

            if form_id is not None:
                import_file_configuration.form_id = form_id
            if data_model_id is not None:
                import_file_configuration.data_model_id = data_model_id
            if import_file_template_mnemonic is not None:
                import_file_configuration.import_file_template_mnemonic = import_file_template_mnemonic
            if import_file_template_description is not None:
                import_file_configuration.import_file_template_description = import_file_template_description

            await session.commit()
            await session.refresh(import_file_configuration)
            return [ImportFileConfigurationData.model_validate(import_file_configuration)]

    async def delete_import_file_configuration(
        self, import_file_configuration_id: str
    ) -> List[ImportFileConfigurationData]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            import_file_configuration = await self._get_import_file_configuration(
                import_file_configuration_id, session
            )
            data = ImportFileConfigurationData.model_validate(import_file_configuration)
            await session.delete(import_file_configuration)
            await session.commit()
            return [data]

    async def _validate_register_exists(self, register_id: str, session: AsyncSession):
        register_definition = await session.get(G2PRegisterDefinition, register_id)
        if not register_definition:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTER_NOT_FOUND.value[1],
                message=f"Register with id {register_id} not found",
            )

    async def _get_import_file_configuration(
        self, import_file_configuration_id: str, session: AsyncSession
    ) -> G2PRegistryImportFileConfiguration:
        import_file_configuration = await session.get(
            G2PRegistryImportFileConfiguration, import_file_configuration_id
        )
        if not import_file_configuration:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.IMPORT_FILE_CONFIGURATION_NOT_FOUND.value[1],
                message=(
                    f"Import file configuration with id "
                    f"{import_file_configuration_id} not found"
                ),
            )
        return import_file_configuration
