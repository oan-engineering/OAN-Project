import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService

from ..errors import G2PRegistryException
from ..models import (
    G2PIntakeFormUITabSection,
    G2PRegisterDefinition,
    G2PRegisterSection,
    G2PRegisterUITab,
    G2PRegisterUITabSection,
    RegisterPurposeEnum,
)
from ..schemas import (
    G2PRegisterSectionData,
    G2PRegisterUITabData,
    G2PRegisterUITabSectionData,
    RegisterRelationEnum,
    RegisterSectionIdData,
    RegisterSectionUISchemaData,
    RegisterTabIdData,
    RegisterTabSectionIdData,
)

_logger = logging.getLogger("g2p-register-metadata-service")


class G2PRegisterMetadataService(BaseService):
    # ---------------------------------------------------------------------
    # Tab metadata operations
    # ---------------------------------------------------------------------
    async def create_tab(
        self,
        register_id: str,
        tab_label: str,
        tab_order: int = 0,
        is_active: bool = True,
    ) -> RegisterTabIdData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._validate_register(register_id, session)
            tab = G2PRegisterUITab(
                register_id=register_id,
                tab_label=tab_label,
                tab_order=tab_order,
                is_active=is_active,
            )
            session.add(tab)
            await session.commit()
            await session.refresh(tab)
            return RegisterTabIdData(tab_id=tab.tab_id)

    async def delete_tab(self, tab_id: str) -> None:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._validate_tab(tab_id, session)

            tab_sections = (
                await session.execute(select(G2PRegisterUITabSection).where(G2PRegisterUITabSection.tab_id == tab_id))
            ).scalars().all()
            for tab_section in tab_sections:
                await session.delete(tab_section)

            tab = await session.get(G2PRegisterUITab, tab_id)
            if tab:
                await session.delete(tab)
            await session.commit()

    async def get_all_tabs(
        self,
        register_id: str | None = None,
        current_page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[G2PRegisterUITabData], int, int]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            query = select(G2PRegisterUITab)
            if register_id is not None:
                await self._validate_register(register_id, session)
                query = query.where(G2PRegisterUITab.register_id == register_id)
            query = query.order_by(G2PRegisterUITab.tab_order.asc(), G2PRegisterUITab.tab_label.asc())
            query = self._apply_pagination(query, current_page, page_size)

            tabs = (await session.execute(query)).scalars().all()
            tab_list = [self._build_tab_data(tab) for tab in tabs]
            total_items = await self._count_tabs(register_id)
            number_of_pages = 1
            if page_size and page_size > 0:
                number_of_pages = (total_items + page_size - 1) // page_size
            return tab_list, total_items, number_of_pages

    async def get_tab(self, tab_id: str) -> G2PRegisterUITabData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            tab = await self._validate_tab(tab_id, session)
            return self._build_tab_data(tab)

    async def update_tab(
        self,
        tab_id: str,
        tab_label: str | None = None,
        tab_order: int | None = None,
        is_active: bool | None = None,
    ) -> RegisterTabIdData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            tab = await self._validate_tab(tab_id, session)

            if tab_label is not None:
                tab.tab_label = tab_label
            if tab_order is not None:
                tab.tab_order = tab_order
            if is_active is not None:
                tab.is_active = is_active

            await session.commit()
            return RegisterTabIdData(tab_id=tab.tab_id)

    async def add_tab_section(
        self,
        tab_id: str,
        section_id: str,
        section_order: int = 0,
        register_id: str | None = None,
    ) -> RegisterTabSectionIdData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            tab = await self._validate_tab(tab_id, session, register_id)
            await self._validate_section(section_id, session, tab.register_id)

            existing = (
                await session.execute(
                    select(G2PRegisterUITabSection).where(
                        G2PRegisterUITabSection.tab_id == tab_id,
                        G2PRegisterUITabSection.section_id == section_id,
                    )
                )
            ).scalar_one_or_none()
            if existing:
                raise ValueError(f"Section '{section_id}' is already linked to tab '{tab_id}'.")

            tab_section = G2PRegisterUITabSection(
                register_id=tab.register_id,
                tab_id=tab_id,
                section_id=section_id,
                section_order=section_order,
            )
            session.add(tab_section)
            await session.commit()
            await session.refresh(tab_section)
            return RegisterTabSectionIdData(tab_section_id=tab_section.tab_section_id)

    async def get_tab_sections(
        self,
        tab_id: str,
        current_page: int | None = None,
        page_size: int | None = None,
    ) -> list[G2PRegisterUITabSectionData]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            tab = await self._validate_tab(tab_id, session)

            query = (
                select(G2PRegisterUITabSection)
                .where(G2PRegisterUITabSection.tab_id == tab_id)
                .order_by(G2PRegisterUITabSection.section_order.asc(), G2PRegisterUITabSection.tab_section_id.asc())
            )
            query = self._apply_pagination(query, current_page, page_size)
            tab_sections = (await session.execute(query)).scalars().all()

            response: list[G2PRegisterUITabSectionData] = []
            for tab_section in tab_sections:
                section = await self._validate_section(tab_section.section_id, session, tab.register_id)
                section_data = await self.build_section_data(
                    section=section,
                    session=session,
                    include_ui_schema=True,
                    include_register_purpose=True,
                    include_register_relation=True,
                    register_id_for_relation=tab.register_id,
                )
                response.append(self._build_tab_section_data(tab_section, section_data=section_data))
            return response

    async def update_tab_section(
        self,
        tab_section_id: str,
        section_id: str | None = None,
        section_order: int | None = None,
    ) -> G2PRegisterUITabSectionData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            tab_section = await self._validate_tab_section(tab_section_id, session)
            if section_id is not None:
                await self._validate_section(section_id, session, tab_section.register_id)
                tab_section.section_id = section_id
            if section_order is not None:
                tab_section.section_order = section_order

            await session.commit()
            await session.refresh(tab_section)

            section = await self._validate_section(tab_section.section_id, session, tab_section.register_id)
            section_data = await self.build_section_data(
                section=section,
                session=session,
                include_ui_schema=True,
                include_register_purpose=True,
                include_register_relation=True,
                register_id_for_relation=tab_section.register_id,
            )
            return self._build_tab_section_data(tab_section, section_data=section_data)

    async def remove_tab_section(self, tab_section_id: str) -> None:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            tab_section = await self._validate_tab_section(tab_section_id, session)
            await session.delete(tab_section)
            await session.commit()

    # ---------------------------------------------------------------------
    # Section metadata operations
    # ---------------------------------------------------------------------
    async def create_section(
        self,
        section_register_id: str,
        register_id: str,
        section_mnemonic: str,
        section_description: str | None = None,
        documents_required: bool = False,
        no_of_verifications_required: int = 0,
        cr_auto_approve_for_bene_portal: bool = False,
        cr_auto_approve_for_agent_portal: bool = False,
        cr_auto_approve_for_staff_portal: bool = False,
        cr_auto_approve_for_partner: bool = False,
        is_list: bool = False,
        is_core_section: bool = False,
        section_weightage: float = 0.0,
        section_ui_schema: dict | None = None,
    ) -> RegisterSectionIdData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._validate_register(register_id, session)
            await self._validate_register(section_register_id, session)

            section = G2PRegisterSection(
                section_register_id=section_register_id,
                register_id=register_id,
                section_mnemonic=section_mnemonic,
                section_description=section_description,
                documents_required=documents_required,
                no_of_verifications_required=no_of_verifications_required,
                cr_auto_approve_for_bene_portal=cr_auto_approve_for_bene_portal,
                cr_auto_approve_for_agent_portal=cr_auto_approve_for_agent_portal,
                cr_auto_approve_for_staff_portal=cr_auto_approve_for_staff_portal,
                cr_auto_approve_for_partner=cr_auto_approve_for_partner,
                is_list=is_list,
                is_core_section=is_core_section,
                section_weightage=section_weightage,
                section_ui_schema=section_ui_schema,
            )
            session.add(section)
            await session.commit()
            await session.refresh(section)
            return RegisterSectionIdData(section_id=section.section_id)

    async def delete_section(self, section_id: str) -> None:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            section = await self._validate_section(section_id, session)

            in_use_in_register_tab = (
                await session.execute(
                    select(G2PRegisterUITabSection.tab_section_id)
                    .where(G2PRegisterUITabSection.section_id == section_id)
                    .limit(1)
                )
            ).scalar_one_or_none()

            in_use_in_intake_form_tab = (
                await session.execute(
                    select(G2PIntakeFormUITabSection.tab_section_id)
                    .where(G2PIntakeFormUITabSection.section_id == section_id)
                    .limit(1)
                )
            ).scalar_one_or_none()

            if in_use_in_register_tab or in_use_in_intake_form_tab:
                raise G2PRegistryException(code="SECTION_CURRENTLY_USED", message="SECTION_CURRENTLY_USED")

            await session.delete(section)
            await session.commit()

    async def get_all_sections_brief(
        self,
        register_id: str,
        current_page: int | None = None,
        page_size: int | None = None,
    ) -> list[G2PRegisterSectionData]:
        return await self._get_sections(
            register_id=register_id,
            include_ui_schema=False,
            include_register_purpose=False,
            include_register_relation=False,
            current_page=current_page,
            page_size=page_size,
        )

    async def get_all_sections(
        self,
        register_id: str,
        current_page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[G2PRegisterSectionData], int, int]:
        sections = await self._get_sections(
            register_id=register_id,
            include_ui_schema=True,
            include_register_purpose=True,
            include_register_relation=True,
            current_page=current_page,
            page_size=page_size,
        )
        total_items = await self._count_sections(register_id)
        number_of_pages = 1
        if page_size and page_size > 0:
            number_of_pages = (total_items + page_size - 1) // page_size
        return sections, total_items, number_of_pages

    async def get_section(
        self,
        section_id: str,
        register_id: str | None = None,
    ) -> G2PRegisterSectionData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            section = await self._validate_section(section_id, session, register_id)
            relation_register_id = register_id or section.register_id
            return await self.build_section_data(
                section=section,
                session=session,
                include_ui_schema=True,
                include_register_purpose=True,
                include_register_relation=True,
                register_id_for_relation=relation_register_id,
            )

    async def update_section(
        self,
        section_id: str,
        section_register_id: str | None = None,
        section_mnemonic: str | None = None,
        section_description: str | None = None,
        documents_required: bool | None = None,
        no_of_verifications_required: int | None = None,
        cr_auto_approve_for_bene_portal: bool | None = None,
        cr_auto_approve_for_agent_portal: bool | None = None,
        cr_auto_approve_for_staff_portal: bool | None = None,
        cr_auto_approve_for_partner: bool | None = None,
        is_list: bool | None = None,
        is_core_section: bool | None = None,
        section_weightage: float | None = None,
    ) -> RegisterSectionIdData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            section = await self._validate_section(section_id, session)

            if section_register_id is not None:
                await self._validate_register(section_register_id, session)
                section.section_register_id = section_register_id
            if section_mnemonic is not None:
                section.section_mnemonic = section_mnemonic
            if section_description is not None:
                section.section_description = section_description
            if documents_required is not None:
                section.documents_required = documents_required
            if no_of_verifications_required is not None:
                section.no_of_verifications_required = no_of_verifications_required
            if cr_auto_approve_for_bene_portal is not None:
                section.cr_auto_approve_for_bene_portal = cr_auto_approve_for_bene_portal
            if cr_auto_approve_for_agent_portal is not None:
                section.cr_auto_approve_for_agent_portal = cr_auto_approve_for_agent_portal
            if cr_auto_approve_for_staff_portal is not None:
                section.cr_auto_approve_for_staff_portal = cr_auto_approve_for_staff_portal
            if cr_auto_approve_for_partner is not None:
                section.cr_auto_approve_for_partner = cr_auto_approve_for_partner
            if is_list is not None:
                section.is_list = is_list
            if is_core_section is not None:
                section.is_core_section = is_core_section
            if section_weightage is not None:
                section.section_weightage = section_weightage

            await session.commit()
            return RegisterSectionIdData(section_id=section.section_id)

    async def update_section_ui_schema(
        self,
        section_id: str,
        section_ui_schema: dict | None = None,
        register_id: str | None = None,
    ) -> RegisterSectionIdData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            section = await self._validate_section(section_id, session, register_id)
            section.section_ui_schema = section_ui_schema
            await session.commit()
            return RegisterSectionIdData(section_id=section.section_id)

    async def get_section_ui_schema(
        self,
        section_id: str,
        register_id: str | None = None,
    ) -> RegisterSectionUISchemaData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            section = await self._validate_section(section_id, session, register_id)
            return RegisterSectionUISchemaData(
                section_id=section.section_id,
                section_ui_schema=section.section_ui_schema,
            )

    # ---------------------------------------------------------------------
    # Shared helpers
    # ---------------------------------------------------------------------
    def _apply_pagination(self, query, current_page: int | None, page_size: int | None):
        if current_page is None or page_size is None:
            return query
        if current_page < 1 or page_size < 1:
            return query
        return query.offset((current_page - 1) * page_size).limit(page_size)

    async def _get_sections(
        self,
        register_id: str,
        include_ui_schema: bool,
        include_register_purpose: bool,
        include_register_relation: bool,
        current_page: int | None = None,
        page_size: int | None = None,
    ) -> list[G2PRegisterSectionData]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._validate_register(register_id, session)
            query = (
                select(G2PRegisterSection)
                .where(G2PRegisterSection.register_id == register_id)
                .order_by(G2PRegisterSection.section_mnemonic.asc())
            )
            query = self._apply_pagination(query, current_page, page_size)
            sections = (await session.execute(query)).scalars().all()
            return [
                await self.build_section_data(
                    section=section,
                    session=session,
                    include_ui_schema=include_ui_schema,
                    include_register_purpose=include_register_purpose,
                    include_register_relation=include_register_relation,
                    register_id_for_relation=register_id,
                )
                for section in sections
            ]

    async def _count_sections(self, register_id: str) -> int:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            count_query = (
                select(func.count())
                .select_from(G2PRegisterSection)
                .where(G2PRegisterSection.register_id == register_id)
            )
            result = await session.execute(count_query)
            return result.scalar() or 0

    async def _count_tabs(self, register_id: str | None) -> int:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            count_query = select(func.count()).select_from(G2PRegisterUITab)
            if register_id is not None:
                count_query = count_query.where(G2PRegisterUITab.register_id == register_id)
            result = await session.execute(count_query)
            return result.scalar() or 0

    async def _validate_register(self, register_id: str, session) -> G2PRegisterDefinition:
        register = await session.get(G2PRegisterDefinition, register_id)
        if not register:
            raise ValueError(f"Register with register_id '{register_id}' not found.")
        return register

    async def _validate_tab(self, tab_id: str, session, register_id: str | None = None) -> G2PRegisterUITab:
        tab = await session.get(G2PRegisterUITab, tab_id)
        if not tab:
            raise ValueError(f"Tab with tab_id '{tab_id}' not found.")
        if register_id is not None and tab.register_id != register_id:
            raise ValueError(f"Tab '{tab_id}' does not belong to register '{register_id}'.")
        return tab

    async def _validate_section(
        self,
        section_id: str,
        session,
        register_id: str | None = None,
    ) -> G2PRegisterSection:
        section = await session.get(G2PRegisterSection, section_id)
        if not section:
            raise ValueError(f"Section with section_id '{section_id}' not found.")
        if register_id is not None and section.register_id != register_id:
            raise ValueError(f"Section '{section_id}' does not belong to register '{register_id}'.")
        return section

    async def _validate_tab_section(self, tab_section_id: str, session) -> G2PRegisterUITabSection:
        tab_section = await session.get(G2PRegisterUITabSection, tab_section_id)
        if not tab_section:
            raise ValueError(f"Tab section with tab_section_id '{tab_section_id}' not found.")
        return tab_section

    async def build_section_data(
        self,
        section: G2PRegisterSection,
        session,
        include_ui_schema: bool,
        include_register_purpose: bool,
        include_register_relation: bool,
        register_id_for_relation: str,
    ) -> G2PRegisterSectionData:
        register_definition = await self._validate_register(register_id_for_relation, session)

        section_register_definition = register_definition
        if section.section_register_id != register_id_for_relation:
            section_register_definition = await self._validate_register(section.section_register_id, session)

        register_purpose: str | None = None
        if include_register_purpose:
            register_purpose = self._as_text_value(section_register_definition.register_purpose)

        register_relation: RegisterRelationEnum | None = None
        if include_register_relation:
            register_relation = await self._get_register_relation(
                register_id=register_id_for_relation,
                section_register_id=section.section_register_id,
                register_definition=register_definition,
                section_register_definition=section_register_definition,
                session=session,
            )

        return G2PRegisterSectionData(
            section_register_id=section.section_register_id,
            register_id=section.register_id,
            section_id=section.section_id,
            section_mnemonic=section.section_mnemonic,
            section_description=section.section_description,
            documents_required=section.documents_required,
            no_of_verifications_required=section.no_of_verifications_required,
            cr_auto_approve_for_bene_portal=section.cr_auto_approve_for_bene_portal,
            cr_auto_approve_for_agent_portal=section.cr_auto_approve_for_agent_portal,
            cr_auto_approve_for_staff_portal=section.cr_auto_approve_for_staff_portal,
            cr_auto_approve_for_partner=section.cr_auto_approve_for_partner,
            is_list=section.is_list,
            is_core_section=section.is_core_section,
            section_weightage=section.section_weightage,
            section_ui_schema=section.section_ui_schema if include_ui_schema else None,
            register_purpose=register_purpose,
            register_relation=register_relation,
        )

    async def _get_register_relation(
        self,
        register_id: str,
        section_register_id: str,
        register_definition: G2PRegisterDefinition,
        section_register_definition: G2PRegisterDefinition,
        session,
    ) -> RegisterRelationEnum:
        if section_register_id == register_id:
            return RegisterRelationEnum.SELF

        if section_register_definition.master_register_id == register_id:
            return RegisterRelationEnum.DESCENDANT

        path_exists, has_register_in_between = await self._has_register_in_path(
            section_register_id,
            register_id,
            session,
        )
        if path_exists and has_register_in_between:
            return RegisterRelationEnum.DESCENDANT_OF_A_REGISTER
        if path_exists:
            return RegisterRelationEnum.DESCENDANT

        if register_definition.master_register_id == section_register_id:
            return RegisterRelationEnum.ANCESTOR

        if (
            register_definition.master_register_id
            and register_definition.master_register_id == section_register_definition.master_register_id
        ):
            return RegisterRelationEnum.PEER

        return RegisterRelationEnum.SELF

    async def _has_register_in_path(
        self,
        start_register_id: str,
        target_register_id: str,
        session,
        max_depth: int = 20,
    ) -> tuple[bool, bool]:
        current_id: str | None = start_register_id
        depth: int = 0
        found_register_in_between: bool = False
        is_first: bool = True

        while current_id and depth < max_depth:
            register_definition: G2PRegisterDefinition = (
                await session.execute(
                    select(G2PRegisterDefinition).where(
                        G2PRegisterDefinition.register_id == current_id,
                    )
                )
            ).scalar()

            if not register_definition:
                return False, False

            current_id = register_definition.master_register_id

            if is_first:
                is_first = False
                depth += 1
                continue

            if register_definition.register_id == target_register_id:
                return True, found_register_in_between

            register_purpose = self._as_text_value(register_definition.register_purpose)
            if register_purpose == RegisterPurposeEnum.REGISTER.value:
                found_register_in_between = True

            if current_id == target_register_id:
                return True, found_register_in_between

            depth += 1

        return False, False

    def _as_text_value(self, value):
        return getattr(value, "value", value)

    def _build_tab_data(self, tab: G2PRegisterUITab) -> G2PRegisterUITabData:
        return G2PRegisterUITabData(
            tab_id=tab.tab_id,
            register_id=tab.register_id,
            tab_label=tab.tab_label,
            tab_order=tab.tab_order,
            is_active=tab.is_active,
        )

    def _build_tab_section_data(
        self,
        tab_section: G2PRegisterUITabSection,
        section_data: G2PRegisterSectionData | None = None,
    ) -> G2PRegisterUITabSectionData:
        return G2PRegisterUITabSectionData(
            tab_section_id=tab_section.tab_section_id,
            register_id=tab_section.register_id,
            tab_id=tab_section.tab_id,
            section_id=tab_section.section_id,
            section_order=tab_section.section_order,
            section_data=section_data,
        )
