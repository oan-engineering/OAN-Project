import uuid

from sqlalchemy import Boolean, DateTime, Integer, String, Text, Index, Date, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, validates
from openg2p_fastapi_common.models import BaseORMModel

from .enum import GenderEnum, MaritalStatusEnum, RecordStatusEnum, ShapeTypeEnum


class G2PTable(BaseORMModel):
    __abstract__ = True

    internal_record_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    link_internal_record_id: Mapped[str] = mapped_column(String, nullable=True, index=True) # Link to internal_record_id of the parent

class G2PProgramRegister(BaseORMModel):
    __abstract__ = True

    internal_record_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    foundational_id: Mapped[str] = mapped_column(String, nullable=True, unique=True, index=True)
    link_foundational_id: Mapped[str] = mapped_column(String, nullable=True, index=True)


class G2PRegister(BaseORMModel):
    __abstract__ = True

    internal_record_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    functional_record_id: Mapped[str] = mapped_column(String, nullable=True, unique=True, index=True)
    link_internal_record_id: Mapped[str] = mapped_column(String, nullable=True, index=True) # Link to internal_record_id of the parent
    link_foundational_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    record_name: Mapped[str] = mapped_column(String, nullable=True)
    record_image_document_id: Mapped[str] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    last_approved_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    last_approved_by: Mapped[str] = mapped_column(String, nullable=False)
    search_text: Mapped[str] = mapped_column(Text, nullable=True)

    record_status: Mapped[RecordStatusEnum] = mapped_column(String, nullable=False, default=RecordStatusEnum.ACTIVE.value)
    record_status_reason: Mapped[str] = mapped_column(String, nullable=True)

    def to_dict(self):
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
        }

    def get_search_text_fields(self) -> list[str]:
        """Return G2PRegister fields for search text aggregation."""
        return [
            self.functional_record_id or "",
            self.record_name or "",
        ]

    def get_record_name_fields(self) -> list[str]:
        """Return fields for record_name aggregation. Child classes can override."""
        return []

    @classmethod
    def __declare_last__(cls):
        """Create table-specific index and register event listeners after table is declared"""
        # Check if this is a concrete class by looking for __tablename__ in the class's own __dict__
        is_abstract = cls.__dict__.get('__abstract__', False)
        has_tablename = '__tablename__' in cls.__dict__
        
        if has_tablename and not is_abstract:
            # Create trigram index for search_text (requires pg_trgm extension)
            index_name = f"idx_{cls.__tablename__}_search_text_trigram"
            idx = Index(index_name, cls.search_text, postgresql_using='gin', postgresql_ops={'search_text': 'gin_trgm_ops'})
            idx._set_parent(cls.__table__, allow_replacements=True)
            
            # Register event listeners for automatic search_text and record_name population
            @event.listens_for(cls, "before_insert")
            def populate_search_text_on_insert(mapper, connection, target):
                _populate_search_text(target)
                _populate_record_name(target)
            
            @event.listens_for(cls, "before_update")
            def populate_search_text_on_update(mapper, connection, target):
                _populate_search_text(target)
                _populate_record_name(target)


def _collect_fields(target, method_name: str) -> list[str]:
    """Collect field values from class-specific hook methods across MRO."""
    all_fields = []
    for base in target.__class__.__mro__:
        if hasattr(base, method_name) and method_name in base.__dict__:
            try:
                fields = getattr(base, method_name)(target)
                if not fields:
                    continue
                if isinstance(fields, str):
                    all_fields.append(fields)
                    continue
                for field in fields:
                    if field is not None:
                        all_fields.append(field if isinstance(field, str) else str(field))
            except Exception:
                # Skip if there's an error getting fields from this class
                pass
    return all_fields


def _populate_search_text(target):
    """
    Populate search_text by aggregating fields from all parent classes
    that have get_search_text_fields() method.
    """
    all_fields = _collect_fields(target, "get_search_text_fields")
    
    target.search_text = " ".join(filter(None, all_fields)).strip() or None


def _populate_record_name(target):
    """
    Populate record_name by aggregating fields from classes implementing
    get_record_name_fields(). If computed value is empty, keep existing value.
    """
    all_fields = _collect_fields(target, "get_record_name_fields")
    computed_record_name = " ".join(filter(None, all_fields)).strip()
    if computed_record_name:
        target.record_name = computed_record_name

class G2PPerson(BaseORMModel):
    __abstract__ = True

    foundational_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    middle_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    given_name: Mapped[str] = mapped_column(String, nullable=True)
    prefix: Mapped[str] = mapped_column(String, nullable=True)
    suffix: Mapped[str] = mapped_column(String, nullable=True)
    gender: Mapped[GenderEnum] = mapped_column(String, nullable=True)
    birth_date: Mapped[str] = mapped_column(Date, nullable=True)
    phone_numbers: Mapped[list] = mapped_column(JSONB, nullable=True)
    emails: Mapped[list] = mapped_column(JSONB, nullable=True)
    marital_status: Mapped[MaritalStatusEnum] = mapped_column(String, nullable=True)
    occupation: Mapped[str] = mapped_column(String, nullable=True)
    income_level: Mapped[str] = mapped_column(String, nullable=True)
    language_code: Mapped[str] = mapped_column(String, nullable=True)
    education_level: Mapped[str] = mapped_column(String, nullable=True)
    registration_date: Mapped[str] = mapped_column(Date, nullable=True)


class G2PGeo(BaseORMModel):
    __abstract__ = True

    latitude: Mapped[str] = mapped_column(String, nullable=True)
    longitude: Mapped[str] = mapped_column(String, nullable=True)
    altitude: Mapped[str] = mapped_column(String, nullable=True)
    plus_code: Mapped[str] = mapped_column(String, nullable=True, index=True)
    address_line_1: Mapped[str] = mapped_column(String, nullable=True)
    address_line_2: Mapped[str] = mapped_column(String, nullable=True)
    postal_code: Mapped[str] = mapped_column(String, nullable=True, index=True)
    country_code: Mapped[str] = mapped_column(String, nullable=True, index=True)
    geo_lowest_level_value_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    geo_code_hierarchy_json: Mapped[str] = mapped_column(JSONB, nullable=True)

    @validates('geo_lowest_level_value_id')
    def update_geo_hierarchy(self, _key: str, value: str) -> str:
        """
        Automatically populate geo_code_hierarchy_json when geo_lowest_level_value_id is set.
        Fetches the hierarchy from master-data-db with caching.
        """
        if value:
            from ..services import G2PGeoHierarchyService
            service = G2PGeoHierarchyService.get_component()
            if service is None:
                self.geo_code_hierarchy_json = None
            else:
                self.geo_code_hierarchy_json = service.get_geo_hierarchy_sync(value)
        else:
            self.geo_code_hierarchy_json = None
        return value



class G2PGeoShape(BaseORMModel):
    __abstract__ = True
    
    shape_type: Mapped[ShapeTypeEnum] = mapped_column(String, nullable=True) 
    shape_coordinates_json: Mapped[str] = mapped_column(JSONB, nullable=True)
    
