"""Shared-step-related schemas.

Shared Steps require TestRail 7.0+; step history requires 7.3+.
"""


from pydantic import BaseModel, Field

from .common import PaginatedResponse


class SharedStepDetail(BaseModel):
    """A single step inside a shared step set (custom_steps_separated entry)"""
    content: str | None = None
    additional_info: str | None = None
    expected: str | None = None
    refs: str | None = None


class SharedStep(BaseModel):
    """TestRail Shared Step schema"""
    id: int
    title: str
    project_id: int | None = None
    created_by: int | None = None
    created_on: int | None = None
    updated_by: int | None = None
    updated_on: int | None = None
    custom_steps_separated: list[SharedStepDetail] = Field(default_factory=list)
    case_ids: list[int] = Field(default_factory=list)


class SharedStepsResponse(PaginatedResponse):
    """Response for get_shared_steps endpoint"""
    shared_steps: list[SharedStep] = Field(default_factory=list)


# Input schemas for MCP tool validation
class GetSharedStepsInput(BaseModel):
    """Input schema for getting shared steps"""
    project_id: int | str = Field(..., description="Project ID")
    created_after: int | str | None = Field(None, description="✅ Only return shared steps created after this date (Unix timestamp or ISO 8601) (API-supported)")
    created_before: int | str | None = Field(None, description="✅ Only return shared steps created before this date (Unix timestamp or ISO 8601) (API-supported)")
    created_by: str | None = Field(None, description="✅ Comma-separated list of creator user IDs to filter by (API-supported)")
    updated_after: int | str | None = Field(None, description="✅ Only return shared steps updated after this date (Unix timestamp or ISO 8601) (API-supported)")
    updated_before: int | str | None = Field(None, description="✅ Only return shared steps updated before this date (Unix timestamp or ISO 8601) (API-supported)")
    refs: str | None = Field(None, description="✅ Filter by a single reference ID (e.g. TR-a, 4291) (API-supported)")
    limit: int | None = Field(None, description="✅ Maximum number of shared steps to return (default 250) (API-supported)")
    offset: int | None = Field(None, description="✅ Pagination offset (API-supported)")


class GetSharedStepInput(BaseModel):
    """Input schema for getting a specific set of shared steps"""
    shared_step_id: str = Field(..., description="Shared step ID")


class SharedStepDetailPayload(BaseModel):
    """A single step in a shared step set. At least one field should be set."""
    content: str | None = Field(None, description="The text contents of the 'Step' field (HTML)")
    additional_info: str | None = Field(None, description="The text contents of the 'Additional Info' field (HTML)")
    expected: str | None = Field(None, description="The text contents of the 'Expected Result' field (HTML)")
    refs: str | None = Field(None, description="Reference information for the 'References' field")


class AddSharedStepPayload(BaseModel):
    """Payload for creating a new set of shared steps"""
    title: str = Field(..., description="The title for the set of steps (required)")
    custom_steps_separated: list[SharedStepDetailPayload] | None = Field(
        None, description="Array of step objects. Each object contains content/additional_info/expected/refs."
    )

    class Config:
        populate_by_name = True


class UpdateSharedStepPayload(BaseModel):
    """Payload for updating a set of shared steps.

    Submitting custom_steps_separated REPLACES all existing steps — send the
    complete array.
    """
    title: str | None = Field(None, description="The title for the set of steps")
    custom_steps_separated: list[SharedStepDetailPayload] | None = Field(
        None, description="Array of step objects. REPLACES all existing steps — send the complete list."
    )

    class Config:
        populate_by_name = True
