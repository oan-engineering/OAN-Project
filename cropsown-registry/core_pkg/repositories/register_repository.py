"""Abstract, generic register data-access base.

Concrete domain repositories (Farmer, Individual, Household, ...) bind the
generic ``T`` to their SQLAlchemy register model and inherit the shared
data-policy -> SQLAlchemy translation implemented here.

Example:
    class RegisterRepositoryFarmer(RegisterRepository[G2PRegisterFarmer]):
        @property
        def model(self) -> type[G2PRegisterFarmer]:
            return G2PRegisterFarmer
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from sqlalchemy import JSON, Select, Text, and_, cast, not_, or_, select
from sqlalchemy.sql.elements import ColumnElement

T = TypeVar("T")

_logger = logging.getLogger("register-repository")

_GROUP_TYPE = "GROUP"
_CONDITION_TYPE = "CONDITION"


class RegisterRepository(ABC, Generic[T]):
    """Generic register repository that converts a data policy into SQL.

    The core responsibility exposed here is translating a ``GROUP``/``CONDITION``
    data-policy filter tree into a SQLAlchemy condition bound to the concrete
    register model ``T``.
    """

    @property
    @abstractmethod
    def model(self) -> type[T]:
        """Concrete SQLAlchemy register model that ``T`` is bound to."""

    def base_select(self) -> Select:
        """A base ``SELECT`` over the concrete register model."""
        return select(self.model)

    def build_policy_condition(self, expression: Any) -> ColumnElement | None:
        """Convert a data-policy filter tree into a SQLAlchemy condition.

        Returns ``None`` when the expression is empty or imposes no restriction.
        Accepts either a plain ``dict`` (as stored in the policy row) or a
        pydantic policy-expression model.
        """
        node = self._as_dict(expression)
        if node is None:
            return None

        node_type = node.get("type")
        if node_type == _CONDITION_TYPE:
            return self._build_condition(node)
        if node_type == _GROUP_TYPE or "children" in node:
            return self._build_group(node)

        _logger.warning("Unrecognized policy node type: %s", node_type)
        return None

    def apply_policy(self, stmt: Select, expression: Any) -> Select:
        """Apply the policy condition to a ``SELECT`` (no-op when empty)."""
        condition = self.build_policy_condition(expression)
        if condition is None:
            return stmt
        return stmt.where(condition)

    def _build_group(self, group: dict) -> ColumnElement | None:
        operator = str(group.get("operator") or "AND").upper()
        conditions = [
            condition
            for child in (group.get("children") or [])
            if (condition := self.build_policy_condition(child)) is not None
        ]
        if not conditions:
            return None
        if operator == "OR":
            return or_(*conditions)
        if operator == "NOT":
            return not_(and_(*conditions))
        return and_(*conditions)

    def _build_condition(self, condition: dict) -> ColumnElement | None:
        field_id = condition.get("field_id")
        if not field_id:
            return None

        column = getattr(self.model, field_id, None)
        if column is None:
            _logger.warning(
                "Policy field '%s' not found on %s; skipping condition",
                field_id,
                self.model.__name__,
            )
            return None

        operator = self._normalize_operator(condition.get("operator"))
        return self._apply_operator(
            column,
            operator,
            condition.get("value"),
            condition.get("values"),
        )

    def _apply_operator(
        self,
        column,
        operator: str,
        value: Any,
        values: Any,
    ) -> ColumnElement | None:
        # JSON/JSONB columns (e.g. geo_code_hierarchy_json) cannot use ILIKE
        # directly; cast to text for substring/prefix operators.
        text_column = self._text_operand(column)
        match operator:
            case "eq":
                return column == value
            case "neq":
                return column != value
            case "in":
                return column.in_(values or [])
            case "nin":
                return ~column.in_(values or [])
            case "contains":
                return text_column.ilike(f"%{value}%")
            case "ncontains":
                return ~text_column.ilike(f"%{value}%")
            case "startsWith":
                return text_column.ilike(f"{value}%")
            case "endsWith":
                return text_column.ilike(f"%{value}")
            case "gt":
                return column > value
            case "gte":
                return column >= value
            case "lt":
                return column < value
            case "lte":
                return column <= value
            case "between":
                if isinstance(value, (list, tuple)) and len(value) == 2:
                    return column.between(value[0], value[1])
                return None
            case "isNull":
                return column.is_(None) if value else column.isnot(None)
            case _:
                _logger.warning("Unsupported policy operator: %s", operator)
                return None

    @staticmethod
    def _text_operand(column):
        """Return a text-comparable operand; cast JSON/JSONB columns to text."""
        column_type = getattr(column, "type", None)
        if isinstance(column_type, JSON):
            return cast(column, Text)
        return column

    @staticmethod
    def _normalize_operator(operator: Any) -> str:
        if operator is None:
            return "eq"
        return operator.value if hasattr(operator, "value") else str(operator)

    @staticmethod
    def _as_dict(expression: Any) -> dict | None:
        if not expression:
            return None
        if isinstance(expression, dict):
            return expression
        if hasattr(expression, "model_dump"):
            return expression.model_dump()
        return None


class RegisterRecordRepository(RegisterRepository[T]):
    """Concrete register repository bound to a resolved register model.

    Used where the register model is resolved dynamically (e.g. by register
    mnemonic). Domain-specific subclasses (Farmer, Individual, Household, ...)
    can override behaviour later; this default simply binds ``model``.
    """

    def __init__(self, model: type[T]):
        self._model = model

    @property
    def model(self) -> type[T]:
        return self._model
