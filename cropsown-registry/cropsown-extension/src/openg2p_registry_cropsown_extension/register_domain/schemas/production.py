from datetime import date
from typing import Optional

from openg2p_registry_core.schemas import (
    G2PRegisterBaseSchema,
    G2PRegisterHistorySchema,
    G2PIntakeFormSchemaBase,
)
from ..models.enums import GrowthStageEnum


class G2PSchemaProduction:

    production_id: Optional[str] = None
    land_id: Optional[str] = None
    season: Optional[str] = None
    commodity: Optional[str] = None
    crop_category: Optional[str] = None


class G2PRegisterSchemaProduction(G2PRegisterBaseSchema, G2PSchemaProduction):
    """
    Schema for Crop Production register.
    Inherits fields from G2PRegisterBaseSchema.
    Attributes inherited from G2PSchemaProduction are specific to the Crop Production domain.
    """


class G2PRegisterHistorySchemaProduction(G2PRegisterHistorySchema, G2PSchemaProduction):
    """
    Schema for Crop Production history.
    Inherits fields from G2PRegisterHistorySchema.
    """


class G2PIntakeFormSchemaProduction(G2PIntakeFormSchemaBase, G2PRegisterBaseSchema, G2PSchemaProduction):
    """
    Schema for Crop Production intake form.
    Inherits fields from G2PRegisterBaseSchema.
    Attributes inherited from G2PSchemaProduction are specific to the Crop Production domain and are included in the intake form schema for data collection.
    """
