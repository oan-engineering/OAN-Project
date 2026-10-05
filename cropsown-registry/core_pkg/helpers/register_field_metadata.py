"""
Build register field name / data-type metadata from SQLAlchemy ORM models
(`G2PRegister*` mapped to registry tables).

Uses persisted column definitions rather than Pydantic schemas, so columns that are
not (yet) mirrored in API schemas remain visible.
"""

from __future__ import annotations

from enum import Enum as PyEnum

from sqlalchemy import LargeBinary as SALargeBinary
from sqlalchemy import Date as SADate
from sqlalchemy import Enum as SAEnum
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import JSON, TypeDecorator
from sqlalchemy.types import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UnicodeText,
)

try:
    from sqlalchemy.types import Uuid as SA_UUID
except ImportError:
    SA_UUID = None

from sqlalchemy.sql.sqltypes import DECIMAL

from ..schemas.register_payload import RegisterFieldMetadata

def iter_register_orm_field_metadata(orm_model_class):  # type: ignore[type-arg,no-untyped-def]
    """List mapped columns from a register SQLAlchemy model."""

    mapper = sa_inspect(orm_model_class)
    register_field_metadata: list[RegisterFieldMetadata] = []

    for column in mapper.columns:
        nullable: bool = bool(column.nullable)
        data_type = _sql_type_to_label(column.type)

        # String column + Python Enum in type_annotation (rare) — prefer enum label
        try:
            py_t = column.type.python_type  # type: ignore[attr-defined]
            if isinstance(py_t, type) and issubclass(py_t, PyEnum):
                data_type = f"enum({py_t.__name__})"
        except (NotImplementedError, TypeError, AttributeError):
            pass

        register_field_metadata.append(
            RegisterFieldMetadata(
                field_name=column.key,
                data_type=data_type,
                required=(not nullable),
                nullable=nullable,
            )
        )

    return sorted(register_field_metadata, key=lambda row: row.field_name)

def _effective_sql_type(column_type):  # type: ignore[type-arg,no-untyped-def]
    """Unwrap TypeDecorator (e.g. Mutable wrappers, custom DB types)."""
    for _ in range(12):
        if not isinstance(column_type, TypeDecorator):
            break
        impl_ref = getattr(column_type.__class__, "impl", None)
        if impl_ref is None:
            break
        if isinstance(impl_ref, type):
            nxt = impl_ref()
            if type(nxt) is type(column_type):  # pragma: no cover
                break
            column_type = nxt
        else:
            column_type = impl_ref  # pragma: no cover -- some impl hooks are instances
            if column_type is column_type:
                break
    return column_type

def _sql_type_to_label(column_type):  # type: ignore[no-untyped-def]
    """Map SQLAlchemy column type to JSON-oriented type names."""

    column_type = _effective_sql_type(column_type)

    if PG_ARRAY is not None and isinstance(column_type, PG_ARRAY):
        inner = column_type.item_type if hasattr(column_type, "item_type") else column_type
        return f"array[{_sql_type_to_label(inner)}]"

    if PG_UUID is not None and isinstance(column_type, PG_UUID):
        return "uuid"
    if SA_UUID is not None and isinstance(column_type, SA_UUID):
        return "uuid"

    if isinstance(column_type, JSONB):
        return "json"
    if isinstance(column_type, JSON):
        return "json"

    if isinstance(column_type, (String, Text, UnicodeText)):
        return "string"

    if isinstance(column_type, (Integer, SmallInteger, BigInteger)):
        return "integer"

    if isinstance(column_type, (Float, DECIMAL, Numeric)):
        return "number"

    if isinstance(column_type, Boolean):
        return "boolean"

    if isinstance(column_type, DateTime):
        return "datetime"
    if isinstance(column_type, SADate):
        return "date"
    if isinstance(column_type, Time):
        return "time"

    if isinstance(column_type, SAEnum):
        enums = getattr(column_type, "enums", None)
        if enums:
            return f"enum({', '.join(str(e) for e in enums)})"
        enum_class = getattr(column_type, "enum_class", None)
        name = getattr(enum_class, "__name__", "") if enum_class else ""
        if name:
            return f"enum({name})"
        return "enum"

    if isinstance(column_type, SALargeBinary):
        return "binary"

    return getattr(type(column_type), "__name__", str(type(column_type))).lower()
