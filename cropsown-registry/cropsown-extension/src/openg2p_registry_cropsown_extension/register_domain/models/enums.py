"""Enumerations for values the ERD does NOT model as lookup tables.

Everything the "CROP SOWN REGISTRY ERD UPDATED" draws as a catalog or lookup
table (crop, crop variety, season, plot category, ownership type, soil
fertility, fertilizer type, land preparation method, water source, infestation
type, cluster status, approval/workflow status) is an **attribute lookup**
instead — a plain String column resolved against g2p_attributes /
g2p_attribute_values, so the values are data an administrator can extend rather
than code. What remains here are the closed value sets the ERD leaves as plain
columns.
"""

from enum import StrEnum


class LandSizeUnitEnum(StrEnum):
    HECTARE = "HECTARE"
    TIMAD = "TIMAD"
    ACRE = "ACRE"
    SQUARE_METER = "SQUARE_METER"


class CroppingSystemEnum(StrEnum):
    MONO_CROPPING = "MONO_CROPPING"
    INTER_CROPPING = "INTER_CROPPING"


class SeedClassEnum(StrEnum):
    LOCAL = "LOCAL"
    IMPROVED = "IMPROVED"


class SeedSourceEnum(StrEnum):
    GOVERNMENT_WOREDS_AGRICULTURE = "GOVERNMENT / WOREDS AGRICULTURE"
    AGRICULTURE_COOPERATIVE_UNION = "AGRICULTURE COOPERATIVE / UNION"
    PRIVATE_SEED_ENTERPRISE = "PRIVATE SEED ENTERPRISE"
    FARMER_TO_FARMER_EXCHANGE_SAVED = "FARMER-TO-FARMER EXCHANGE / SAVED"



class CropMaturityStatusEnum(StrEnum):
    READY_FOR_HARVEST = "READY_FOR_HARVEST"
    NOT_YET_READY_FOR_HARVEST = "NOT_YET_READY_FOR_HARVEST"




class GrowthStageEnum(StrEnum):
    EMERGENCE = "EMERGENCE"
    VEGETATIVE = "VEGETATIVE"
    FLOWERING = "FLOWERING"
    MATURITY = "MATURITY"


class SeverityLevelEnum(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AgroEcologicalZoneEnum(StrEnum):
    KOLLA = "KOLLA"
    WOINA_DEGA = "WOINA_DEGA"
    DEGA = "DEGA"
    WURCH = "WURCH"
    BEREHA = "BEREHA"



