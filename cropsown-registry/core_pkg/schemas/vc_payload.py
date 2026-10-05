from typing import Optional
from pydantic import BaseModel


# =============================================================================
# VC Data Schemas (response payloads)
# =============================================================================

class VcConfigurationData(BaseModel):
    vc_config_id: str
    register_id: str
    intake_form_id: Optional[str] = None
    intake_form_mnemonic: Optional[str] = None
    data_model_id: Optional[str] = None
    data_model_mnemonic: Optional[str] = None
    vc_mnemonic: str
    descriptor_schema: dict

    class Config:
        from_attributes: bool = True


# =============================================================================
# VC Request Payload Schemas
# =============================================================================

class VcConfigurationRequestPayload(BaseModel):
    vc_config_id: Optional[str] = None
    register_id: Optional[str] = None
    intake_form_id: Optional[str] = None
    data_model_id: Optional[str] = None
    vc_mnemonic: Optional[str] = None
    descriptor_schema: Optional[dict] = None
