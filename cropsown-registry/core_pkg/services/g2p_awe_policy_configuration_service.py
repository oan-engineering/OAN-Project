import logging
import uuid
from typing import List

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..models import (
    AwePolicyScopeEnum,
    G2PRegisterDefinition,
    G2PRegistryAwePolicyConfiguration,
)
from ..schemas import AwePolicyConfigurationData

_logger = logging.getLogger("g2p-awe-policy-configuration-service")

CHANGE_REQUEST_POLICY_TYPES = (
    "registry.change_request",
    "change_request",
)
INTAKE_FORM_POLICY_TYPES = (
    "registry.intake_form",
    "intake_form",
)


class G2PAwePolicyConfigurationService(BaseService):
    async def get_all_awe_policy_configurations(
        self,
        current_page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[AwePolicyConfigurationData], int]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            query = (
                select(G2PRegistryAwePolicyConfiguration)
                .order_by(
                    G2PRegistryAwePolicyConfiguration.register_id.asc(),
                    G2PRegistryAwePolicyConfiguration.policy_scope.asc(),
                    G2PRegistryAwePolicyConfiguration.awe_policy_config_id.asc(),
                )
            )
            count_query = select(func.count()).select_from(G2PRegistryAwePolicyConfiguration)

            query = self._apply_pagination(query, current_page, page_size)

            rows = (await session.execute(query)).scalars().all()
            total_items = (await session.execute(count_query)).scalar_one()

            return [AwePolicyConfigurationData.model_validate(r) for r in rows], total_items

    async def get_awe_policy_configuration(self, awe_policy_config_id: str) -> List[AwePolicyConfigurationData]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            row = await self._get_configuration_or_error(awe_policy_config_id, session)
            return [AwePolicyConfigurationData.model_validate(row)]

    async def create_awe_policy_configuration(
        self,
        policy_scope: str,
        register_id: str,
        intake_form_id: str | None,
        section_id: str | None,
        policy_type: str,
        policy_key: str,
        context_field_names: list | None,
    ) -> List[AwePolicyConfigurationData]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self._validate_register_exists(register_id, session)
            scope_enum = self._parse_and_validate_scope(policy_scope, intake_form_id, section_id)

            row = G2PRegistryAwePolicyConfiguration(
                awe_policy_config_id=str(uuid.uuid4()),
                policy_scope=scope_enum,
                register_id=register_id,
                intake_form_id=intake_form_id,
                section_id=section_id,
                policy_type=policy_type,
                policy_key=policy_key,
                context_field_names=context_field_names,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return [AwePolicyConfigurationData.model_validate(row)]

    async def update_awe_policy_configuration(
        self,
        awe_policy_config_id: str,
        policy_scope: str | None,
        register_id: str | None,
        intake_form_id: str | None,
        section_id: str | None,
        policy_type: str | None,
        policy_key: str | None,
        context_field_names: list | None,
    ) -> List[AwePolicyConfigurationData]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            row = await self._get_configuration_or_error(awe_policy_config_id, session)

            effective_scope = (
                policy_scope if policy_scope is not None else row.policy_scope.value
            )
            effective_register = register_id if register_id is not None else row.register_id
            effective_intake_form = (
                intake_form_id if intake_form_id is not None else row.intake_form_id
            )
            effective_section = section_id if section_id is not None else row.section_id

            if register_id is not None:
                await self._validate_register_exists(register_id, session)

            scope_enum = self._parse_and_validate_scope(
                effective_scope, effective_intake_form, effective_section
            )

            row.policy_scope = scope_enum
            row.register_id = effective_register
            row.intake_form_id = effective_intake_form
            row.section_id = effective_section
            if policy_type is not None:
                row.policy_type = policy_type
            if policy_key is not None:
                row.policy_key = policy_key
            if context_field_names is not None:
                row.context_field_names = context_field_names

            await session.commit()
            await session.refresh(row)
            return [AwePolicyConfigurationData.model_validate(row)]

    async def delete_awe_policy_configuration(self, awe_policy_config_id: str) -> List[AwePolicyConfigurationData]:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            row = await self._get_configuration_or_error(awe_policy_config_id, session)
            data = AwePolicyConfigurationData.model_validate(row)
            await session.delete(row)
            await session.commit()
            return [data]

    def _parse_and_validate_scope(
        self, policy_scope: str, intake_form_id: str | None, section_id: str | None
    ) -> AwePolicyScopeEnum:
        # Normalize empty strings coming from clients to `None` so that
        # validation behaves consistently for optional fields.
        if isinstance(intake_form_id, str) and intake_form_id.strip() == "":
            intake_form_id = None
        if isinstance(section_id, str) and section_id.strip() == "":
            section_id = None

        try:
            scope = AwePolicyScopeEnum(policy_scope)
        except ValueError as exc:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                message=f"Invalid policy_scope '{policy_scope}'. Expected one of: "
                f"{', '.join(s.value for s in AwePolicyScopeEnum)}",
            ) from exc

        if scope == AwePolicyScopeEnum.REGISTER:
            if intake_form_id is not None or section_id is not None:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                    message="For REGISTER scope, intake_form_id and section_id must be omitted",
                )
        elif scope == AwePolicyScopeEnum.INTAKE_FORM:
            if not intake_form_id:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                    message="For INTAKE_FORM scope, intake_form_id is required",
                )
            if section_id is not None:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                    message="For INTAKE_FORM scope, section_id must be omitted",
                )
        elif scope == AwePolicyScopeEnum.SECTION:
            if not section_id:
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                    message="For SECTION scope, section_id is required",
                )
        return scope

    def _apply_pagination(self, query, current_page: int | None, page_size: int | None):
        if current_page is None or page_size is None:
            return query
        if current_page < 1 or page_size < 1:
            return query
        return query.offset((current_page - 1) * page_size).limit(page_size)

    async def _validate_register_exists(self, register_id: str, session: AsyncSession) -> None:
        register_definition = await session.get(G2PRegisterDefinition, register_id)
        if not register_definition:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTER_NOT_FOUND.value[1],
                message=f"Register with id {register_id} not found",
            )

    @staticmethod
    def _policy_type_filter(policy_type: str):
        if policy_type == "registry.change_request":
            types = CHANGE_REQUEST_POLICY_TYPES
        elif policy_type == "registry.intake_form":
            types = INTAKE_FORM_POLICY_TYPES
        else:
            types = (policy_type,)
        return G2PRegistryAwePolicyConfiguration.policy_type.in_(types)

    async def find_effective_policy_configuration(
        self,
        session: AsyncSession,
        *,
        register_id: str,
        policy_type: str,
        section_id: str | None = None,
        intake_form_id: str | None = None,
    ) -> G2PRegistryAwePolicyConfiguration | None:
        """Resolve policy: SECTION (if section_id) → INTAKE_FORM (if form_id) → REGISTER."""
        type_filter = self._policy_type_filter(policy_type)

        if section_id:
            row = (
                await session.execute(
                    select(G2PRegistryAwePolicyConfiguration).where(
                        G2PRegistryAwePolicyConfiguration.register_id == register_id,
                        type_filter,
                        G2PRegistryAwePolicyConfiguration.policy_scope == AwePolicyScopeEnum.SECTION.value,
                        G2PRegistryAwePolicyConfiguration.section_id == section_id,
                    )
                )
            ).scalar_one_or_none()
            if row is not None:
                return row

        if intake_form_id:
            row = (
                await session.execute(
                    select(G2PRegistryAwePolicyConfiguration).where(
                        G2PRegistryAwePolicyConfiguration.register_id == register_id,
                        type_filter,
                        G2PRegistryAwePolicyConfiguration.policy_scope == AwePolicyScopeEnum.INTAKE_FORM.value,
                        G2PRegistryAwePolicyConfiguration.intake_form_id == intake_form_id,
                    )
                )
            ).scalar_one_or_none()
            if row is not None:
                return row

        return (
            await session.execute(
                select(G2PRegistryAwePolicyConfiguration).where(
                    G2PRegistryAwePolicyConfiguration.register_id == register_id,
                    type_filter,
                    G2PRegistryAwePolicyConfiguration.policy_scope == AwePolicyScopeEnum.REGISTER.value,
                )
            )
        ).scalar_one_or_none()

    async def _get_configuration_or_error(
        self, awe_policy_config_id: str, session: AsyncSession
    ) -> G2PRegistryAwePolicyConfiguration:
        row = await session.get(G2PRegistryAwePolicyConfiguration, awe_policy_config_id)
        if not row:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.AWE_POLICY_CONFIGURATION_NOT_FOUND.value[1],
                message=f"AWE policy configuration with id {awe_policy_config_id} not found",
            )
        return row
