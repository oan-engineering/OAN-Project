from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

from openg2p_fastapi_common.schemas import G2PRequest, G2PRequestBody, G2PResponse, G2PResponseBody


# =============================================================================
# Score Data Schemas
# =============================================================================


class GetScoresRequestPayload(BaseModel):
    """Payload for getting scores for a record."""
    link_internal_record_id: str = Field(..., description="Linked record internal record ID")


class ScoreData(BaseModel):
    """Individual score data."""
    score_type: str = Field(..., description="Type of score")
    computed_score: float = Field(..., description="Computed score value")
    computed_at: Optional[str] = Field(None, description="Timestamp when score was computed")
    triggered_by_cr_id: str = Field(..., description="Change request ID that triggered this computation")
    triggered_by_submission_id: Optional[str] = Field(
        None, description="Submission ID that triggered this computation (if any)"
    )


class GetScoresResponsePayload(BaseModel):
    """Response payload for getting scores."""
    scores: List[ScoreData] = Field(..., description="List of scores for the record")


# =============================================================================
# Score History Schemas
# =============================================================================


class GetScoreHistoryRequestPayload(BaseModel):
    """Payload for getting score history for a record."""
    link_internal_record_id: str = Field(..., description="Linked record internal record ID")
    score_type: str = Field(..., description="Type of score")


class ScoreHistoryData(BaseModel):
    """Historical score data."""
    computed_score: float = Field(..., description="Computed score value")
    computed_at: Optional[str] = Field(None, description="Timestamp when score was computed")
    triggered_by_cr_id: str = Field(..., description="Change request ID that triggered this computation")
    triggered_by_submission_id: Optional[str] = Field(
        None, description="Submission ID that triggered this computation (if any)"
    )


class GetScoreHistoryResponsePayload(BaseModel):
    """Response payload for getting score history."""
    history: List[ScoreHistoryData] = Field(..., description="List of historical scores")


# =============================================================================
# Score Definitions (metadata CRUD)
# =============================================================================


class ScoreContributingAttributeInput(BaseModel):
    """Contributing attribute row for create/update."""

    attribute_name: str = Field(..., description="Register field path or column name (e.g. headship_type)")
    attribute_computation_required: bool = Field(
        False, description="Whether a lookup/computation step is required for this attribute"
    )
    attribute_computation_value: Optional[dict[str, Any]] = Field(
        None,
        description='Optional map of raw values to contributions, e.g. {"CHILD_HEADED": 0.2}',
    )
    attribute_weightage: float = Field(..., description="Weightage for this attribute in the score")


class ScoreContributingAttributeData(BaseModel):
    """Persisted contributing attribute metadata."""

    contributing_attribute_id: str = Field(..., description="Contributing attribute row ID")
    attribute_name: str = Field(..., description="Register field path or column name")
    attribute_computation_required: bool = Field(
        ..., description="Whether a lookup/computation step is required for this attribute"
    )
    attribute_computation_value: Optional[dict[str, Any]] = Field(
        None, description="Value lookup / computation map (JSON)"
    )
    attribute_weightage: float = Field(..., description="Weightage for this attribute")


class ScoreDefinitionData(BaseModel):
    """Score definition header (use score-contributing-attribute APIs for attribute rows)."""

    score_definition_id: str = Field(..., description="Score definition ID")
    register_mnemonic: str = Field(..., description="Register mnemonic this score applies to")
    score_type: str = Field(..., description="Type of score")
    is_enabled: bool = Field(..., description="Whether the score definition is enabled")


class GetScoreDefinitionsRequestPayload(BaseModel):
    """Payload for getting score definitions for a register."""
    
    register_id: str = Field(..., description="Register definition ID")


class GetScoreDefinitionsResponsePayload(BaseModel):
    """Response payload for getting score definitions."""

    score_definitions: List[ScoreDefinitionData] = Field(..., description="Score definitions on this page")


class CreateScoreDefinitionRequestPayload(BaseModel):
    """Payload for creating a new score definition (header only)."""

    register_id: str = Field(..., description="Register definition ID")
    score_type: str = Field(..., description="Type of score")


class CreateScoreDefinitionResponsePayload(BaseModel):
    """Response payload for creating a score definition."""
    score_definition: ScoreDefinitionData = Field(..., description="Created score definition")


class UpdateScoreDefinitionRequestPayload(BaseModel):
    """Payload for updating an existing score definition (header only)."""

    score_definition_id: str = Field(..., description="Score definition ID")
    is_enabled: Optional[bool] = Field(None, description="Whether the score definition is enabled")


class UpdateScoreDefinitionResponsePayload(BaseModel):
    """Response payload for updating a score definition."""
    score_definition: ScoreDefinitionData = Field(..., description="Updated score definition")


class DeleteScoreDefinitionRequestPayload(BaseModel):
    score_definition_id: str = Field(..., description="Score definition ID to delete")


class DeleteScoreDefinitionResponsePayload(BaseModel):
    score_definition_id: str = Field(..., description="ID of the deleted score definition")


# =============================================================================
# Score contributing attributes (separate from definition header CRUD)
# =============================================================================


class GetAllScoreContributingAttributesRequestPayload(BaseModel):
    """Payload for listing contributing attributes for a score definition."""

    score_definition_id: str = Field(..., description="Score definition ID")


class GetAllScoreContributingAttributesResponsePayload(BaseModel):
    """List page only; pagination totals are in response_body.pagination_response."""

    contributing_attributes: List[ScoreContributingAttributeData] = Field(
        ...,
        description="Contributing attribute rows on this page",
    )


class CreateScoreContributingAttributeRequestPayload(BaseModel):
    """Create payload: score definition id plus attribute fields at the root."""

    score_definition_id: str = Field(..., description="Score definition ID")
    attribute_name: str = Field(..., description="Register field path or column name (e.g. headship_type)")
    attribute_computation_required: bool = Field(
        False, description="Whether a lookup/computation step is required for this attribute"
    )
    attribute_computation_value: Optional[dict[str, Any]] = Field(
        None,
        description='Optional map of raw values to contributions, e.g. {"CHILD_HEADED": 0.2}',
    )
    attribute_weightage: float = Field(..., description="Weightage for this attribute in the score")


class CreateScoreContributingAttributeResponsePayload(BaseModel):
    contributing_attribute: ScoreContributingAttributeData = Field(
        ..., description="Created contributing attribute row"
    )


class UpdateScoreContributingAttributeRequestPayload(BaseModel):
    contributing_attribute_id: str = Field(..., description="Contributing attribute row ID")
    attribute_name: Optional[str] = Field(None, description="Register field path or column name")
    attribute_computation_required: Optional[bool] = Field(
        None, description="Whether a lookup/computation step is required for this attribute"
    )
    attribute_computation_value: Optional[dict[str, Any]] = Field(
        None, description="Value lookup / computation map (JSON)"
    )
    attribute_weightage: Optional[float] = Field(None, description="Weightage for this attribute in the score")


class UpdateScoreContributingAttributeResponsePayload(BaseModel):
    contributing_attribute: ScoreContributingAttributeData = Field(
        ..., description="Updated contributing attribute row"
    )


class DeleteScoreContributingAttributeRequestPayload(BaseModel):
    contributing_attribute_id: str = Field(..., description="Contributing attribute row ID to delete")


class DeleteScoreContributingAttributeResponsePayload(BaseModel):
    contributing_attribute_id: str = Field(..., description="ID of the deleted row")


# =============================================================================
# Score Data Request Schemas
# =============================================================================


class GetScoresRequestBody(G2PRequestBody):
    request_payload: GetScoresRequestPayload


class GetScoresRequest(G2PRequest):
    request_body: GetScoresRequestBody


# =============================================================================
# Score History Request Schemas
# =============================================================================


class GetScoreHistoryRequestBody(G2PRequestBody):
    request_payload: GetScoreHistoryRequestPayload


class GetScoreHistoryRequest(G2PRequest):
    request_body: GetScoreHistoryRequestBody


# =============================================================================
# Score Definitions Request Schemas
# =============================================================================


class GetScoreDefinitionsRequestBody(G2PRequestBody):
    request_payload: GetScoreDefinitionsRequestPayload


class GetScoreDefinitionsRequest(G2PRequest):
    request_body: GetScoreDefinitionsRequestBody


class CreateScoreDefinitionRequestBody(G2PRequestBody):
    request_payload: CreateScoreDefinitionRequestPayload


class CreateScoreDefinitionRequest(G2PRequest):
    request_body: CreateScoreDefinitionRequestBody


class UpdateScoreDefinitionRequestBody(G2PRequestBody):
    request_payload: UpdateScoreDefinitionRequestPayload


class UpdateScoreDefinitionRequest(G2PRequest):
    request_body: UpdateScoreDefinitionRequestBody


class DeleteScoreDefinitionRequestBody(G2PRequestBody):
    request_payload: DeleteScoreDefinitionRequestPayload


class DeleteScoreDefinitionRequest(G2PRequest):
    request_body: DeleteScoreDefinitionRequestBody


class GetAllScoreContributingAttributesRequestBody(G2PRequestBody):
    request_payload: GetAllScoreContributingAttributesRequestPayload


class GetAllScoreContributingAttributesRequest(G2PRequest):
    request_body: GetAllScoreContributingAttributesRequestBody


class CreateScoreContributingAttributeRequestBody(G2PRequestBody):
    request_payload: CreateScoreContributingAttributeRequestPayload


class CreateScoreContributingAttributeRequest(G2PRequest):
    request_body: CreateScoreContributingAttributeRequestBody


class UpdateScoreContributingAttributeRequestBody(G2PRequestBody):
    request_payload: UpdateScoreContributingAttributeRequestPayload


class UpdateScoreContributingAttributeRequest(G2PRequest):
    request_body: UpdateScoreContributingAttributeRequestBody


class DeleteScoreContributingAttributeRequestBody(G2PRequestBody):
    request_payload: DeleteScoreContributingAttributeRequestPayload


class DeleteScoreContributingAttributeRequest(G2PRequest):
    request_body: DeleteScoreContributingAttributeRequestBody


# =============================================================================
# Response Wrappers (staff portal style)
# =============================================================================


class GetScoresResponseBody(G2PResponseBody):
    response_payload: Optional[GetScoresResponsePayload] = None


class GetScoresResponse(G2PResponse):
    response_body: Optional[GetScoresResponseBody] = None


class GetScoreHistoryResponseBody(G2PResponseBody):
    response_payload: Optional[GetScoreHistoryResponsePayload] = None


class GetScoreHistoryResponse(G2PResponse):
    response_body: Optional[GetScoreHistoryResponseBody] = None


class GetScoreDefinitionsResponseBody(G2PResponseBody):
    response_payload: Optional[GetScoreDefinitionsResponsePayload] = None


class GetScoreDefinitionsResponse(G2PResponse):
    response_body: Optional[GetScoreDefinitionsResponseBody] = None


class CreateScoreDefinitionResponseBody(G2PResponseBody):
    response_payload: Optional[CreateScoreDefinitionResponsePayload] = None


class CreateScoreDefinitionResponse(G2PResponse):
    response_body: Optional[CreateScoreDefinitionResponseBody] = None


class UpdateScoreDefinitionResponseBody(G2PResponseBody):
    response_payload: Optional[UpdateScoreDefinitionResponsePayload] = None


class UpdateScoreDefinitionResponse(G2PResponse):
    response_body: Optional[UpdateScoreDefinitionResponseBody] = None


class DeleteScoreDefinitionResponseBody(G2PResponseBody):
    response_payload: Optional[DeleteScoreDefinitionResponsePayload] = None


class DeleteScoreDefinitionResponse(G2PResponse):
    response_body: Optional[DeleteScoreDefinitionResponseBody] = None


class GetAllScoreContributingAttributesResponseBody(G2PResponseBody):
    response_payload: Optional[GetAllScoreContributingAttributesResponsePayload] = None


class GetAllScoreContributingAttributesResponse(G2PResponse):
    response_body: Optional[GetAllScoreContributingAttributesResponseBody] = None


class CreateScoreContributingAttributeResponseBody(G2PResponseBody):
    response_payload: Optional[CreateScoreContributingAttributeResponsePayload] = None


class CreateScoreContributingAttributeResponse(G2PResponse):
    response_body: Optional[CreateScoreContributingAttributeResponseBody] = None


class UpdateScoreContributingAttributeResponseBody(G2PResponseBody):
    response_payload: Optional[UpdateScoreContributingAttributeResponsePayload] = None


class UpdateScoreContributingAttributeResponse(G2PResponse):
    response_body: Optional[UpdateScoreContributingAttributeResponseBody] = None


class DeleteScoreContributingAttributeResponseBody(G2PResponseBody):
    response_payload: Optional[DeleteScoreContributingAttributeResponsePayload] = None


class DeleteScoreContributingAttributeResponse(G2PResponse):
    response_body: Optional[DeleteScoreContributingAttributeResponseBody] = None
