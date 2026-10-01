"""
Schemas for deduplication configuration and results.
"""
from typing import Optional
from pydantic import BaseModel, Field


class DeduplicationFieldConfig(BaseModel):
    """
    Configuration for a single field used in deduplication matching.
    
    Attributes:
        field_name: Name of the field to match on (e.g., 'first_name', 'date_of_birth')
        match_type: Type of matching to perform (EXACT, FUZZY, PHONETIC, NUMERIC_RANGE, DATE_RANGE)
        weight: Weight of this field in the overall score calculation (default: 1.0)
        similarity_threshold: Minimum similarity score required for this field to contribute to the match (default: 0.7)
        range_value: For NUMERIC_RANGE matching, the +/- range around the incoming value (default: 0)
        range_days: For DATE_RANGE matching, the +/- days around the incoming date (default: 0)
    """
    field_name: str = Field(
        ...,
        description="Name of the field to match on (e.g., 'first_name', 'date_of_birth')"
    )
    match_type: str = Field(
        default="EXACT",
        description="Type of matching: EXACT, FUZZY, PHONETIC, NUMERIC_RANGE, DATE_RANGE"
    )
    weight: float = Field(
        default=1.0,
        description="Weight of this field in the overall score calculation",
        ge=0.0
    )
    similarity_threshold: float = Field(
        default=0.7,
        description="Minimum similarity score required for this field to contribute to the match",
        ge=0.0,
        le=1.0
    )
    range_value: Optional[float] = Field(
        default=0,
        description="For NUMERIC_RANGE matching, the +/- range around the incoming value"
    )
    range_days: Optional[int] = Field(
        default=0,
        description="For DATE_RANGE matching, the +/- days around the incoming date"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "field_name": "first_name",
                    "match_type": "FUZZY",
                    "weight": 1.5,
                    "similarity_threshold": 0.8
                },
                {
                    "field_name": "date_of_birth",
                    "match_type": "DATE_RANGE",
                    "weight": 2.0,
                    "similarity_threshold": 0.9,
                    "range_days": 7
                },
                {
                    "field_name": "age",
                    "match_type": "NUMERIC_RANGE",
                    "weight": 1.0,
                    "similarity_threshold": 0.7,
                    "range_value": 2
                }
            ]
        }


