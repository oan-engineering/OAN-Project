from datetime import date
from typing import Optional, List

from pydantic import field_validator

from openg2p_registry_core.schemas import (
    G2PRegisterBaseSchema,
    G2PRegisterHistorySchema,
    G2PIntakeFormSchemaBase,
)
from ..models.enums import SeedClassEnum


def _coerce_str_list(value):
    """Normalise a multi-select value to a list. Accepts a native list, or a
    comma-joined string (how the value can get stored/passed once the generic
    list->string coercion in the platform touches a JSONB list column), so
    register/history/intake validation never fails on a str where a list is
    expected."""
    if value is None or isinstance(value, list):
        return value
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",") if part.strip()]
        return parts or None
    return value


class G2PSchemaSowing:

    cluster_id: Optional[str] = None
    cluster_name: Optional[str] = None
    agro_ecological_zone: Optional[str] = None
    cluster_area_hectare: Optional[float] = None

    sowing_id: Optional[str] = None
    temporary_land_id: Optional[str] = None
    sync_id: Optional[str] = None
    sowing_date_ec: Optional[str] = None
    geo_tagged_photo_document_id: Optional[str] = None
    land_id: Optional[str] = None
    season: Optional[str] = None
    commodity: Optional[str] = None
    area_sown: Optional[float] = None
    sowing_date: Optional[date] = None
    fertilizer_type: Optional[str] = None
    fertilizer_qty: Optional[float] = None
    cluster_status: Optional[List[str]] = None
    cluster_season: Optional[str] = None
    cluster_area_sown: Optional[float] = None
    cluster_has_pest_disease: Optional[bool] = None
    has_pest_disease: Optional[bool] = None





    da_name: Optional[str] = None
    da_mobile_number: Optional[str] = None
    supervisor_name: Optional[str] = None
    supervisor_mobile_number: Optional[str] = None

    _coerce_cluster_status = field_validator("cluster_status", mode="before")(_coerce_str_list)


class G2PRegisterSchemaSowing(G2PRegisterBaseSchema, G2PSchemaSowing):
    """
    Schema for Sowing register.
    Inherits fields from G2PRegisterBaseSchema.
    Attributes inherited from G2PSchemaSowing are specific to the Sowing domain.
    """


class G2PRegisterHistorySchemaSowing(G2PRegisterHistorySchema, G2PSchemaSowing):
    """
    Schema for Sowing history.
    Inherits fields from G2PRegisterHistorySchema.
    """


class G2PIntakeFormSchemaSowing(G2PIntakeFormSchemaBase, G2PRegisterBaseSchema, G2PSchemaSowing):
    """
    Schema for Sowing intake form.
    Inherits fields from G2PRegisterBaseSchema.
    Attributes inherited from G2PSchemaSowing are specific to the Sowing domain and are included in the intake form schema for data collection.
    """
