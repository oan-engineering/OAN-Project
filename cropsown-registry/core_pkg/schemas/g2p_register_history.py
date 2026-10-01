from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional


class G2PTableHistorySchema(BaseModel):
    """Base schema for G2PTableHistory fields."""

    history_record_id: Optional[str] = None
    internal_record_id: Optional[str] = None
    link_internal_record_id: Optional[str] = None


class G2PProgramRegisterHistorySchema(BaseModel):
    """Base schema for G2PProgramRegisterHistory fields."""

    history_record_id: Optional[str] = None
    internal_record_id: Optional[str] = None
    foundational_id: Optional[str] = None
    link_foundational_id: Optional[str] = None


class G2PRegisterHistorySchema(BaseModel):
    """Base schema for G2PRegisterHistory fields."""

    history_record_id: Optional[str] = None
    internal_record_id: Optional[str] = None
    tab_id: Optional[str] = None
    section_id: Optional[str] = None
    change_request_id: Optional[str] = None
    submission_id: Optional[str] = None
    change_request_source: Optional[str] = None
    is_primary_section: Optional[bool] = None
    functional_record_id: Optional[str] = None
    link_internal_record_id: Optional[str] = None
    link_foundational_id: Optional[str] = None
    record_status: Optional[str] = None
    record_status_reason: Optional[str] = None
    record_name: Optional[str] = None
    record_image_document_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


class G2PPersonHistorySchema(BaseModel):
    """Base schema for G2PPersonHistory fields."""

    foundational_id: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    given_name: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    phone_numbers: Optional[list] = None
    emails: Optional[list] = None
    marital_status: Optional[str] = None
    occupation: Optional[str] = None
    income_level: Optional[str] = None
    language_code: Optional[str] = None
    education_level: Optional[str] = None
    registration_date: Optional[date] = None


class G2PGeoHistorySchema(BaseModel):
    """Base schema for G2PGeoHistory fields."""

    latitude: Optional[str] = None
    longitude: Optional[str] = None
    altitude: Optional[str] = None
    plus_code: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: Optional[str] = None
    geo_lowest_level_value_id: Optional[str] = None
    geo_code_hierarchy_json: Optional[dict] = None


class G2PGeoShapeHistorySchema(BaseModel):
    """Base schema for G2PGeoShapeHistory fields."""

    shape_type: Optional[str] = None
    shape_coordinates_json: Optional[dict] = None
