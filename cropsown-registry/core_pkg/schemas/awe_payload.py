from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from ..models.enum import AwePolicyScopeEnum


class AwePolicyConfigurationData(BaseModel):
    awe_policy_config_id: str
    policy_scope: AwePolicyScopeEnum
    register_id: str
    intake_form_id: Optional[str] = None
    section_id: Optional[str] = None
    policy_type: str
    policy_key: str
    context_field_names: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class CreateAwePolicyConfigurationRequestPayload(BaseModel):
    policy_scope: AwePolicyScopeEnum
    register_id: str
    intake_form_id: Optional[str] = None
    section_id: Optional[str] = None
    policy_type: str
    policy_key: str
    context_field_names: Optional[List[str]] = None


class UpdateAwePolicyConfigurationRequestPayload(BaseModel):
    awe_policy_config_id: str
    policy_scope: Optional[AwePolicyScopeEnum] = None
    register_id: Optional[str] = None
    intake_form_id: Optional[str] = None
    section_id: Optional[str] = None
    policy_type: Optional[str] = None
    policy_key: Optional[str] = None
    context_field_names: Optional[List[str]] = None


class GetAwePolicyConfigurationRequestPayload(BaseModel):
    awe_policy_config_id: str


class DeleteAwePolicyConfigurationRequestPayload(BaseModel):
    awe_policy_config_id: str


class GetAllAwePolicyConfigurationsRequestPayload(BaseModel):
    pass
