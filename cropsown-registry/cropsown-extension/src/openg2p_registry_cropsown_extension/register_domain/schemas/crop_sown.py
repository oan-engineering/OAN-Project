from typing import Optional

from openg2p_registry_core.schemas import (
    G2PRegisterBaseSchema,
    G2PGeoSchema,
    G2PRegisterHistorySchema,
    G2PGeoHistorySchema,
    G2PIntakeFormSchemaBase,
)
import re
from pydantic import field_validator




class G2PSchemaCropSown:

    rejection_reason: Optional[str] = None
    edit_count: Optional[int] = None
    # Farmer (identified, held in the farmer registry)
    farmer_uuid: Optional[str] = None
    farmer_id: Optional[str] = None
    fayda_fan_id: Optional[str] = None
    farmer_name: Optional[str] = None
    land_id: Optional[str] = None

    # Address — admin hierarchy from the master-data catalog
    region: Optional[str] = None
    zone: Optional[str] = None
    woreda: Optional[str] = None
    kebele: Optional[str] = None
    gps_coordinate: Optional[str] = None
    region_name: Optional[str] = None
    zone_name: Optional[str] = None
    woreda_name: Optional[str] = None
    kebele_name: Optional[str] = None
    address_hierarchy: Optional[str] = None

    # Record lifecycle & field staff
    status: Optional[str] = None
    crop_year: Optional[str] = None
    production_season: Optional[str] = None
    lifecycle_stage: Optional[str] = None


class G2PRegisterSchemaCropSown(G2PRegisterBaseSchema, G2PGeoSchema, G2PSchemaCropSown):
    """
    Schema for Crop Sown Record register.
    Inherits fields from G2PRegisterBaseSchema, G2PGeoSchema, G2PGeoShapeSchema.
    Attributes inherited from G2PSchemaCropSown are specific to the Crop Sown Record domain,
    and include the land attributes of the single plot the record covers.
    """



class G2PRegisterHistorySchemaCropSown(G2PRegisterHistorySchema, G2PGeoHistorySchema, G2PSchemaCropSown):
    """
    Schema for Crop Sown Record history.
    Inherits fields from G2PRegisterHistorySchema, G2PGeoHistorySchema.
    """



class G2PIntakeFormSchemaCropSown(G2PIntakeFormSchemaBase, G2PRegisterBaseSchema, G2PGeoSchema, G2PSchemaCropSown):
    """
    Schema for Crop Sown Record intake form.
    Inherits fields from G2PRegisterBaseSchema, G2PGeoSchema, G2PGeoShapeSchema.
    Attributes inherited from G2PSchemaCropSown are specific to the Crop Sown Record domain and are included in the intake form schema for data collection.
    """

