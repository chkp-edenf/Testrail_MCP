"""Re-export shim — relocated to testrail_core.schemas.shared_steps (plan-004 phase 5)."""
from testrail_core.schemas.shared_steps import (
    AddSharedStepPayload,
    GetSharedStepInput,
    GetSharedStepsInput,
    SharedStep,
    SharedStepDetail,
    SharedStepDetailPayload,
    SharedStepsResponse,
    UpdateSharedStepPayload,
)

__all__ = [
    "AddSharedStepPayload",
    "GetSharedStepInput",
    "GetSharedStepsInput",
    "SharedStep",
    "SharedStepDetail",
    "SharedStepDetailPayload",
    "SharedStepsResponse",
    "UpdateSharedStepPayload",
]
