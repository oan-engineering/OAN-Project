"""Sowing lines — a child of CROP_SOWN_RECORDS.

The ERD links every crop line straight to the crop sown record, so this register
sits directly under CropSown with no intermediate land/sowing level; the plot it
applies to is named by `land_uuid` (the stable generated key, not shown in
the UI) and carries the operator-facing `land_id` alongside it.
"""

from datetime import date

from openg2p_registry_core.models.g2p_intake_form import G2PIntakeForm
from openg2p_registry_core.models import G2PRegister, G2PRegisterHistory
from sqlalchemy import Boolean, Date, Integer, Numeric, String, select, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..services import G2PRegisterDomainServiceSowing
from .enums import SeedClassEnum


class G2PSowing:
    # ── Plot: each line records the land it was worked on (Gen1 puts
    # land_info_id and its attributes on the line, not the header) ───────────
    land_id: Mapped[str] = mapped_column(String, nullable=True)
    season: Mapped[str] = mapped_column(String, nullable=True)                # Attribute lookup (CROP_SEASON)
    commodity: Mapped[str] = mapped_column(String, nullable=True)             # Attribute lookup (CROP_COMMODITY)
    area_sown: Mapped[float] = mapped_column(Numeric, nullable=True)
    sowing_date: Mapped[str] = mapped_column(Date, nullable=True)
    fertilizer_type: Mapped[str] = mapped_column(String, nullable=True)       # Attribute lookup (FERTILIZER_TYPE)
    fertilizer_qty: Mapped[float] = mapped_column(Numeric, nullable=True)
    cluster_status: Mapped[list[str]] = mapped_column(JSONB, nullable=True)        # Attribute lookup (CLUSTER_STATUS)
    has_pest_disease: Mapped[bool] = mapped_column(Boolean, nullable=True)

    cluster_id: Mapped[str] = mapped_column(String, nullable=True)
    cluster_name: Mapped[str] = mapped_column(String, nullable=True)
    agro_ecological_zone: Mapped[str] = mapped_column(String, nullable=True)
    cluster_area_hectare: Mapped[float] = mapped_column(Numeric, nullable=True)
    cluster_season: Mapped[str] = mapped_column(String, nullable=True)
    cluster_area_sown: Mapped[float] = mapped_column(Numeric, nullable=True)
    cluster_has_pest_disease: Mapped[bool] = mapped_column(Boolean, nullable=True)

    temporary_land_id: Mapped[str] = mapped_column(String, nullable=True)
    sync_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    sowing_date_ec: Mapped[str] = mapped_column(String, nullable=True)
    geo_tagged_photo_document_id: Mapped[str] = mapped_column(String, nullable=True)





    da_name: Mapped[str] = mapped_column(String, nullable=True)
    da_mobile_number: Mapped[str] = mapped_column(String, nullable=True)
    supervisor_name: Mapped[str] = mapped_column(String, nullable=True)
    supervisor_mobile_number: Mapped[str] = mapped_column(String, nullable=True)

# All Register classes should have the prefix G2PRegister
class G2PRegisterSowing(G2PRegister, G2PSowing):
    __tablename__ = "g2p_register_sowings"
    __table_args__ = {"extend_existing": True}

    def get_search_text_fields(self) -> str:
        """Return sowing fields used to build search_text."""
        return G2PRegisterDomainServiceSowing().construct_search_text(self.to_dict())

    def get_record_name_fields(self) -> str:
        """Return sowing record_name from domain service implementation."""
        return G2PRegisterDomainServiceSowing().construct_record_name(self.to_dict())


# All Register History classes should have the prefix G2PRegisterHistory
class G2PRegisterHistorySowing(G2PRegisterHistory, G2PSowing):
    __tablename__ = "g2p_register_history_sowings"
    __table_args__ = {"extend_existing": True}


# All Intake Form classes should have the prefix G2PIntakeForm
class G2PIntakeFormSowing(G2PIntakeForm, G2PRegister, G2PSowing):
    __tablename__ = "g2p_intake_form_sowings"
    __table_args__ = {"extend_existing": True}

    async def get_link_internal_record_id(self, session):
        from .crop_sown import G2PIntakeFormCropSown
        result = await session.execute(
            select(G2PIntakeFormCropSown).where(
                G2PIntakeFormCropSown.submission_id == self.submission_id
            )
        )
        crop_sown = result.scalars().first()
        if crop_sown:
            self.link_internal_record_id = crop_sown.internal_record_id

    def get_search_text_fields(self) -> str:
        """Return sowing fields used to build search_text."""
        return G2PRegisterDomainServiceSowing().construct_search_text(self.to_dict())

    def get_record_name_fields(self) -> str:
        """Return sowing record_name from domain service implementation."""
        return G2PRegisterDomainServiceSowing().construct_record_name(self.to_dict())




