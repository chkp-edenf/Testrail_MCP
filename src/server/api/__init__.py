"""MCP Tool Registration

This module provides centralized tool registration and routing.
Returns a dictionary mapping tool names to their handler functions,
enabling clean dispatch through a single call handler.
"""

from typing import Callable, Awaitable
from mcp.types import TextContent
from ...client.api import TestRailClient

# Import all handlers
from .projects import handle_get_projects, handle_get_project
from .suites import handle_get_suites, handle_get_suite, handle_add_suite, handle_update_suite, handle_delete_suite
from .sections import (
    handle_get_sections, handle_get_section, handle_add_section,
    handle_update_section, handle_delete_section, handle_move_section
)
from .cases import (
    handle_get_cases, handle_get_case, handle_get_cases_by_ids, handle_add_case, handle_update_case,
    handle_delete_case, handle_get_case_history, handle_copy_cases_to_section,
    handle_move_cases_to_section, handle_update_cases, handle_delete_cases
)
from .tests import handle_get_tests, handle_get_test
from .runs import (
    handle_get_runs, handle_get_run, handle_add_run, handle_update_run,
    handle_close_run, handle_delete_run
)
from .plans import (
    handle_get_plans, handle_get_plan, handle_add_plan, handle_update_plan,
    handle_close_plan, handle_delete_plan,
    handle_add_plan_entry, handle_update_plan_entry, handle_delete_plan_entry
)
from .results import (
    handle_get_results, handle_get_results_for_case, handle_get_results_for_run,
    handle_add_result, handle_add_results, handle_add_result_for_case, handle_add_results_for_cases
)
from .case_fields import handle_get_case_fields, handle_get_case_types, handle_get_priorities, handle_get_templates
from .statuses import handle_get_statuses
from .users import handle_get_users, handle_get_user, handle_get_user_by_email
from .milestones import (
    handle_get_milestones, handle_get_milestone, handle_add_milestone,
    handle_update_milestone, handle_delete_milestone
)
from .configs import (
    handle_get_configs, handle_add_config_group, handle_add_config
)
from .health import handle_get_server_health
from .attachments import (
    handle_upload_attachment, handle_list_attachments,
    handle_get_attachment, handle_delete_attachment
)
from .shared_steps import (
    handle_get_shared_steps, handle_get_shared_step, handle_get_shared_step_history,
    handle_add_shared_step, handle_update_shared_step, handle_delete_shared_step
)


# Type alias for handler functions
ToolHandler = Callable[[dict, TestRailClient], Awaitable[list[TextContent]]]


def get_tool_handlers() -> dict[str, ToolHandler]:
    """Get routing map of tool names to handler functions
    
    Returns:
        Dictionary mapping tool names to async handler functions
    """
    return {
        # Projects
        "get_projects": handle_get_projects,
        "get_project": handle_get_project,
        
        # Suites
        "get_suites": handle_get_suites,
        "get_suite": handle_get_suite,
        "add_suite": handle_add_suite,
        "update_suite": handle_update_suite,
        "delete_suite": handle_delete_suite,
        
        # Sections
        "get_sections": handle_get_sections,
        "get_section": handle_get_section,
        "add_section": handle_add_section,
        "update_section": handle_update_section,
        "delete_section": handle_delete_section,
        "move_section": handle_move_section,
        
        # Cases
        "get_cases": handle_get_cases,
        "get_case": handle_get_case,
        "get_cases_by_ids": handle_get_cases_by_ids,
        "add_case": handle_add_case,
        "update_case": handle_update_case,
        "delete_case": handle_delete_case,
        "get_case_history": handle_get_case_history,
        "copy_cases_to_section": handle_copy_cases_to_section,
        "move_cases_to_section": handle_move_cases_to_section,
        "update_cases": handle_update_cases,
        "delete_cases": handle_delete_cases,
        
        # Tests
        "get_tests": handle_get_tests,
        "get_test": handle_get_test,
        
        # Runs
        "get_runs": handle_get_runs,
        "get_run": handle_get_run,
        "add_run": handle_add_run,
        "update_run": handle_update_run,
        "close_run": handle_close_run,
        "delete_run": handle_delete_run,
        
        # Plans
        "get_plans": handle_get_plans,
        "get_plan": handle_get_plan,
        "add_plan": handle_add_plan,
        "update_plan": handle_update_plan,
        "close_plan": handle_close_plan,
        "delete_plan": handle_delete_plan,
        "add_plan_entry": handle_add_plan_entry,
        "update_plan_entry": handle_update_plan_entry,
        "delete_plan_entry": handle_delete_plan_entry,
        
        # Results
        "get_results": handle_get_results,
        "get_results_for_case": handle_get_results_for_case,
        "get_results_for_run": handle_get_results_for_run,
        "add_result": handle_add_result,
        "add_result_for_case": handle_add_result_for_case,
        "add_results": handle_add_results,
        "add_results_for_cases": handle_add_results_for_cases,
        
        # Metadata
        "get_case_fields": handle_get_case_fields,
        "get_templates": handle_get_templates,
        "get_case_types": handle_get_case_types,
        "get_priorities": handle_get_priorities,
        "get_statuses": handle_get_statuses,
        
        # Users
        "get_users": handle_get_users,
        "get_user": handle_get_user,
        "get_user_by_email": handle_get_user_by_email,
        
        # Milestones
        "get_milestones": handle_get_milestones,
        "get_milestone": handle_get_milestone,
        "add_milestone": handle_add_milestone,
        "update_milestone": handle_update_milestone,
        "delete_milestone": handle_delete_milestone,
        
        # Configurations
        "get_configs": handle_get_configs,
        "add_config_group": handle_add_config_group,
        "add_config": handle_add_config,
        
        # Health
        "get_server_health": handle_get_server_health,

        # Attachments
        "upload_attachment": handle_upload_attachment,
        "list_attachments": handle_list_attachments,
        "get_attachment": handle_get_attachment,
        "delete_attachment": handle_delete_attachment,

        # Shared Steps
        "get_shared_steps": handle_get_shared_steps,
        "get_shared_step": handle_get_shared_step,
        "get_shared_step_history": handle_get_shared_step_history,
        "add_shared_step": handle_add_shared_step,
        "update_shared_step": handle_update_shared_step,
        "delete_shared_step": handle_delete_shared_step,
    }


__all__ = [
    "get_tool_handlers",
    # Re-export handlers for backwards compatibility
    "handle_get_projects",
    "handle_get_project",
    "handle_get_suites",
    "handle_get_suite",
    "handle_add_suite",
    "handle_update_suite",
    "handle_delete_suite",
    "handle_get_sections",
    "handle_get_section",
    "handle_add_section",
    "handle_update_section",
    "handle_delete_section",
    "handle_move_section",
    "handle_get_cases",
    "handle_get_case",
    "handle_get_cases_by_ids",
    "handle_add_case",
    "handle_update_case",
    "handle_delete_case",
    "handle_get_case_history",
    "handle_copy_cases_to_section",
    "handle_move_cases_to_section",
    "handle_update_cases",
    "handle_delete_cases",
    "handle_get_tests",
    "handle_get_test",
    "handle_get_runs",
    "handle_get_run",
    "handle_add_run",
    "handle_update_run",
    "handle_close_run",
    "handle_delete_run",
    "handle_get_plans",
    "handle_get_plan",
    "handle_add_plan",
    "handle_update_plan",
    "handle_close_plan",
    "handle_delete_plan",
    "handle_add_plan_entry",
    "handle_update_plan_entry",
    "handle_delete_plan_entry",
    "handle_get_results",
    "handle_get_results_for_case",
    "handle_get_results_for_run",
    "handle_add_result",
    "handle_add_result_for_case",
    "handle_add_results",
    "handle_add_results_for_cases",
    "handle_get_case_fields",
    "handle_get_templates",
    "handle_get_case_types",
    "handle_get_priorities",
    "handle_get_statuses",
    "handle_get_users",
    "handle_get_user",
    "handle_get_user_by_email",
    "handle_get_milestones",
    "handle_get_milestone",
    "handle_add_milestone",
    "handle_update_milestone",
    "handle_delete_milestone",
    "handle_get_configs",
    "handle_add_config_group",
    "handle_add_config",
    "handle_get_server_health",
    "handle_upload_attachment",
    "handle_list_attachments",
    "handle_get_attachment",
    "handle_delete_attachment",
    "handle_get_shared_steps",
    "handle_get_shared_step",
    "handle_get_shared_step_history",
    "handle_add_shared_step",
    "handle_update_shared_step",
    "handle_delete_shared_step",
]

