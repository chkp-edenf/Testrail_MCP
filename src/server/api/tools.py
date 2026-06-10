"""MCP Tool Definitions for TestRail

This module contains all Tool() schema definitions organized by resource type.
Separating tool definitions from stdio.py keeps the entry point clean and focused.
"""

from mcp.types import Tool

from .aliases import get_alias_tool_defs


def get_all_tools() -> list[Tool]:
    """Get all TestRail MCP tool definitions.

    Returns the 62 canonical tool definitions plus, when
    `TESTRAIL_LEGACY_ALIASES` is enabled, 28 bun913 compatibility
    aliases. Aliases are listed alongside the canonical tools so
    consumers migrating from `@bun913/mcp-testrail` see their existing
    tool names available.
    """
    canonical_tools: list[Tool] = [
        # ==================== PROJECTS ====================
        Tool(
            name="get_projects",
            description="""Get all TestRail projects for discovery and exploration.

WHEN TO USE:
- Discovering available projects in the TestRail instance
- Browsing all projects for selection
- User needs to explore what projects exist

WHEN TO SKIP:
- project_id is already known from user input
- Use get_project for details of a specific known project ID""",
            inputSchema={
                "type": "object",
                "properties": {
                    "is_completed": {"type": "integer", "description": "Filter by completion status: 1 for completed, 0 for active (optional)"},
                    "limit": {"type": "integer", "description": "Maximum number of projects to return (optional)"},
                    "offset": {"type": "integer", "description": "Number of projects to skip for pagination (optional)"}
                },
                "required": []
            }
        ),
        Tool(
            name="get_project",
            description="""Get details and validate a specific project by ID.

WHEN TO USE:
- Need detailed project information for a known project_id
- Validating that a project_id exists

WHEN TO SKIP:
- Project details not needed and project_id already validated
- Proceed directly with operations requiring project_id""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"}
                },
                "required": ["project_id"]
            }
        ),
        
        # ==================== SUITES ====================
        Tool(
            name="get_suites",
            description="""Get all test suites for a project to discover available suites.

WHEN TO USE:
- Discovering available suites in a project
- User needs to select from suite options
- Exploring suite structure

WHEN TO SKIP:
- suite_id is already provided by user
- Use get_suite for details of a specific known suite ID""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_suite",
            description="""Get details of a specific test suite by ID.

WHEN TO USE:
- Need detailed suite information for a known suite_id
- Validating suite existence

WHEN TO SKIP:
- Suite details not needed and suite_id already known
- Proceed directly with operations requiring suite_id""",
            inputSchema={
                "type": "object",
                "properties": {
                    "suite_id": {"type": "string", "description": "Suite ID"}
                },
                "required": ["suite_id"]
            }
        ),
        Tool(
            name="add_suite",
            description="Create a new test suite",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "name": {"type": "string", "description": "Suite name"},
                    "description": {"type": "string", "description": "Suite description (optional)"}
                },
                "required": ["project_id", "name"]
            }
        ),
        Tool(
            name="update_suite",
            description="Update an existing test suite",
            inputSchema={
                "type": "object",
                "properties": {
                    "suite_id": {"type": "string", "description": "Suite ID"},
                    "name": {"type": "string", "description": "New suite name (optional)"},
                    "description": {"type": "string", "description": "New suite description (optional)"}
                },
                "required": ["suite_id"]
            }
        ),
        Tool(
            name="delete_suite",
            description="Delete a test suite (soft delete)",
            inputSchema={
                "type": "object",
                "properties": {
                    "suite_id": {"type": "string", "description": "Suite ID"}
                },
                "required": ["suite_id"]
            }
        ),
        
        # ==================== SECTIONS ====================
        Tool(
            name="get_sections",
            description="Get all sections for a project/suite",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "suite_id": {"type": "string", "description": "Suite ID (optional, filters sections by suite)"},
                    "limit": {"type": "integer", "description": "Maximum number of sections to return (optional, requires TestRail 6.7+)"},
                    "offset": {"type": "integer", "description": "Number of sections to skip for pagination (optional, requires TestRail 6.7+)"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_section",
            description="Get details of a specific section",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"}
                },
                "required": ["section_id"]
            }
        ),
        Tool(
            name="add_section",
            description="Create a new section in a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "name": {"type": "string", "description": "Section name"},
                    "description": {"type": "string", "description": "Section description (optional)"},
                    "suite_id": {"type": "string", "description": "Suite ID (optional, for multi-suite projects)"},
                    "parent_id": {"type": "string", "description": "Parent section ID (optional, for nested sections)"}
                },
                "required": ["project_id", "name"]
            }
        ),
        Tool(
            name="update_section",
            description="Update an existing section",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"},
                    "name": {"type": "string", "description": "New section name (optional)"},
                    "description": {"type": "string", "description": "New section description (optional)"}
                },
                "required": ["section_id"]
            }
        ),
        Tool(
            name="delete_section",
            description="Delete a section (soft delete)",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"}
                },
                "required": ["section_id"]
            }
        ),
        Tool(
            name="move_section",
            description="Move section to different parent or change display order",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"},
                    "parent_id": {"type": "string", "description": "New parent section ID (optional)"},
                    "after_id": {"type": "string", "description": "Section ID to place after (optional, for ordering)"}
                },
                "required": ["section_id"]
            }
        ),
        
        # ==================== CASES ====================
        Tool(
            name="get_cases",
            description="""Get test case definitions (templates) for a project/suite with optional filtering.

DATA MODEL CLARITY:
- Test Cases = Reusable test definitions/templates stored in project/suite
- Tests = Instances of cases within a specific test run (use get_tests for run instances)

WHEN TO USE:
- Browsing/discovering test cases in a project or suite
- Filtering cases by section, priority, type, template, etc.
- Working with case definitions (not run instances)
- Paginating through large case sets

WHEN TO SKIP - USE ALTERNATIVES INSTEAD:
- ✅ If you have specific case IDs: Use get_cases_by_ids (batch) or get_case (single)
- ✅ If working with test run instances: Use get_tests

FILTERING CAPABILITIES:
- ✅ API-supported filters (fast, server-side):
  * section_id, template_id: Filter by structure
  * priority_id, type_id, milestone_id: Filter by attributes
  * created_by, created_after, created_before: Filter by creation
  * updated_by, updated_after, updated_before: Filter by modification
  * limit/offset: Pagination controls

PERFORMANCE TIP:
- Use API-supported filters for large datasets
- When case IDs are known, prefer get_cases_by_ids over pagination
- Filters are applied server-side for efficiency""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "suite_id": {"type": "string", "description": "Suite ID (optional)"},
                    "limit": {"type": "string", "description": "Max results (default 250)"},
                    "section_id": {"type": ["integer", "string"], "description": "✅ Filter by section ID (API-supported)"},
                    "template_id": {"type": ["integer", "string"], "description": "✅ Filter by template ID (API-supported)"},
                    "offset": {"type": ["integer", "string"], "description": "✅ Pagination offset (API-supported)"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_cases_by_ids",
            description="""Fetch multiple specific test cases by a list of case IDs (batch operation).

WHEN TO USE:
- You have a specific list of case IDs to retrieve
- More efficient than calling get_case multiple times
- More precise than get_cases pagination when exact IDs are known
- User provided specific case numbers to fetch

WHEN TO SKIP - USE ALTERNATIVES:
- If fetching only 1 case: Use get_case instead
- If discovering cases by filters: Use get_cases
- If working with test run instances: Use get_tests

EXAMPLE USAGE:
- User says: "Get cases 123, 456, 789" → Use this tool
- User says: "Get all cases in section X" → Use get_cases with section_id filter

SEE ALSO: get_case (single ID), get_cases (discover/filter)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs (e.g., '123,456,789')"}
                },
                "required": ["case_ids"]
            }
        ),
        Tool(
            name="get_case",
            description="""Get complete details of a specific test case by ID.

WHEN TO USE:
- Fetching details for a single known case_id
- Need full case information including all custom fields

WHEN TO SKIP - USE ALTERNATIVES:
- If fetching multiple cases: Use get_cases_by_ids (more efficient)
- If discovering cases: Use get_cases with filters

SEE ALSO: get_cases_by_ids (bulk fetch), get_cases (discover/filter)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "Test case ID"}
                },
                "required": ["case_id"]
            }
        ),
        Tool(
            name="add_case",
            description="Create a new test case in a section. Use get_case_fields to discover available custom fields for your TestRail instance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Section ID"},
                    "title": {"type": "string", "description": "Test case title"},
                    "template_id": {"type": "string", "description": "Template ID (optional)"},
                    "type_id": {"type": "string", "description": "Test case type ID (optional). Use get_case_types to retrieve valid type IDs."},
                    "priority_id": {"type": "string", "description": "Priority ID (optional). Use get_priorities to retrieve valid priority IDs."},
                    "estimate": {"type": "string", "description": "Time estimate (optional)"},
                    "refs": {"type": "string", "description": "References/requirements (optional)"},
                    "custom_fields": {"type": "string", "description": "JSON object containing custom fields as key-value pairs. Example: '{\"custom_field1\": \"value\", \"custom_field2\": \"option1,option2\"}'. Use get_case_fields to discover available custom fields and their valid values for your TestRail instance. Field values can be provided as human-readable strings or numeric IDs - the MCP will convert them automatically. (optional)"}
                },
                "required": ["section_id", "title"]
            }
        ),
        Tool(
            name="update_case",
            description="Update an existing test case. Use get_case_fields to discover available custom fields for your TestRail instance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "Test case ID"},
                    "title": {"type": "string", "description": "New title (optional)"},
                    "template_id": {"type": "string", "description": "Template ID (optional)"},
                    "type_id": {"type": "string", "description": "Test case type ID (optional). Use get_case_types to retrieve valid type IDs."},
                    "priority_id": {"type": "string", "description": "Priority ID (optional). Use get_priorities to retrieve valid priority IDs."},
                    "estimate": {"type": "string", "description": "Time estimate (optional)"},
                    "refs": {"type": "string", "description": "References/requirements (optional)"},
                    "custom_fields": {"type": "string", "description": "JSON object containing custom fields as key-value pairs. Example: '{\"custom_field1\": \"new_value\", \"custom_field2\": \"updated_text\"}'. Use get_case_fields to discover available custom fields for your instance. (optional)"}
                },
                "required": ["case_id"]
            }
        ),
        Tool(
            name="delete_case",
            description="Delete a test case (soft delete)",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "Test case ID"}
                },
                "required": ["case_id"]
            }
        ),
        Tool(
            name="get_case_history",
            description="Get the change history for a test case",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "Test case ID"}
                },
                "required": ["case_id"]
            }
        ),
        Tool(
            name="copy_cases_to_section",
            description="Copy test cases to a different section",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Target section ID"},
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs (e.g., '123,456,789')"}
                },
                "required": ["section_id", "case_ids"]
            }
        ),
        Tool(
            name="move_cases_to_section",
            description="Move test cases to a different section",
            inputSchema={
                "type": "object",
                "properties": {
                    "section_id": {"type": "string", "description": "Target section ID"},
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs (e.g., '123,456,789')"}
                },
                "required": ["section_id", "case_ids"]
            }
        ),
        Tool(
            name="update_cases",
            description="Bulk update test cases. Use get_case_fields to discover available custom fields for your TestRail instance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "suite_id": {"type": "string", "description": "Suite ID"},
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs"},
                    "priority_id": {"type": "string", "description": "New priority ID (optional). Use get_priorities to retrieve valid priority IDs."},
                    "type_id": {"type": "string", "description": "New type ID (optional). Use get_case_types to retrieve valid type IDs."},
                    "template_id": {"type": "string", "description": "New template ID (optional)"},
                    "custom_fields": {"type": "string", "description": "JSON object containing custom fields to update as key-value pairs. Example: '{\"custom_field1\": \"value\", \"custom_field2\": \"option1,option2,option3\"}'. Use get_case_fields to discover available fields. (optional)"}
                },
                "required": ["suite_id", "case_ids"]
            }
        ),
        Tool(
            name="delete_cases",
            description="Bulk delete test cases (soft delete)",
            inputSchema={
                "type": "object",
                "properties": {
                    "suite_id": {"type": "string", "description": "Suite ID"},
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs"}
                },
                "required": ["suite_id", "case_ids"]
            }
        ),
        
        # ==================== TESTS ====================
        Tool(
            name="get_tests",
            description="""Get tests for a test run. Supports multiple filtering options for precise test queries.

FILTERING GUIDANCE:
- ✅ API-supported filters (faster, applied server-side):
  * status_id: Filter by test status (supports comma-separated values)
  * limit/offset: Pagination controls
  
- 🔧 Client-side filters (applied after API call):
  * assignedto_id: Filter by assigned user
  * priority_id: Filter by test priority
  * type_id: Filter by test case type
  
PERFORMANCE TIP: Use API-supported filters (status_id) for large datasets. Client-side filters are applied after fetching data, so combine with limit to avoid large transfers.

COMMON WORKFLOWS:
1. Count tests by status: Call get_tests with status_id filter, then count results
2. Find assignee's pending tests:
   - First: Call get_users to find user ID
   - Then: Call get_tests with assignedto_id filter
3. Analyze test distribution:
   - Call get_tests without filters to get all tests
   - Use client-side filters (assignedto_id, priority_id, type_id) to segment results

LOOKUP TOOLS:
- get_users: Retrieve valid user IDs for assignedto_id
- get_statuses: Retrieve valid status IDs
- get_priorities: Retrieve valid priority IDs
- get_case_types: Retrieve valid type IDs""",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"},
                    "status_id": {"type": "string", "description": "Filter by status ID (optional). Use get_statuses to discover available status IDs. Supports comma-separated values for multiple statuses."},
                    "assignedto_id": {"type": "integer", "description": "🔧 Filter by assigned user ID (client-side). Use get_users to retrieve valid user IDs."},
                    "priority_id": {"type": "integer", "description": "🔧 Filter by priority ID (client-side). Use get_priorities to retrieve valid priority IDs."},
                    "type_id": {"type": "integer", "description": "🔧 Filter by test type ID (client-side). Use get_case_types to retrieve valid type IDs."},
                    "limit": {"type": "integer", "description": "✅ Limit number of results (API-supported)"},
                    "offset": {"type": "integer", "description": "✅ Pagination offset (API-supported)"},
                    "with_data": {"type": "boolean", "description": "Include additional test data in response (optional, requires TestRail 7.4+)"}
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="get_test",
            description="Get details of a specific test",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_id": {"type": "string", "description": "Test ID"}
                },
                "required": ["test_id"]
            }
        ),
        
        # ==================== RUNS ====================
        Tool(
            name="get_runs",
            description="Get test runs for a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "limit": {"type": "string", "description": "Max results (default 250)"},
                    "suite_id": {"type": ["integer", "string"], "description": "✅ Filter by suite ID (API-supported)"},
                    "offset": {"type": "integer", "description": "✅ Pagination offset (API-supported)"},
                    "refs_filter": {"type": "string", "description": "Filter runs by references/requirements (optional)"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_run",
            description="Get details of a specific test run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"}
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="add_run",
            description="Create a new test run",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "name": {"type": "string", "description": "Run name"},
                    "description": {"type": "string", "description": "Run description (optional)"},
                    "suite_id": {"type": "string", "description": "Suite ID (optional)"},
                    "milestone_id": {"type": "string", "description": "Milestone ID (optional). Use get_milestones to retrieve valid milestone IDs for the project."},
                    "assignedto_id": {"type": "string", "description": "User ID to assign (optional). Use get_users to retrieve valid user IDs."},
                    "include_all": {"type": "string", "description": "Include all cases: true/false (optional)"},
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs (optional)"},
                    "refs": {"type": "string", "description": "References/requirements for the run (optional)"},
                    "start_on": {"type": "integer", "description": "Start date as Unix timestamp (optional)"},
                    "due_on": {"type": "integer", "description": "Due date as Unix timestamp (optional)"}
                },
                "required": ["project_id", "name"]
            }
        ),
        Tool(
            name="update_run",
            description="Update an existing test run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"},
                    "name": {"type": "string", "description": "New run name (optional)"},
                    "description": {"type": "string", "description": "New description (optional)"},
                    "milestone_id": {"type": "string", "description": "New milestone ID (optional). Use get_milestones to retrieve valid milestone IDs for the project."},
                    "include_all": {"type": "string", "description": "Include all cases: true/false (optional)"},
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs (optional)"},
                    "refs": {"type": "string", "description": "References/requirements for the run (optional)"},
                    "start_on": {"type": "integer", "description": "Start date as Unix timestamp (optional)"},
                    "due_on": {"type": "integer", "description": "Due date as Unix timestamp (optional)"}
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="close_run",
            description="Close a test run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"}
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="delete_run",
            description="Delete a test run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"}
                },
                "required": ["run_id"]
            }
        ),
        
        # ==================== PLANS ====================
        Tool(
            name="get_plans",
            description="Get test plans for a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "limit": {"type": "integer", "description": "✅ Limit number of results (API-supported)"},
                    "offset": {"type": "integer", "description": "✅ Pagination offset (API-supported)"},
                    "created_by": {"type": ["integer", "string"], "description": "✅ Filter by creator user ID (API-supported). Use get_users to retrieve valid user IDs."},
                    "created_after": {"type": "integer", "description": "✅ Filter plans created after timestamp (API-supported)"},
                    "created_before": {"type": "integer", "description": "✅ Filter plans created before timestamp (API-supported)"},
                    "milestone_id": {"type": ["integer", "string"], "description": "✅ Filter by milestone ID (API-supported). Use get_milestones to retrieve valid milestone IDs."},
                    "is_completed": {"type": ["integer", "boolean"], "description": "✅ Filter by completion status (API-supported)"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_plan",
            description="Get details of a specific test plan",
            inputSchema={
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "Test plan ID"}
                },
                "required": ["plan_id"]
            }
        ),
        Tool(
            name="add_plan",
            description="Create a new test plan",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "name": {"type": "string", "description": "Plan name"},
                    "description": {"type": "string", "description": "Plan description (optional)"},
                    "milestone_id": {"type": "string", "description": "Milestone ID (optional). Use get_milestones to retrieve valid milestone IDs for the project."},
                    "entries": {"type": "string", "description": "JSON array of plan entries (optional)"}
                },
                "required": ["project_id", "name"]
            }
        ),
        Tool(
            name="update_plan",
            description="Update an existing test plan",
            inputSchema={
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "Test plan ID"},
                    "name": {"type": "string", "description": "New plan name (optional)"},
                    "description": {"type": "string", "description": "New description (optional)"},
                    "milestone_id": {"type": "string", "description": "New milestone ID (optional). Use get_milestones to retrieve valid milestone IDs for the project."},
                    "entries": {"type": "string", "description": "JSON array of updated plan entries (optional)"}
                },
                "required": ["plan_id"]
            }
        ),
        Tool(
            name="close_plan",
            description="Close a test plan",
            inputSchema={
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "Test plan ID"}
                },
                "required": ["plan_id"]
            }
        ),
        Tool(
            name="delete_plan",
            description="Delete a test plan",
            inputSchema={
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "Test plan ID"}
                },
                "required": ["plan_id"]
            }
        ),
        Tool(
            name="add_plan_entry",
            description="Add a test run/entry to an existing plan",
            inputSchema={
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "Plan ID"},
                    "suite_id": {"type": "string", "description": "Suite ID (required)"},
                    "name": {"type": "string", "description": "Entry name (optional)"},
                    "description": {"type": "string", "description": "Entry description (optional)"},
                    "assignedto_id": {"type": "string", "description": "User ID to assign (optional). Use get_users to retrieve valid user IDs."},
                    "include_all": {"type": "string", "description": "Include all cases: true/false (optional)"},
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs (optional)"},
                    "config_ids": {"type": "string", "description": "Comma-separated config IDs (optional)"},
                    "runs": {"type": "string", "description": "JSON array of custom run configurations (optional)"}
                },
                "required": ["plan_id", "suite_id"]
            }
        ),
        Tool(
            name="update_plan_entry",
            description="Update an existing plan entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "Plan ID"},
                    "entry_id": {"type": "string", "description": "Entry ID to update"},
                    "name": {"type": "string", "description": "New entry name (optional)"},
                    "description": {"type": "string", "description": "New description (optional)"},
                    "assignedto_id": {"type": "string", "description": "New assignee user ID (optional). Use get_users to retrieve valid user IDs."},
                    "include_all": {"type": "string", "description": "Include all cases: true/false (optional)"},
                    "case_ids": {"type": "string", "description": "Comma-separated case IDs (optional)"},
                    "config_ids": {"type": "string", "description": "Comma-separated config IDs (optional)"}
                },
                "required": ["plan_id", "entry_id"]
            }
        ),
        Tool(
            name="delete_plan_entry",
            description="Remove an entry from a plan",
            inputSchema={
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "Plan ID"},
                    "entry_id": {"type": "string", "description": "Entry ID to delete"}
                },
                "required": ["plan_id", "entry_id"]
            }
        ),
        
        # ==================== RESULTS ====================
        Tool(
            name="get_results",
            description="Get results for a test",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_id": {"type": "string", "description": "Test ID"},
                    "limit": {"type": "string", "description": "Max results (default 250)"},
                    "offset": {"type": "integer", "description": "✅ Pagination offset (API-supported)"}
                },
                "required": ["test_id"]
            }
        ),
        Tool(
            name="get_results_for_case",
            description="Get results for a case in a run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"},
                    "case_id": {"type": "string", "description": "Test case ID"},
                    "limit": {"type": "string", "description": "Max results (default 250)"},
                    "offset": {"type": "integer", "description": "✅ Pagination offset (API-supported)"}
                },
                "required": ["run_id", "case_id"]
            }
        ),
        Tool(
            name="get_results_for_run",
            description="Get all results for a run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"},
                    "limit": {"type": "string", "description": "Max results (default 250)"},
                    "offset": {"type": "integer", "description": "✅ Pagination offset (API-supported)"},
                    "defects_filter": {"type": "string", "description": "Filter results by defect/bug IDs (optional)"}
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="add_result",
            description="""Add a result for a test. Accepts status by ID or name (e.g., '1', 'passed', 'failed').

WORKFLOW TIP: If unsure about available statuses, call get_statuses first to discover all valid status IDs and names for your TestRail instance.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_id": {"type": "string", "description": "Test ID"},
                    "status_id": {"type": "string", "description": "Status ID or name (e.g., '1', 'passed', 'failed', 'blocked'). Use get_statuses to discover all available status options. Accepts both numeric IDs and human-readable names."},
                    "comment": {"type": "string", "description": "Result comment (optional)"},
                    "version": {"type": "string", "description": "Version tested (optional)"},
                    "elapsed": {"type": "string", "description": "Time elapsed (optional)"},
                    "defects": {"type": "string", "description": "Defects/bugs found (optional)"},
                    "assignedto_id": {"type": "string", "description": "Assigned user ID (optional). Use get_users to retrieve valid user IDs for assignment."}
                },
                "required": ["test_id", "status_id"]
            }
        ),
        Tool(
            name="add_results",
            description="Add results for multiple tests in a run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"},
                    "results": {"type": "string", "description": "JSON array of results: [{\"test_id\": 1, \"status_id\": 1}, ...]"}
                },
                "required": ["run_id", "results"]
            }
        ),
        Tool(
            name="add_result_for_case",
            description="""Add a result for a case in a run. Alternative to add_result that doesn't require test_id.

USE CASES:
- When you know the run_id and case_id but don't have the test_id
- Simpler workflow for submitting results directly by case

COMPARISON WITH add_result:
- add_result: Requires test_id (the instance of a case in a run)
- add_result_for_case: Uses run_id + case_id (automatically finds the test)

WORKFLOW TIP: If unsure about available statuses, call get_statuses first to discover all valid status IDs and names for your TestRail instance.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"},
                    "case_id": {"type": "string", "description": "Test case ID"},
                    "status_id": {"type": "string", "description": "Status ID or name (e.g., '1', 'passed', 'failed', 'blocked'). Use get_statuses to discover all available status options. Accepts both numeric IDs and human-readable names."},
                    "comment": {"type": "string", "description": "Result comment (optional)"},
                    "version": {"type": "string", "description": "Version tested (optional)"},
                    "elapsed": {"type": "string", "description": "Time elapsed (optional)"},
                    "defects": {"type": "string", "description": "Defects/bugs found (optional)"},
                    "assignedto_id": {"type": "string", "description": "Assigned user ID (optional). Use get_users to retrieve valid user IDs for assignment."}
                },
                "required": ["run_id", "case_id", "status_id"]
            }
        ),
        Tool(
            name="add_results_for_cases",
            description="""Add results for multiple cases in a run. Bulk version of add_result_for_case.

USE CASES:
- Bulk submit results using case IDs instead of test IDs
- Simpler workflow when you have run_id and multiple case_ids

COMPARISON WITH add_results:
- add_results: Requires test_id for each result (instance of case in run)
- add_results_for_cases: Uses case_id for each result (automatically finds tests)

RESULT FORMAT:
Each result object should contain:
- case_id (required): The test case ID
- status_id (required): Status ID or name
- comment, version, elapsed, defects, assignedto_id (optional)

EXAMPLE:
results: '[{"case_id": 123, "status_id": "passed", "comment": "Test OK"}, {"case_id": 456, "status_id": "failed", "comment": "Bug found"}]'""",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Test run ID"},
                    "results": {"type": "string", "description": "JSON array of results: [{\"case_id\": 1, \"status_id\": 1, \"comment\": \"...\"}, ...]"}
                },
                "required": ["run_id", "results"]
            }
        ),
        
        # ==================== METADATA ====================
        Tool(
            name="get_case_fields",
            description="Get all available case fields including custom fields and their possible values",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_templates",
            description="Get all templates for a project. Templates are used to organize case fields and are required for case operations. Use this to discover available template IDs for the add_case, update_case, update_cases, and get_cases tools.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_case_types",
            description="""Get all available case types and populate cache for smart resolution. Returns type IDs for test case categorization and filtering.

CROSS-REFERENCES:
- Use returned type IDs with add_case, update_case, update_cases (type_id parameter)
- Use returned type IDs with get_tests (type_id filter)
- Note: get_tests uses client-side filtering for type_id""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_priorities",
            description="""Get all available priorities and populate cache for smart resolution. Returns priority IDs for test case management and filtering.

CROSS-REFERENCES:
- Use returned priority IDs with add_case, update_case, update_cases (priority_id parameter)
- Use returned priority IDs with get_tests (priority_id filter)
- Note: get_tests uses client-side filtering for priority_id""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_statuses",
            description="""Get all available test statuses for use with test results. Returns status IDs and names for filtering and result submission.

CROSS-REFERENCES:
- Use returned status IDs with get_tests (status_id filter)
- Use returned status IDs or names with add_result (status_id - required parameter)
- Supports both numeric IDs and human-readable names (e.g., '1', 'passed', 'failed')""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        # ==================== USERS ====================
        Tool(
            name="get_users",
            description="""Get all users in TestRail instance. Returns user IDs needed for filtering and assignment operations.

CROSS-REFERENCES:
- Use returned user IDs with get_tests (assignedto_id filter)
- Use returned user IDs with add_run, add_result (assignedto_id assignment)
- Use returned user IDs with add_plan_entry, update_plan_entry (assignedto_id assignment)
- Use returned user IDs with get_plans (created_by filter)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "is_active": {"type": "string", "description": "Filter by active status: true/false (optional). Omit to get all users."},
                    "project_id": {"type": "integer", "description": "✅ Filter users by project ID (API-supported)"},
                    "name": {"type": "string", "description": "🔧 Filter by name substring (client-side, case-insensitive)"},
                    "email": {"type": "string", "description": "🔧 Filter by email substring (client-side, case-insensitive)"}
                },
                "required": []
            }
        ),
        Tool(
            name="get_user",
            description="Get specific user by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID (numeric identifier)"}
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="get_user_by_email",
            description="Lookup user by email address",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Email address of the user to lookup"}
                },
                "required": ["email"]
            }
        ),
        
        # ==================== MILESTONES ====================
        Tool(
            name="get_milestones",
            description="""Get milestones for a project. Returns milestone IDs for release management, run/plan association, and filtering.

CROSS-REFERENCES:
- Use returned milestone IDs with add_run, update_run (milestone_id parameter)
- Use returned milestone IDs with add_plan, update_plan (milestone_id parameter)
- Use returned milestone IDs with get_plans (milestone_id filter)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "is_completed": {"type": "string", "description": "✅ Filter by completion status: true/false (API-supported)"},
                    "is_started": {"type": "string", "description": "✅ Filter by started status: true/false (API-supported)"},
                    "name": {"type": "string", "description": "🔧 Filter by milestone name substring (client-side, case-insensitive)"},
                    "limit": {"type": "integer", "description": "Maximum number of milestones to return (optional)"},
                    "offset": {"type": "integer", "description": "Number of milestones to skip for pagination (optional)"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_milestone",
            description="Get details of a specific milestone",
            inputSchema={
                "type": "object",
                "properties": {
                    "milestone_id": {"type": "string", "description": "Milestone ID"}
                },
                "required": ["milestone_id"]
            }
        ),
        Tool(
            name="add_milestone",
            description="Create a new milestone for release management and timeline tracking",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "name": {"type": "string", "description": "Milestone name"},
                    "description": {"type": "string", "description": "Milestone description (optional)"},
                    "due_on": {"type": "string", "description": "Due date as Unix timestamp (optional)"},
                    "start_on": {"type": "string", "description": "Start date as Unix timestamp (optional)"},
                    "parent_id": {"type": "string", "description": "Parent milestone ID for hierarchical milestones (optional)"}
                },
                "required": ["project_id", "name"]
            }
        ),
        Tool(
            name="update_milestone",
            description="Update an existing milestone",
            inputSchema={
                "type": "object",
                "properties": {
                    "milestone_id": {"type": "string", "description": "Milestone ID"},
                    "name": {"type": "string", "description": "New milestone name (optional)"},
                    "description": {"type": "string", "description": "New description (optional)"},
                    "due_on": {"type": "string", "description": "Due date as Unix timestamp (optional)"},
                    "start_on": {"type": "string", "description": "Start date as Unix timestamp (optional)"},
                    "parent_id": {"type": "string", "description": "Parent milestone ID (optional)"},
                    "is_completed": {"type": "string", "description": "Mark as completed: true/false (optional)"},
                    "is_started": {"type": "string", "description": "Mark as started: true/false (optional)"}
                },
                "required": ["milestone_id"]
            }
        ),
        Tool(
            name="delete_milestone",
            description="Delete a milestone",
            inputSchema={
                "type": "object",
                "properties": {
                    "milestone_id": {"type": "string", "description": "Milestone ID"}
                },
                "required": ["milestone_id"]
            }
        ),
        
        # ==================== CONFIGURATIONS ====================
        Tool(
            name="get_configs",
            description="Get all configuration groups for a project. Configurations are used for multi-platform testing (e.g., Browser, OS, Device) in matrix testing scenarios.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="add_config_group",
            description="Create a new configuration group for organizing test configurations (e.g., 'Browsers', 'Operating Systems', 'Devices')",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "name": {"type": "string", "description": "Configuration group name"}
                },
                "required": ["project_id", "name"]
            }
        ),
        Tool(
            name="add_config",
            description="Add a configuration to a group (e.g., add 'Chrome' to 'Browsers' group)",
            inputSchema={
                "type": "object",
                "properties": {
                    "config_group_id": {"type": "string", "description": "Configuration group ID"},
                    "name": {"type": "string", "description": "Configuration name"}
                },
                "required": ["config_group_id", "name"]
            }
        ),
        
        # ==================== ATTACHMENTS ====================
        Tool(
            name="upload_attachment",
            description="""Upload a file (screenshot, document, etc.) to a TestRail entity.

WHEN TO USE:
- Attaching screenshots or evidence to test cases or results
- Uploading documents to runs or plans

ENTITY TYPES: case, result, run, plan

EMBEDDING IMAGES IN CASES (2-step process):
1. Upload the image with this tool (entity_type: case)
2. Update the case field with an HTML img tag: <img src="index.php?/attachments/get/{attachment_id}" />

SECURITY: Only allowed file extensions (.png, .jpg, .pdf, .doc, etc.). Sensitive paths are blocked.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {"type": "string", "description": "Entity type: case, result, run, or plan", "enum": ["case", "result", "run", "plan"]},
                    "entity_id": {"type": "string", "description": "Entity ID to attach to"},
                    "file_path": {"type": "string", "description": "Absolute path to the file to upload"},
                    "filename": {"type": "string", "description": "Override filename (optional, defaults to basename of file_path)"}
                },
                "required": ["entity_type", "entity_id", "file_path"]
            }
        ),
        Tool(
            name="list_attachments",
            description="""List attachments for a TestRail entity.

ENTITY TYPES: case, run, plan, test (not result)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {"type": "string", "description": "Entity type: case, run, plan, or test", "enum": ["case", "run", "plan", "test"]},
                    "entity_id": {"type": "string", "description": "Entity ID"}
                },
                "required": ["entity_type", "entity_id"]
            }
        ),
        Tool(
            name="get_attachment",
            description="Get details of a specific attachment by ID (numeric or alphanumeric UUID on TestRail 7.1+)",
            inputSchema={
                "type": "object",
                "properties": {
                    "attachment_id": {"type": "string", "description": "Attachment ID (numeric or alphanumeric UUID)"}
                },
                "required": ["attachment_id"]
            }
        ),
        Tool(
            name="delete_attachment",
            description="Delete an attachment by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "attachment_id": {"type": "string", "description": "Attachment ID (numeric or alphanumeric UUID)"}
                },
                "required": ["attachment_id"]
            }
        ),

        # ==================== SHARED STEPS ====================
        Tool(
            name="get_shared_steps",
            description="""Get shared steps (reusable test step sets) for a project. Requires TestRail 7.0+.

CROSS-REFERENCES:
- Use returned shared step IDs with get_shared_step / update_shared_step / delete_shared_step
- case_ids on each set lists the test cases that reference it""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "created_after": {"type": "string", "description": "✅ Only shared steps created after this date (Unix timestamp or ISO 8601) (API-supported)"},
                    "created_before": {"type": "string", "description": "✅ Only shared steps created before this date (Unix timestamp or ISO 8601) (API-supported)"},
                    "created_by": {"type": "string", "description": "✅ Comma-separated list of creator user IDs (API-supported)"},
                    "updated_after": {"type": "string", "description": "✅ Only shared steps updated after this date (Unix timestamp or ISO 8601) (API-supported)"},
                    "updated_before": {"type": "string", "description": "✅ Only shared steps updated before this date (Unix timestamp or ISO 8601) (API-supported)"},
                    "refs": {"type": "string", "description": "✅ Filter by a single reference ID, e.g. TR-a, 4291 (API-supported)"},
                    "limit": {"type": "integer", "description": "Maximum number of shared steps to return (default 250)"},
                    "offset": {"type": "integer", "description": "Number of shared steps to skip for pagination (optional)"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_shared_step",
            description="Get details of a specific set of shared steps, including its steps and the case_ids that reference it. Requires TestRail 7.0+.",
            inputSchema={
                "type": "object",
                "properties": {
                    "shared_step_id": {"type": "string", "description": "Shared step ID"}
                },
                "required": ["shared_step_id"]
            }
        ),
        Tool(
            name="get_shared_step_history",
            description="Get the change history of a set of shared steps. Requires TestRail 7.3+.",
            inputSchema={
                "type": "object",
                "properties": {
                    "shared_step_id": {"type": "string", "description": "Shared step ID"}
                },
                "required": ["shared_step_id"]
            }
        ),
        Tool(
            name="add_shared_step",
            description="""Create a new set of shared steps for a project. Requires TestRail 7.0+ and permission to add test cases.

Step fields use HTML (not Markdown). Each step object supports: content, additional_info, expected, refs.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "title": {"type": "string", "description": "Title for the set of steps"},
                    "custom_steps_separated": {
                        "type": "array",
                        "description": "Array of step objects. Each object may contain content/additional_info/expected/refs.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string", "description": "The 'Step' field (HTML)"},
                                "additional_info": {"type": "string", "description": "The 'Additional Info' field (HTML)"},
                                "expected": {"type": "string", "description": "The 'Expected Result' field (HTML)"},
                                "refs": {"type": "string", "description": "Reference information for the 'References' field"}
                            }
                        }
                    }
                },
                "required": ["project_id", "title"]
            }
        ),
        Tool(
            name="update_shared_step",
            description="""Update an existing set of shared steps. Requires TestRail 7.0+ and permission to edit test cases.

IMPORTANT: submitting custom_steps_separated REPLACES all existing steps. GET the shared step first, modify the full array, then send the complete list back.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "shared_step_id": {"type": "string", "description": "Shared step ID"},
                    "title": {"type": "string", "description": "New title for the set of steps (optional)"},
                    "custom_steps_separated": {
                        "type": "array",
                        "description": "Complete array of step objects — REPLACES all existing steps.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string", "description": "The 'Step' field (HTML)"},
                                "additional_info": {"type": "string", "description": "The 'Additional Info' field (HTML)"},
                                "expected": {"type": "string", "description": "The 'Expected Result' field (HTML)"},
                                "refs": {"type": "string", "description": "Reference information for the 'References' field"}
                            }
                        }
                    }
                },
                "required": ["shared_step_id"]
            }
        ),
        Tool(
            name="delete_shared_step",
            description="""Delete a set of shared steps. Requires TestRail 7.0+ and permission to delete test cases. CANNOT be undone.

By default the steps are kept in the test cases that referenced them. Set keep_in_cases=false to also remove the steps from those cases.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "shared_step_id": {"type": "string", "description": "Shared step ID"},
                    "keep_in_cases": {"type": "string", "description": "Keep steps in referencing cases: true/false (default true). false also removes the steps from all referencing cases."}
                },
                "required": ["shared_step_id"]
            }
        ),

        # ==================== HEALTH CHECK ====================
        Tool(
            name="get_server_health",
            description="Get server health status including cache status, rate limiter stats, and connection readiness",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]
    return canonical_tools + get_alias_tool_defs()
