import logging
import uuid
from typing import List, Optional

from fastapi_cache import FastAPICache
from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..models import G2PAttribute, G2PAttributeValue
from ..repositories import AttributeValueRepository
from ..schemas import AttributeData, AttributeValueData
from .g2p_data_policy_service import G2PDataPolicyService

_logger = logging.getLogger("g2p-attribute-service")


class G2PAttributeService(BaseService):
    async def get_attributes(
        self,
        session: AsyncSession,
        current_page: Optional[int] = None,
        page_size: Optional[int] = None,
        search_text: Optional[str] = None,
    ) -> tuple[List[AttributeData], int]:
        filters = []
        if search_text:
            filters.append(G2PAttribute.attribute_code.ilike(f"%{search_text}%"))

        count_query = select(func.count()).select_from(G2PAttribute)
        if filters:
            count_query = count_query.where(*filters)
        total = (await session.execute(count_query)).scalar_one()

        query = select(G2PAttribute)
        if filters:
            query = query.where(*filters)
        query = query.order_by(G2PAttribute.attribute_code)
        if current_page is not None and page_size is not None:
            query = query.offset((current_page - 1) * page_size).limit(page_size)

        result = await session.execute(query)
        return [self._attribute_to_data(row) for row in result.scalars().all()], total

    async def get_attribute(self, attribute_id: str, session: AsyncSession) -> AttributeData:
        attribute = await session.get(G2PAttribute, attribute_id)
        if not attribute:
            self._raise_attribute_not_found(attribute_id)
        return self._attribute_to_data(attribute)

    async def create_attribute(
        self,
        *,
        attribute_code: str,
        attribute_display: str,
        is_hierarchical: bool,
        session: AsyncSession,
    ) -> AttributeData:
        attribute_code = attribute_code.strip()
        attribute_display = attribute_display.strip()
        if not attribute_code or not attribute_display:
            self._raise_validation_error("attribute_code and attribute_display are required")

        if await self._attribute_code_exists(session, attribute_code):
            self._raise_attribute_already_exists(f"attribute_code already exists: {attribute_code}")

        attribute = G2PAttribute(
            attribute_id=str(uuid.uuid4()),
            attribute_code=attribute_code,
            attribute_display=attribute_display,
            is_hierarchical=is_hierarchical,
        )
        session.add(attribute)
        await session.flush()
        return self._attribute_to_data(attribute)

    async def update_attribute(
        self,
        *,
        attribute_id: str,
        attribute_code: Optional[str],
        attribute_display: Optional[str],
        is_hierarchical: Optional[bool],
        session: AsyncSession,
    ) -> AttributeData:
        attribute = await session.get(G2PAttribute, attribute_id)
        if not attribute:
            self._raise_attribute_not_found(attribute_id)

        if all(value is None for value in (attribute_code, attribute_display, is_hierarchical)):
            self._raise_validation_error("At least one field must be provided to update")

        if attribute_code is not None:
            attribute_code = attribute_code.strip()
            if not attribute_code:
                self._raise_validation_error("attribute_code cannot be empty")
            if await self._attribute_code_exists(
                session, attribute_code, exclude_attribute_id=attribute_id
            ):
                self._raise_attribute_already_exists(f"attribute_code already exists: {attribute_code}")
            attribute.attribute_code = attribute_code

        if attribute_display is not None:
            attribute_display = attribute_display.strip()
            if not attribute_display:
                self._raise_validation_error("attribute_display cannot be empty")
            attribute.attribute_display = attribute_display

        if is_hierarchical is not None:
            if is_hierarchical is False and await self._attribute_has_hierarchical_values(session, attribute_id):
                raise G2PRegistryException(
                    code=G2PRegistryErrorCodes.ATTRIBUTE_HAS_HIERARCHICAL_VALUES.value[1],
                    message=(
                        f"Cannot set is_hierarchical=false for attribute '{attribute_id}' "
                        "while values have parent_value_id set"
                    ),
                )
            attribute.is_hierarchical = is_hierarchical

        session.add(attribute)
        await session.flush()
        return self._attribute_to_data(attribute)

    async def delete_attribute(self, attribute_id: str, session: AsyncSession) -> str:
        attribute = await session.get(G2PAttribute, attribute_id)
        if not attribute:
            self._raise_attribute_not_found(attribute_id)

        if await self._attribute_value_count(session, attribute_id) > 0:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.ATTRIBUTE_HAS_VALUES.value[1],
                message=f"Cannot delete attribute '{attribute_id}' while attribute values exist",
            )

        await session.delete(attribute)
        await session.flush()
        return attribute_id

    async def get_attribute_values(
        self,
        attribute_id: Optional[str] = None,
        parent_value_id: Optional[str] = None,
        current_page: Optional[int] = None,
        page_size: Optional[int] = None,
        search_text: Optional[str] = None,
        session: Optional[AsyncSession] = None,
        policy_mnemonics: list[str] | None = None,
    ) -> tuple[List[AttributeValueData], int]:
        async def _run(db_session: AsyncSession) -> tuple[List[AttributeValueData], int]:
            filters = []
            if attribute_id:
                filters.append(G2PAttributeValue.attribute_id == attribute_id)
            if parent_value_id:
                filters.append(G2PAttributeValue.parent_value_id == parent_value_id)
            if search_text:
                filters.append(G2PAttributeValue.value_code.ilike(f"%{search_text}%"))

            policy_condition = await self._build_attribute_value_policy_condition(
                policy_mnemonics,
                db_session,
                attribute_id=attribute_id,
            )
            if policy_condition is not None:
                filters.append(policy_condition)

            count_query = select(func.count()).select_from(G2PAttributeValue)
            if filters:
                count_query = count_query.where(*filters)
            total = (await db_session.execute(count_query)).scalar_one()

            query = select(G2PAttributeValue)
            if filters:
                query = query.where(*filters)
            query = query.order_by(
                G2PAttributeValue.attribute_id,
                G2PAttributeValue.sort_order,
            )
            if current_page is not None and page_size is not None:
                query = query.offset((current_page - 1) * page_size).limit(page_size)

            result = await db_session.execute(query)
            return [self._value_to_data(value) for value in result.scalars().all()], total

        if session is not None:
            return await _run(session)

        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as db_session:
            return await _run(db_session)

    async def _build_attribute_value_policy_condition(
        self,
        policy_mnemonics: list[str] | None,
        session: AsyncSession,
        attribute_id: str | None = None,
    ):
        """Resolve ATTRIBUTE policy and translate it for ``G2PAttributeValue`` rows."""
        if not policy_mnemonics:
            return None

        merged_expression = await G2PDataPolicyService.get_component().resolve_attribute_policy(
            policy_mnemonics, session
        )
        if not merged_expression:
            return None

        attribute_context = None
        if attribute_id:
            attribute = await session.get(G2PAttribute, attribute_id)
            if attribute:
                attribute_context = attribute.attribute_code

        return AttributeValueRepository().build_policy_condition(
            merged_expression,
            attribute_context=attribute_context,
        )

    async def create_attribute_value(
        self,
        *,
        attribute_id: str,
        value_code: str,
        value_display: str,
        parent_value_id: Optional[str],
        sort_order: int,
        session: AsyncSession,
    ) -> AttributeValueData:
        value_code = value_code.strip()
        value_display = value_display.strip()
        if not value_code or not value_display:
            self._raise_validation_error("value_code and value_display are required")

        attribute = await session.get(G2PAttribute, attribute_id)
        if not attribute:
            self._raise_attribute_not_found(attribute_id)

        await self._validate_parent_value(
            session,
            attribute=attribute,
            attribute_id=attribute_id,
            parent_value_id=parent_value_id,
            exclude_value_id=None,
        )

        if await self._value_code_exists(session, attribute_id, value_code):
            self._raise_attribute_value_already_exists(
                f"value_code already exists for attribute '{attribute_id}': {value_code}"
            )

        value = G2PAttributeValue(
            value_id=str(uuid.uuid4()),
            attribute_id=attribute_id,
            value_code=value_code,
            value_display=value_display,
            parent_value_id=parent_value_id,
            sort_order=sort_order,
        )
        session.add(value)
        await session.flush()
        await self._clear_attribute_cache()
        return self._value_to_data(value)

    async def update_attribute_value(
        self,
        *,
        value_id: str,
        value_code: Optional[str],
        value_display: Optional[str],
        parent_value_id: Optional[str],
        sort_order: Optional[int],
        session: AsyncSession,
    ) -> AttributeValueData:
        value = await session.get(G2PAttributeValue, value_id)
        if not value:
            self._raise_attribute_value_not_found(value_id)

        if all(field is None for field in (value_code, value_display, parent_value_id, sort_order)):
            self._raise_validation_error("At least one field must be provided to update")

        attribute = await session.get(G2PAttribute, value.attribute_id)
        if not attribute:
            self._raise_attribute_not_found(value.attribute_id)

        if parent_value_id is not None:
            if parent_value_id == value_id:
                self._raise_validation_error("parent_value_id cannot reference the value itself")
            await self._validate_parent_value(
                session,
                attribute=attribute,
                attribute_id=value.attribute_id,
                parent_value_id=parent_value_id or None,
                exclude_value_id=value_id,
            )
            value.parent_value_id = parent_value_id or None

        if value_code is not None:
            value_code = value_code.strip()
            if not value_code:
                self._raise_validation_error("value_code cannot be empty")
            if await self._value_code_exists(
                session, value.attribute_id, value_code, exclude_value_id=value_id
            ):
                self._raise_attribute_value_already_exists(
                    f"value_code already exists for attribute '{value.attribute_id}': {value_code}"
                )
            value.value_code = value_code

        if value_display is not None:
            value_display = value_display.strip()
            if not value_display:
                self._raise_validation_error("value_display cannot be empty")
            value.value_display = value_display

        if sort_order is not None:
            value.sort_order = sort_order

        session.add(value)
        await session.flush()
        await self._clear_attribute_cache()
        return self._value_to_data(value)

    async def delete_attribute_value(self, value_id: str, session: AsyncSession) -> str:
        value = await session.get(G2PAttributeValue, value_id)
        if not value:
            self._raise_attribute_value_not_found(value_id)

        if await self._child_value_count(session, value_id) > 0:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.ATTRIBUTE_VALUE_HAS_CHILDREN.value[1],
                message=f"Cannot delete attribute value '{value_id}' while child values exist",
            )

        await session.delete(value)
        await session.flush()
        await self._clear_attribute_cache()
        return value_id

    def _attribute_to_data(self, attribute: G2PAttribute) -> AttributeData:
        return AttributeData(
            attribute_id=attribute.attribute_id,
            attribute_code=attribute.attribute_code,
            attribute_display=attribute.attribute_display,
            is_hierarchical=attribute.is_hierarchical,
        )

    def _value_to_data(self, value: G2PAttributeValue) -> AttributeValueData:
        return AttributeValueData(
            value_id=value.value_id,
            attribute_id=value.attribute_id,
            value_code=value.value_code,
            value_display=value.value_display,
            parent_value_id=value.parent_value_id,
            sort_order=value.sort_order,
        )

    async def _attribute_code_exists(
        self,
        session: AsyncSession,
        attribute_code: str,
        exclude_attribute_id: Optional[str] = None,
    ) -> bool:
        query = select(func.count()).select_from(G2PAttribute).where(
            G2PAttribute.attribute_code == attribute_code
        )
        if exclude_attribute_id:
            query = query.where(G2PAttribute.attribute_id != exclude_attribute_id)
        return (await session.execute(query)).scalar_one() > 0

    async def _value_code_exists(
        self,
        session: AsyncSession,
        attribute_id: str,
        value_code: str,
        exclude_value_id: Optional[str] = None,
    ) -> bool:
        query = select(func.count()).select_from(G2PAttributeValue).where(
            G2PAttributeValue.attribute_id == attribute_id,
            G2PAttributeValue.value_code == value_code,
        )
        if exclude_value_id:
            query = query.where(G2PAttributeValue.value_id != exclude_value_id)
        return (await session.execute(query)).scalar_one() > 0

    async def _attribute_value_count(self, session: AsyncSession, attribute_id: str) -> int:
        return (
            await session.execute(
                select(func.count()).select_from(G2PAttributeValue).where(
                    G2PAttributeValue.attribute_id == attribute_id
                )
            )
        ).scalar_one()

    async def _child_value_count(self, session: AsyncSession, value_id: str) -> int:
        return (
            await session.execute(
                select(func.count()).select_from(G2PAttributeValue).where(
                    G2PAttributeValue.parent_value_id == value_id
                )
            )
        ).scalar_one()

    async def _attribute_has_hierarchical_values(self, session: AsyncSession, attribute_id: str) -> bool:
        return (
            await session.execute(
                select(func.count()).select_from(G2PAttributeValue).where(
                    G2PAttributeValue.attribute_id == attribute_id,
                    G2PAttributeValue.parent_value_id.is_not(None),
                )
            )
        ).scalar_one() > 0

    async def _validate_parent_value(
        self,
        session: AsyncSession,
        *,
        attribute: G2PAttribute,
        attribute_id: str,
        parent_value_id: Optional[str],
        exclude_value_id: Optional[str],
    ) -> None:
        if not parent_value_id:
            return

        if not attribute.is_hierarchical:
            self._raise_validation_error(
                f"parent_value_id is not allowed for non-hierarchical attribute '{attribute_id}'"
            )

        parent = await session.get(G2PAttributeValue, parent_value_id)
        if not parent or parent.attribute_id != attribute_id:
            self._raise_validation_error(
                f"parent_value_id '{parent_value_id}' was not found for attribute '{attribute_id}'"
            )
        if exclude_value_id and parent_value_id == exclude_value_id:
            self._raise_validation_error("parent_value_id cannot reference the value itself")

    async def _clear_attribute_cache(self) -> None:
        await FastAPICache.clear()

    def _raise_validation_error(self, message: str) -> None:
        raise G2PRegistryException(
            code=G2PRegistryErrorCodes.REQUEST_VALIDATION_ERROR.value[1],
            message=message,
        )

    def _raise_attribute_not_found(self, attribute_id: str) -> None:
        raise G2PRegistryException(
            code=G2PRegistryErrorCodes.ATTRIBUTE_NOT_FOUND.value[1],
            message=f"Attribute not found: {attribute_id}",
        )

    def _raise_attribute_already_exists(self, message: str) -> None:
        raise G2PRegistryException(
            code=G2PRegistryErrorCodes.ATTRIBUTE_ALREADY_EXISTS.value[1],
            message=message,
        )

    def _raise_attribute_value_not_found(self, value_id: str) -> None:
        raise G2PRegistryException(
            code=G2PRegistryErrorCodes.ATTRIBUTE_VALUE_NOT_FOUND.value[1],
            message=f"Attribute value not found: {value_id}",
        )

    def _raise_attribute_value_already_exists(self, message: str) -> None:
        raise G2PRegistryException(
            code=G2PRegistryErrorCodes.ATTRIBUTE_VALUE_ALREADY_EXISTS.value[1],
            message=message,
        )
