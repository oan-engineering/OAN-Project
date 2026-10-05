import uuid

from sqlalchemy import Boolean, Integer, String, Text, JSON, Float, Index, text
from sqlalchemy.orm import Mapped, mapped_column, validates
from openg2p_fastapi_common.models import BaseORMModel

from .enum import RegisterPurposeEnum
from .g2p_register_tab import G2PRegisterUITab, G2PRegisterUITabSection

class G2PRegisterDefinition(BaseORMModel):
    __tablename__ = "g2p_register_definitions"

    register_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    register_mnemonic: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    register_subject: Mapped[str] = mapped_column(String, nullable=True)
    register_description: Mapped[Text] = mapped_column(Text, nullable=True)
    master_register_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    register_rank: Mapped[int] = mapped_column(Integer, nullable=True)

    # ID generation
    functional_id_generation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Register type flags
    register_purpose: Mapped[RegisterPurposeEnum] = mapped_column(String, nullable=False)
    program_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    program_mnemonic: Mapped[str] = mapped_column(String, nullable=True, index=True)

    # Register display configuration
    register_icon: Mapped[str] = mapped_column(Text, nullable=True)  # BASE64 encoded icon
    has_image: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Deduplication configuration
    dedup_is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dedup_threshold_score: Mapped[float] = mapped_column(Float, nullable=True)

    # Completion score configuration
    completion_score_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Outgest configuration
    outgest_applicable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Registrant authentication configuration
    requires_registrant_authentication: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    registrant_authentication_validity_days: Mapped[int] = mapped_column(Integer, nullable=True, default=730)
    registrant_re_auth_warning_days_before: Mapped[int] = mapped_column(Integer, nullable=True, default=30)

    @validates('register_mnemonic')
    def set_register_subject(self, _key: str, register_mnemonic_value: str) -> str:
        """
        Automatically set register_subject to the plural form of register_mnemonic
        with the first letter capitalized.
        Example: 'farmer' -> 'Farmers'
        """
        if register_mnemonic_value:
            plural_form: str = register_mnemonic_value + 's'
            capitalized_plural: str = plural_form[0].upper() + plural_form[1:]
            self.register_subject = capitalized_plural
        return register_mnemonic_value
