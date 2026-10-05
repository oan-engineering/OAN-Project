import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService

from ..models import (
    G2PIntakeFormDefinition,
    G2PIntakeFormUITab,
    G2PIntakeFormUITabSection,
    G2PRegisterDefinition,
    G2PRegisterSection,
    RegisterPurposeEnum,
)
from ..schemas import (
    IntakeFormDefinitionData,
    IntakeFormIdData,
    IntakeFormRenderedData,
    IntakeFormRenderedSectionData,
    IntakeFormRenderedTabData,
    IntakeFormTabIdData,
    IntakeFormTabSectionIdData,
    IntakeFormUITabData,
    IntakeFormUITabSectionData,
)
from .g2p_register_metadata_service import G2PRegisterMetadataService

_logger = logging.getLogger("g2p-intake-form-metadata-service")


class G2PIntakeFormMetadataService(BaseService):
    async def create_intake_form(
        self,
        register_id: str,
        form_mnemonic: str,
        form_description: str | None = None,
        number_of_verifications: int = 0,
        used_only_in_ingestion_pipeline: bool = False,
    ) -> IntakeFormIdData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._validate_register_for_intake_form_creation(register_id, session)

            intake_form = G2PIntakeFormDefinition(
                register_id=register_id,
                form_mnemonic=form_mnemonic,
                form_description=form_description,
                number_of_verifications=number_of_verifications,
                used_only_in_ingestion_pipeline=used_only_in_ingestion_pipeline,
            )
            session.add(intake_form)
            await session.commit()
            await session.refresh(intake_form)
            return IntakeFormIdData(form_id=intake_form.form_id)

    async def update_intake_form(
        self,
        form_id: str,
        form_mnemonic: str | None = None,
        form_description: str | None = None,
        number_of_verifications: int | None = None,
        used_only_in_ingestion_pipeline: bool | None = None,
    ) -> IntakeFormIdData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            intake_form = await self._validate_intake_form(form_id, session)

            if form_mnemonic is not None:
                intake_form.form_mnemonic = form_mnemonic
            if form_description is not None:
                intake_form.form_description = form_description
            if number_of_verifications is not None:
                intake_form.number_of_verifications = number_of_verifications
            if used_only_in_ingestion_pipeline is not None:
                intake_form.used_only_in_ingestion_pipeline = used_only_in_ingestion_pipeline

            await session.commit()
            return IntakeFormIdData(form_id=intake_form.form_id)

    async def delete_intake_form(self, form_id: str) -> None:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            intake_form = await self._validate_intake_form(form_id, session)

            tabs = (
                await session.execute(select(G2PIntakeFormUITab).where(G2PIntakeFormUITab.form_id == form_id))
            ).scalars().all()

            tab_ids = [tab.tab_id for tab in tabs]
            if tab_ids:
                tab_sections = (
                    await session.execute(
                        select(G2PIntakeFormUITabSection).where(G2PIntakeFormUITabSection.tab_id.in_(tab_ids))
                    )
                ).scalars().all()
                for tab_section in tab_sections:
                    await session.delete(tab_section)

            for tab in tabs:
                await session.delete(tab)

            await session.delete(intake_form)
            await session.commit()

    async def get_all_intake_forms(
        self,
        register_id: str | None = None,
        current_page: int | None = None,
        page_size: int | None = None,
        used_only_in_ingestion_pipeline: bool | None = None,
    ) -> tuple[list[IntakeFormDefinitionData], int]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            query = (
                select(
                    G2PIntakeFormDefinition,
                    G2PRegisterDefinition.register_mnemonic,
                )
                .join(
                    G2PRegisterDefinition,
                    G2PIntakeFormDefinition.register_id == G2PRegisterDefinition.register_id,
                    isouter=True,
                )
                .order_by(
                    G2PIntakeFormDefinition.form_mnemonic.asc(),
                    G2PIntakeFormDefinition.form_id.asc(),
                )
            )
            count_query = select(func.count()).select_from(G2PIntakeFormDefinition)

            if register_id is not None:
                await self._validate_register(register_id, session)
                query = query.where(G2PIntakeFormDefinition.register_id == register_id)
                count_query = count_query.where(G2PIntakeFormDefinition.register_id == register_id)

            if used_only_in_ingestion_pipeline is not None:
                query = query.where(G2PIntakeFormDefinition.used_only_in_ingestion_pipeline.is_(used_only_in_ingestion_pipeline))
                count_query = count_query.where(G2PIntakeFormDefinition.used_only_in_ingestion_pipeline.is_(used_only_in_ingestion_pipeline))

            query = self._apply_pagination(query, current_page, page_size)

            rows = (await session.execute(query)).all()
            total_items = (await session.execute(count_query)).scalar_one()

            return [
                IntakeFormDefinitionData(
                    form_id=intake_form.form_id,
                    register_id=intake_form.register_id,
                    form_mnemonic=intake_form.form_mnemonic,
                    form_description=intake_form.form_description,
                    number_of_verifications=intake_form.number_of_verifications,
                    used_only_in_ingestion_pipeline=intake_form.used_only_in_ingestion_pipeline,
                    register_mnemonic=register_mnemonic,
                )
                for intake_form, register_mnemonic in rows
            ], total_items

    async def get_intake_form(self, form_id: str) -> IntakeFormDefinitionData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            row = (
                await session.execute(
                    select(
                        G2PIntakeFormDefinition,
                        G2PRegisterDefinition.register_mnemonic,
                    )
                    .join(
                        G2PRegisterDefinition,
                        G2PIntakeFormDefinition.register_id == G2PRegisterDefinition.register_id,
                        isouter=True,
                    )
                    .where(G2PIntakeFormDefinition.form_id == form_id)
                )
            ).first()

            if row is None:
                raise ValueError(f"Intake form with form_id '{form_id}' not found")

            intake_form, register_mnemonic = row
            return IntakeFormDefinitionData(
                form_id=intake_form.form_id,
                register_id=intake_form.register_id,
                form_mnemonic=intake_form.form_mnemonic,
                form_description=intake_form.form_description,
                number_of_verifications=intake_form.number_of_verifications,
                used_only_in_ingestion_pipeline=intake_form.used_only_in_ingestion_pipeline,
                register_mnemonic=register_mnemonic,
            )

    async def render_intake_form(self, form_id: str) -> IntakeFormRenderedData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            intake_form = await self._validate_intake_form(form_id, session)

            tabs = (
                await session.execute(
                    select(G2PIntakeFormUITab)
                    .where(G2PIntakeFormUITab.form_id == form_id)
                    .order_by(G2PIntakeFormUITab.tab_order.asc())
                )
            ).scalars().all()

            rendered_tabs: list[IntakeFormRenderedTabData] = []
            for tab in tabs:
                rows = (
                    await session.execute(
                        select(G2PIntakeFormUITabSection, G2PRegisterSection)
                        .join(
                            G2PRegisterSection,
                            G2PIntakeFormUITabSection.section_id == G2PRegisterSection.section_id,
                            isouter=True,
                        )
                        .where(G2PIntakeFormUITabSection.tab_id == tab.tab_id)
                        .order_by(G2PIntakeFormUITabSection.section_order.asc())
                    )
                ).all()

                rendered_sections: list[IntakeFormRenderedSectionData] = []
                for tab_section, section in rows:
                    if section is None:
                        continue
                    section_data = await G2PRegisterMetadataService.get_component().build_section_data(
                        section=section,
                        session=session,
                        include_ui_schema=True,
                        include_register_purpose=True,
                        include_register_relation=True,
                        register_id_for_relation=intake_form.register_id,
                    )
                    rendered_sections.append(
                        IntakeFormRenderedSectionData(
                            **section_data.model_dump(),
                            tab_section_id=tab_section.tab_section_id,
                            section_order=tab_section.section_order,
                        )
                    )

                rendered_tabs.append(
                    IntakeFormRenderedTabData(
                        tab_id=tab.tab_id,
                        form_id=tab.form_id,
                        tab_label=tab.tab_label,
                        tab_order=tab.tab_order,
                        sections=rendered_sections,
                    )
                )

            return IntakeFormRenderedData(
                form_id=intake_form.form_id,
                register_id=intake_form.register_id,
                form_mnemonic=intake_form.form_mnemonic,
                form_description=intake_form.form_description,
                number_of_verifications=intake_form.number_of_verifications,
                used_only_in_ingestion_pipeline=intake_form.used_only_in_ingestion_pipeline,
                tabs=rendered_tabs,
            )

    async def create_tab(
        self,
        form_id: str,
        tab_label: str,
        tab_order: int = 0,
    ) -> IntakeFormTabIdData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._validate_intake_form(form_id, session)
            tab = G2PIntakeFormUITab(
                form_id=form_id,
                tab_label=tab_label,
                tab_order=tab_order,
            )
            session.add(tab)
            await session.commit()
            await session.refresh(tab)
            return IntakeFormTabIdData(tab_id=tab.tab_id)

    async def delete_tab(self, tab_id: str) -> None:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            tab = await self._validate_tab(tab_id, session)
            tab_sections = (
                await session.execute(
                    select(G2PIntakeFormUITabSection).where(G2PIntakeFormUITabSection.tab_id == tab_id)
                )
            ).scalars().all()
            for tab_section in tab_sections:
                await session.delete(tab_section)

            await session.delete(tab)
            await session.commit()

    async def update_tab(
        self,
        tab_id: str,
        tab_label: str | None = None,
        tab_order: int | None = None,
    ) -> IntakeFormTabIdData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            tab = await self._validate_tab(tab_id, session)

            if tab_label is not None:
                tab.tab_label = tab_label
            if tab_order is not None:
                tab.tab_order = tab_order

            await session.commit()
            return IntakeFormTabIdData(tab_id=tab.tab_id)

    async def get_tab(self, tab_id: str) -> IntakeFormUITabData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            tab = await self._validate_tab(tab_id, session)
            return IntakeFormUITabData(
                tab_id=tab.tab_id,
                form_id=tab.form_id,
                tab_label=tab.tab_label,
                tab_order=tab.tab_order,
            )

    async def get_all_tabs(
        self,
        form_id: str | None = None,
        current_page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[IntakeFormUITabData], int]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            query = select(G2PIntakeFormUITab).order_by(
                G2PIntakeFormUITab.tab_order.asc(),
                G2PIntakeFormUITab.tab_label.asc(),
                G2PIntakeFormUITab.tab_id.asc(),
            )
            count_query = select(func.count()).select_from(G2PIntakeFormUITab)

            if form_id is not None:
                await self._validate_intake_form(form_id, session)
                query = query.where(G2PIntakeFormUITab.form_id == form_id)
                count_query = count_query.where(G2PIntakeFormUITab.form_id == form_id)

            query = self._apply_pagination(query, current_page, page_size)

            tabs = (await session.execute(query)).scalars().all()
            total_items = (await session.execute(count_query)).scalar_one()
            return [
                IntakeFormUITabData(
                    tab_id=tab.tab_id,
                    form_id=tab.form_id,
                    tab_label=tab.tab_label,
                    tab_order=tab.tab_order,
                )
                for tab in tabs
            ], total_items

    async def add_section(
        self,
        tab_id: str,
        section_id: str,
        section_order: int = 0,
    ) -> IntakeFormTabSectionIdData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._validate_tab(tab_id, session)
            await self._validate_section(section_id, session)

            existing = (
                await session.execute(
                    select(G2PIntakeFormUITabSection).where(
                        G2PIntakeFormUITabSection.tab_id == tab_id,
                        G2PIntakeFormUITabSection.section_id == section_id,
                    )
                )
            ).scalar_one_or_none()
            if existing:
                raise ValueError(f"Section '{section_id}' is already linked to tab '{tab_id}'")

            tab_section = G2PIntakeFormUITabSection(
                tab_id=tab_id,
                section_id=section_id,
                section_order=section_order,
            )
            session.add(tab_section)
            await session.commit()
            await session.refresh(tab_section)
            return IntakeFormTabSectionIdData(tab_section_id=tab_section.tab_section_id)

    async def remove_section(self, tab_section_id: str) -> None:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            tab_section = await self._validate_tab_section(tab_section_id, session)
            await session.delete(tab_section)
            await session.commit()

    async def update_section(
        self,
        tab_section_id: str,
        section_order: int | None = None,
    ) -> IntakeFormTabSectionIdData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            tab_section = await self._validate_tab_section(tab_section_id, session)

            if section_order is not None:
                tab_section.section_order = section_order

            await session.commit()
            return IntakeFormTabSectionIdData(tab_section_id=tab_section.tab_section_id)

    async def get_all_sections(
        self,
        tab_id: str | None = None,
        current_page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[IntakeFormUITabSectionData], int]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            query = (
                select(
                    G2PIntakeFormUITabSection,
                    G2PRegisterSection.section_mnemonic,
                )
                .join(
                    G2PRegisterSection,
                    G2PIntakeFormUITabSection.section_id == G2PRegisterSection.section_id,
                    isouter=True,
                )
                .order_by(
                    G2PIntakeFormUITabSection.section_order.asc(),
                    G2PIntakeFormUITabSection.tab_section_id.asc(),
                )
            )
            count_query = select(func.count()).select_from(G2PIntakeFormUITabSection)

            if tab_id is not None:
                await self._validate_tab(tab_id, session)
                query = query.where(G2PIntakeFormUITabSection.tab_id == tab_id)
                count_query = count_query.where(G2PIntakeFormUITabSection.tab_id == tab_id)

            query = self._apply_pagination(query, current_page, page_size)

            rows = (await session.execute(query)).all()
            total_items = (await session.execute(count_query)).scalar_one()

            return [
                IntakeFormUITabSectionData(
                    tab_section_id=tab_section.tab_section_id,
                    tab_id=tab_section.tab_id,
                    section_id=tab_section.section_id,
                    section_order=tab_section.section_order,
                    section_mnemonic=section_mnemonic,
                )
                for tab_section, section_mnemonic in rows
            ], total_items

    def _apply_pagination(self, query, current_page: int | None, page_size: int | None):
        if current_page is None or page_size is None:
            return query
        if current_page < 1 or page_size < 1:
            return query
        return query.offset((current_page - 1) * page_size).limit(page_size)

    async def _validate_register(self, register_id: str, session) -> G2PRegisterDefinition:
        register = await session.get(G2PRegisterDefinition, register_id)
        if not register:
            raise ValueError(f"Register with register_id '{register_id}' not found")
        return register

    async def _validate_register_for_intake_form_creation(self, register_id: str, session) -> G2PRegisterDefinition:
        register = await self._validate_register(register_id, session)
        if register.register_purpose != RegisterPurposeEnum.REGISTER.value:
            raise ValueError(
                f"register_id '{register_id}' must have register_purpose '{RegisterPurposeEnum.REGISTER.value}'"
            )
        return register

    async def _validate_intake_form(self, form_id: str, session) -> G2PIntakeFormDefinition:
        intake_form = await session.get(G2PIntakeFormDefinition, form_id)
        if not intake_form:
            raise ValueError(f"Intake form with form_id '{form_id}' not found")
        return intake_form

    async def _validate_tab(self, tab_id: str, session) -> G2PIntakeFormUITab:
        tab = await session.get(G2PIntakeFormUITab, tab_id)
        if not tab:
            raise ValueError(f"Intake form tab with tab_id '{tab_id}' not found")
        return tab

    async def _validate_section(self, section_id: str, session) -> G2PRegisterSection:
        section = await session.get(G2PRegisterSection, section_id)
        if not section:
            raise ValueError(f"Section with section_id '{section_id}' not found")
        return section

    async def _validate_tab_section(self, tab_section_id: str, session) -> G2PIntakeFormUITabSection:
        tab_section = await session.get(G2PIntakeFormUITabSection, tab_section_id)
        if not tab_section:
            raise ValueError(f"Tab section with tab_section_id '{tab_section_id}' not found")
        return tab_section
