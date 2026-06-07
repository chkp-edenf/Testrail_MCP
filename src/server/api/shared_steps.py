"""Shared step handler functions.

Shared Steps require TestRail 7.0+; get_shared_step_history requires 7.3+.
"""

import json
import logging
from datetime import datetime

from mcp.types import TextContent

from ...client.api import TestRailClient
from ...shared.schemas.shared_steps import GetSharedStepsInput
from .utils import create_error_response, create_success_response, truncate_output

logger = logging.getLogger(__name__)


def _to_timestamp(value: int | str) -> int:
    """Coerce an int/numeric-string/ISO 8601 date into a Unix timestamp."""
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    # ISO 8601 — tolerate a trailing 'Z'
    return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())


def format_shared_step(step: dict) -> str:
    """Format a single shared step set for display"""
    output = f"**{step.get('title', 'Untitled')}** (ID: {step.get('id')})\n"
    project_id = step.get("project_id")
    if project_id is not None:
        output += f"  └─ Project ID: {project_id}\n"

    steps = step.get("custom_steps_separated") or []
    output += f"  └─ Steps: {len(steps)}\n"
    for idx, detail in enumerate(steps, start=1):
        content = (detail.get("content") or "").strip()
        preview = content[:80] + "..." if len(content) > 80 else content
        output += f"     {idx}. {preview or '(empty)'}\n"

    case_ids = step.get("case_ids") or []
    if case_ids:
        output += f"  └─ Used by {len(case_ids)} case(s): {case_ids}\n"

    return output


async def handle_get_shared_steps(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get shared steps for a project with filtering support"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")

    try:
        input_data = GetSharedStepsInput(**arguments)
        project_id = int(input_data.project_id)

        created_after = _to_timestamp(input_data.created_after) if input_data.created_after else None
        created_before = _to_timestamp(input_data.created_before) if input_data.created_before else None
        updated_after = _to_timestamp(input_data.updated_after) if input_data.updated_after else None
        updated_before = _to_timestamp(input_data.updated_before) if input_data.updated_before else None
        limit = int(input_data.limit) if input_data.limit else None
        offset = int(input_data.offset) if input_data.offset else None

        result = await client.shared_steps.get_shared_steps(
            project_id=project_id,
            created_after=created_after,
            created_before=created_before,
            created_by=input_data.created_by,
            updated_after=updated_after,
            updated_before=updated_before,
            refs=input_data.refs,
            limit=limit,
            offset=offset,
        )
        shared_steps = result.get("shared_steps", [])

        if not shared_steps:
            response = create_success_response(
                "No shared steps found",
                {"shared_steps": [], "count": 0},
            )
        else:
            output = f"**Shared Steps for Project {project_id}**\n\n"
            for step in shared_steps:
                output += format_shared_step(step) + "\n"

            response = create_success_response(
                f"Found {len(shared_steps)} shared step set(s)",
                {
                    "shared_steps": shared_steps,
                    "count": len(shared_steps),
                    "formatted": truncate_output(output),
                },
            )

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        logger.error(f"Error in get_shared_steps: {str(e)}")
        response = create_error_response("Failed to fetch shared steps", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_shared_step(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get details of a specific set of shared steps"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")

    try:
        shared_step_id = int(arguments["shared_step_id"])
        result = await client.shared_steps.get_shared_step(shared_step_id)

        output = f"**Shared Step Details**\n\n{format_shared_step(result)}"
        response = create_success_response(
            f"Retrieved shared step {shared_step_id}",
            {"shared_step": result, "formatted": truncate_output(output)},
        )

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        logger.error(f"Error in get_shared_step: {str(e)}")
        response = create_error_response("Failed to fetch shared step", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_shared_step_history(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Get the change history of a set of shared steps (TestRail 7.3+)"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")

    try:
        shared_step_id = int(arguments["shared_step_id"])
        result = await client.shared_steps.get_shared_step_history(shared_step_id)

        history = result.get("step_history", []) if isinstance(result, dict) else []
        response = create_success_response(
            f"Retrieved history for shared step {shared_step_id} ({len(history)} change(s))",
            {"step_history": history, "count": len(history), "raw": result},
        )

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        logger.error(f"Error in get_shared_step_history: {str(e)}")
        response = create_error_response("Failed to fetch shared step history", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_add_shared_step(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Create a new set of shared steps"""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")

    try:
        project_id = int(arguments["project_id"])

        if not arguments.get("title"):
            raise ValueError("Missing required field: title")

        data: dict = {"title": arguments["title"]}
        if arguments.get("custom_steps_separated") is not None:
            data["custom_steps_separated"] = arguments["custom_steps_separated"]

        result = await client.shared_steps.add_shared_step(project_id, data)

        output = f"**Shared Step Created**\n\n{format_shared_step(result)}"
        response = create_success_response(
            f"Successfully created shared step '{result.get('title')}'",
            {"shared_step": result, "formatted": truncate_output(output)},
        )

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        logger.error(f"Error in add_shared_step: {str(e)}")
        response = create_error_response("Failed to create shared step", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_update_shared_step(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Update an existing set of shared steps.

    Submitting custom_steps_separated REPLACES all existing steps.
    """
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")

    try:
        shared_step_id = int(arguments["shared_step_id"])
        data: dict = {}

        if arguments.get("title"):
            data["title"] = arguments["title"]
        if arguments.get("custom_steps_separated") is not None:
            data["custom_steps_separated"] = arguments["custom_steps_separated"]

        if not data:
            response = create_error_response(
                "No update fields provided", Exception("No fields specified")
            )
            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        result = await client.shared_steps.update_shared_step(shared_step_id, data)

        output = f"**Shared Step Updated**\n\n{format_shared_step(result)}"
        response = create_success_response(
            f"Successfully updated shared step {shared_step_id}",
            {"shared_step": result, "formatted": truncate_output(output)},
        )

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        logger.error(f"Error in update_shared_step: {str(e)}")
        response = create_error_response("Failed to update shared step", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_delete_shared_step(arguments: dict, client: TestRailClient) -> list[TextContent]:
    """Delete a set of shared steps. Cannot be undone."""
    logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")

    try:
        shared_step_id = int(arguments["shared_step_id"])

        # Default True (keep steps in referencing cases). Accept bool/int/str.
        keep_raw = arguments.get("keep_in_cases", True)
        if isinstance(keep_raw, str):
            keep_in_cases = keep_raw.strip().lower() not in ("0", "false", "no", "off")
        else:
            keep_in_cases = bool(keep_raw)

        await client.shared_steps.delete_shared_step(shared_step_id, keep_in_cases=keep_in_cases)

        detail = (
            "steps kept in referencing cases"
            if keep_in_cases
            else "steps also removed from referencing cases"
        )
        response = create_success_response(
            f"Successfully deleted shared step {shared_step_id}",
            {
                "shared_step_id": shared_step_id,
                "keep_in_cases": keep_in_cases,
                "formatted": f"Shared step {shared_step_id} has been deleted ({detail})",
            },
        )

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        logger.error(f"Error in delete_shared_step: {str(e)}")
        response = create_error_response("Failed to delete shared step", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
