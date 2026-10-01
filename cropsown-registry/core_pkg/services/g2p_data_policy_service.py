"""Data policy CRUD and policy expression merge."""

import logging
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService

from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..models import G2PRegistryDataPolicy
from ..models.enum import PolicyTargetEnum, RegistryDataPolicyTypeEnum
from ..schemas.g2p_data_policy import (
    PolicyFilterGroup,
    PolicyTarget,
    RegistryDataPolicyData,
    RegistryDataPolicyType,
)

_logger = logging.getLogger("g2p-data-policy-service")


class G2PDataPolicyService(BaseService):
    async def get_policy(
        self,
        session: AsyncSession,
        policy_id: str,
    ) -> RegistryDataPolicyData:
        result = await session.execute(
            select(G2PRegistryDataPolicy).where(
                G2PRegistryDataPolicy.policy_id == policy_id
            )
        )
        policy = result.scalar_one_or_none()
        if not policy:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTER_DATA_NOT_FOUND.value[1],
                message=f"Data policy not found: {policy_id}",
            )
        return self._to_policy_data(policy)

    async def get_all_policies(
        self,
        session: AsyncSession,
        current_page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[RegistryDataPolicyData], int]:
        stmt = select(G2PRegistryDataPolicy).order_by(
            G2PRegistryDataPolicy.policy_mnemonic,
            G2PRegistryDataPolicy.policy_target,
        )
        if current_page is not None and page_size is not None:
            stmt = stmt.offset((current_page - 1) * page_size).limit(page_size)

        total = (
            await session.execute(select(func.count()).select_from(G2PRegistryDataPolicy))
        ).scalar_one()
        result = await session.execute(stmt)
        policies = result.scalars().all()
        return [self._to_policy_data(policy) for policy in policies], total

    async def add_policy(
        self,
        policy_mnemonic: str,
        policy_description: str | None,
        register_id: str | None,
        policy_type: RegistryDataPolicyType,
        policy_filter_expression: dict,
        session: AsyncSession,
        policy_target: PolicyTarget = PolicyTarget.REGISTER_RECORD,
    ) -> RegistryDataPolicyData:
        normalized_expression = self._validate_policy_filter_expression(policy_filter_expression)

        if policy_target == PolicyTarget.REGISTER_RECORD and not register_id:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                message="register_id is required when policy_target is REGISTER_RECORD",
            )
        if policy_target in (PolicyTarget.GEO, PolicyTarget.ATTRIBUTE) and register_id:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                message="register_id must be null when policy_target is GEO or ATTRIBUTE",
            )

        duplicate_conditions = [
            G2PRegistryDataPolicy.policy_mnemonic == policy_mnemonic,
            G2PRegistryDataPolicy.policy_target == policy_target.value,
        ]
        if register_id is not None:
            duplicate_conditions.append(G2PRegistryDataPolicy.register_id == register_id)
        else:
            duplicate_conditions.append(G2PRegistryDataPolicy.register_id.is_(None))

        existing = await session.execute(
            select(G2PRegistryDataPolicy).where(*duplicate_conditions)
        )
        if existing.scalar_one_or_none():
            scope = f"register '{register_id}'" if register_id else "global"
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                message=(
                    f"Policy mnemonic '{policy_mnemonic}' already exists for {scope} "
                    f"target '{policy_target.value}'"
                ),
            )

        policy = G2PRegistryDataPolicy(
            policy_mnemonic=policy_mnemonic,
            policy_description=policy_description,
            register_id=register_id,
            policy_target=policy_target.value,
            policy_type=policy_type.value,
            policy_filter_expression=normalized_expression,
        )
        session.add(policy)
        await session.flush()
        await session.refresh(policy)
        return self._to_policy_data(policy)

    async def remove_policy(
        self,
        policy_id: str,
        session: AsyncSession,
    ) -> tuple[str, str, bool]:
        """
        Remove a policy row.

        Returns (policy_id, policy_mnemonic, should_delete_keycloak_role).
        Keycloak role is removed only when no other policy rows share the mnemonic.
        """
        result = await session.execute(
            select(G2PRegistryDataPolicy).where(G2PRegistryDataPolicy.policy_id == policy_id)
        )
        policy = result.scalar_one_or_none()
        if not policy:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTER_DATA_NOT_FOUND.value[1],
                message=f"Data policy not found: {policy_id}",
            )

        deleted_id = policy.policy_id
        policy_mnemonic = policy.policy_mnemonic
        await session.delete(policy)
        await session.flush()

        remaining = await session.execute(
            select(G2PRegistryDataPolicy).where(
                G2PRegistryDataPolicy.policy_mnemonic == policy_mnemonic
            )
        )
        should_delete_role = remaining.scalar_one_or_none() is None
        return deleted_id, policy_mnemonic, should_delete_role

    async def resolve_register_record_policy(
        self,
        register_id: str,
        policy_mnemonics: Sequence[str] | None,
        session: AsyncSession,
    ) -> dict | None:
        """Resolve and merge REGISTER_RECORD policies for the given mnemonics.

        ALLOW policies are unioned (OR); DISALLOW policies are negated and
        intersected (AND NOT). Returns ``None`` when no policy applies (no
        restriction).
        """
        if not policy_mnemonics:
            return None

        result = await session.execute(
            select(G2PRegistryDataPolicy).where(
                G2PRegistryDataPolicy.policy_mnemonic.in_(list(policy_mnemonics)),
                G2PRegistryDataPolicy.policy_target == PolicyTarget.REGISTER_RECORD.value,
                G2PRegistryDataPolicy.register_id == register_id,
            )
        )
        policies = result.scalars().all()
        if not policies:
            return None

        allow_expressions: list[dict] = []
        disallow_expressions: list[dict] = []
        for policy in policies:
            expression = policy.policy_filter_expression
            if not isinstance(expression, dict):
                continue
            if policy.policy_type == RegistryDataPolicyType.DISALLOW.value:
                disallow_expressions.append(expression)
            else:
                allow_expressions.append(expression)

        return self._merge_expressions(allow_expressions, disallow_expressions)

    async def resolve_attribute_policy(
        self,
        policy_mnemonics: Sequence[str] | None,
        session: AsyncSession,
    ) -> dict | None:
        """Resolve and merge global ATTRIBUTE policies for the given mnemonics.

        ATTRIBUTE policies are register-agnostic (``register_id`` is null).
        ALLOW policies are unioned (OR); DISALLOW policies are negated and
        intersected (AND NOT). Returns ``None`` when no policy applies (no
        restriction).
        """
        if not policy_mnemonics:
            return None

        result = await session.execute(
            select(G2PRegistryDataPolicy).where(
                G2PRegistryDataPolicy.policy_mnemonic.in_(list(policy_mnemonics)),
                G2PRegistryDataPolicy.policy_target == PolicyTarget.ATTRIBUTE.value
            )
        )
        policies = result.scalars().all()
        if not policies:
            return None

        allow_expressions: list[dict] = []
        disallow_expressions: list[dict] = []
        for policy in policies:
            expression = policy.policy_filter_expression
            if not isinstance(expression, dict):
                continue
            if policy.policy_type == RegistryDataPolicyType.DISALLOW.value:
                disallow_expressions.append(expression)
            else:
                allow_expressions.append(expression)

        return self._merge_expressions(allow_expressions, disallow_expressions)

    @staticmethod
    def _merge_expressions(
        allow_expressions: list[dict],
        disallow_expressions: list[dict],
    ) -> dict | None:
        nodes: list[dict] = []

        if len(allow_expressions) == 1:
            nodes.append(allow_expressions[0])
        elif len(allow_expressions) > 1:
            nodes.append(
                {"type": "GROUP", "operator": "OR", "children": allow_expressions}
            )

        for disallow_expression in disallow_expressions:
            nodes.append(
                {"type": "GROUP", "operator": "NOT", "children": [disallow_expression]}
            )

        if not nodes:
            return None
        if len(nodes) == 1:
            return nodes[0]
        return {"type": "GROUP", "operator": "AND", "children": nodes}

    def _to_policy_data(self, policy: G2PRegistryDataPolicy) -> RegistryDataPolicyData:
        return RegistryDataPolicyData(
            policy_id=policy.policy_id,
            policy_mnemonic=policy.policy_mnemonic,
            policy_description=policy.policy_description,
            register_id=policy.register_id,
            policy_target=PolicyTarget(policy.policy_target),
            policy_type=RegistryDataPolicyType(policy.policy_type),
            policy_filter_expression=policy.policy_filter_expression,
        )

    def _validate_policy_filter_expression(self, expression: dict) -> dict:
        """Validate and normalize a GROUP/CONDITION policy filter tree."""
        if not isinstance(expression, dict):
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.INVALID_REQUEST.value[1],
                message="policy_filter_expression must be a JSON object",
            )
        if expression.get("type") == "CONDITION":
            from ..schemas.g2p_data_policy import PolicyFilterCondition

            validated = PolicyFilterCondition.model_validate(expression)
            return validated.model_dump(mode="json")
        validated_group = PolicyFilterGroup.model_validate(expression)
        return validated_group.model_dump(mode="json")