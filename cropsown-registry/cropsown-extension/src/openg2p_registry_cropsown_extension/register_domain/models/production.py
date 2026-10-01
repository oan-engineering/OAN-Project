"""Crop Production lines — a child of CROP_SOWN_RECORDS.

The ERD links every crop line straight to the crop sown record, so this register
sits directly under CropSown with no intermediate land/sowing level; the plot it
applies to is named by `land_uuid` (the stable generated key, not shown in
the UI) and carries the operator-facing `land_id` alongside it.
"""

from datetime import date

from openg2p_registry_core.models.g2p_intake_form import G2PIntakeForm
from openg2p_registry_core.models import G2PRegister, G2PRegisterHistory
from sqlalchemy import Boolean, Date, Integer, Numeric, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ..services import G2PRegisterDomainServiceProduction
from .enums import GrowthStageEnum


class G2PProduction:
    production_id: Mapped[str] = mapped_column(String, nullable=True)
    # ── Plot: each line records the land it was worked on (Gen1 puts
    # land_info_id and its attributes on the line, not the header) ───────────
    land_id: Mapped[str] = mapped_column(String, nullable=True)
    season: Mapped[str] = mapped_column(String, nullable=True)                # Attribute lookup (CROP_SEASON)
    commodity: Mapped[str] = mapped_column(String, nullable=True)             # Attribute lookup (CROP_COMMODITY)
    crop_category: Mapped[str] = mapped_column(String, nullable=True)         # Attribute lookup (CROP_CATEGORY)



# All Register classes should have the prefix G2PRegister
class G2PRegisterProduction(G2PRegister, G2PProduction):
    __tablename__ = "g2p_register_productions"
    __table_args__ = {"extend_existing": True}

    def get_search_text_fields(self) -> str:
        """Return crop production fields used to build search_text."""
        return G2PRegisterDomainServiceProduction().construct_search_text(self.to_dict())

    def get_record_name_fields(self) -> str:
        """Return crop production record_name from domain service implementation."""
        return G2PRegisterDomainServiceProduction().construct_record_name(self.to_dict())


# All Register History classes should have the prefix G2PRegisterHistory
class G2PRegisterHistoryProduction(G2PRegisterHistory, G2PProduction):
    __tablename__ = "g2p_register_history_productions"
    __table_args__ = {"extend_existing": True}


# All Intake Form classes should have the prefix G2PIntakeForm
class G2PIntakeFormProduction(G2PIntakeForm, G2PRegister, G2PProduction):
    __tablename__ = "g2p_intake_form_productions"
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
        """Return crop production fields used to build search_text."""
        return G2PRegisterDomainServiceProduction().construct_search_text(self.to_dict())

    def get_record_name_fields(self) -> str:
        """Return crop production record_name from domain service implementation."""
        return G2PRegisterDomainServiceProduction().construct_record_name(self.to_dict())
