"""Tests for bun913 compatibility aliases (TESTRAIL_LEGACY_ALIASES).

Phase 3 of v2.0. Verifies:
- Explicit alias map contains all 28 bun913 entries.
- Each alias resolves to a tool name registered with the dispatcher.
- Generic camelCase->snake_case fallback covers tools not in the
  explicit map.
- Argument keys are translated camelCase->snake_case before dispatch.
- TESTRAIL_LEGACY_ALIASES=0 disables both the explicit map and the
  generic fallback.
- Read-only and allowlist gates check the CANONICAL name, not the
  alias — so blocking add_case also blocks an addCase alias call.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from mcp.shared.exceptions import McpError

import src.server.api.access_control as ac
import src.server.api.aliases as al

_AL_LOGGER = "src.server.api.aliases"


@pytest.fixture(autouse=True)
def _reset_aliases(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(al, "_enabled", True)
    monkeypatch.setattr(ac, "_read_only", False)
    monkeypatch.setattr(ac, "_allowed_tools", None)
    yield


# ---------------------------------------------------------------------------
# BUN913_ALIASES — the explicit map
# ---------------------------------------------------------------------------

EXPECTED_ALIASES: dict[str, str] = {
    "getProjects": "get_projects",
    "getProject": "get_project",
    "getSuites": "get_suites",
    "getSuite": "get_suite",
    "getSections": "get_sections",
    "getSection": "get_section",
    "getCases": "get_cases",
    "getCase": "get_case",
    "getCasesByIds": "get_cases_by_ids",
    "getRuns": "get_runs",
    "getRun": "get_run",
    "getTests": "get_tests",
    "getTest": "get_test",
    "getResults": "get_results",
    "getResultsForCase": "get_results_for_case",
    "getResultsForRun": "get_results_for_run",
    "getCaseFields": "get_case_fields",
    "getCaseTypes": "get_case_types",
    "getPriorities": "get_priorities",
    "getStatuses": "get_statuses",
    "getTemplates": "get_templates",
    "getMilestones": "get_milestones",
    "getMilestone": "get_milestone",
    "getPlans": "get_plans",
    "getPlan": "get_plan",
    "getUsers": "get_users",
    "getUser": "get_user",
    "getUserByEmail": "get_user_by_email",
}


def test_bun913_aliases_has_28_entries() -> None:
    assert len(al.BUN913_ALIASES) == 28
    assert al.BUN913_ALIASES == EXPECTED_ALIASES


def test_every_alias_target_exists_in_dispatcher() -> None:
    """Each canonical name on the right side of the alias map must be a
    real tool the dispatcher can route to. Catches typos in the map."""
    from src.server.api import get_tool_handlers  # noqa: PLC0415

    registered = set(get_tool_handlers().keys())
    missing = set(al.BUN913_ALIASES.values()) - registered
    assert missing == set(), f"alias targets not in dispatcher: {missing}"


def test_no_alias_targets_a_write_tool() -> None:
    """Forward-compat guard (spektr v2 MEDIUM).

    The current 28-entry alias map only points at read tools. If a
    future PR adds an alias whose canonical target is in
    `WRITE_TOOL_NAMES`, this test fails — forcing the contributor to
    confirm the gating implications. The dispatcher already runs alias
    resolution BEFORE `enforce_access`, so a write-aliased call IS
    blocked under TESTRAIL_READ_ONLY=1; this test just makes the
    "we accept this" decision explicit at the alias-map definition.
    """
    write_aliases = {
        alias: canonical
        for alias, canonical in al.BUN913_ALIASES.items()
        if canonical in ac.WRITE_TOOL_NAMES
    }
    assert write_aliases == {}, (
        f"bun913 aliases that resolve to write tools — confirm gating "
        f"implications in plan-005 before landing: {write_aliases}"
    )


# ---------------------------------------------------------------------------
# camel_to_snake — generic translator
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "camel,snake",
    [
        ("caseId", "case_id"),
        ("projectId", "project_id"),
        ("suiteId", "suite_id"),
        ("sectionId", "section_id"),
        ("runId", "run_id"),
        ("testId", "test_id"),
        ("milestoneId", "milestone_id"),
        ("userId", "user_id"),
        ("planId", "plan_id"),
        ("caseIds", "case_ids"),
        ("getCasesByIds", "get_cases_by_ids"),
        ("addCase", "add_case"),
        ("getResultsForCase", "get_results_for_case"),
        ("bulkAddForCases", "bulk_add_for_cases"),
        ("getUserByEmail", "get_user_by_email"),
        # idempotent on already-snake_case
        ("already_snake", "already_snake"),
        ("get_projects", "get_projects"),
        # single word stays lowered
        ("foo", "foo"),
        # leading uppercase (PascalCase) — same as camelCase rules
        ("ProjectId", "project_id"),
    ],
)
def test_camel_to_snake(camel: str, snake: str) -> None:
    assert al.camel_to_snake(camel) == snake


# ---------------------------------------------------------------------------
# translate_args — dict-key conversion
# ---------------------------------------------------------------------------

def test_translate_args_converts_top_level_keys() -> None:
    args = {"caseId": 123, "projectId": 1, "suiteId": 5}
    assert al.translate_args(args) == {"case_id": 123, "project_id": 1, "suite_id": 5}


def test_translate_args_preserves_values_unchanged() -> None:
    args = {"caseIds": [1, 2, 3], "data": {"nestedKey": "stays"}}
    out = al.translate_args(args)
    assert out["case_ids"] == [1, 2, 3]
    # nested dict keys are NOT translated (bun913 inputs are flat)
    assert out["data"] == {"nestedKey": "stays"}


def test_translate_args_idempotent_on_snake_case() -> None:
    args = {"case_id": 1, "project_id": 2}
    assert al.translate_args(args) == args


def test_translate_args_empty() -> None:
    assert al.translate_args({}) == {}


# ---------------------------------------------------------------------------
# resolve — name + args together
# ---------------------------------------------------------------------------

def test_resolve_explicit_alias() -> None:
    name, args = al.resolve("getCase", {"caseId": 42})
    assert name == "get_case"
    assert args == {"case_id": 42}


def test_resolve_explicit_alias_with_array_arg() -> None:
    name, args = al.resolve("getCasesByIds", {"caseIds": [1, 2, 3]})
    assert name == "get_cases_by_ids"
    assert args == {"case_ids": [1, 2, 3]}


def test_resolve_already_canonical_passthrough() -> None:
    """A snake_case name with snake_case args should pass through unchanged."""
    name, args = al.resolve("get_case", {"case_id": 42})
    assert name == "get_case"
    assert args == {"case_id": 42}


def test_resolve_unknown_camelcase_falls_through_generic_translator() -> None:
    """Generic translator is the fallback for camelCase names not in the
    explicit map. Lets us forward-compat with new bun913 tools without
    updating BUN913_ALIASES first."""
    name, args = al.resolve("addCase", {"projectId": 1, "title": "x"})
    assert name == "add_case"
    assert args == {"project_id": 1, "title": "x"}


def test_resolve_when_disabled_returns_input_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(al, "_enabled", False)
    name, args = al.resolve("getCase", {"caseId": 42})
    assert name == "getCase"
    assert args == {"caseId": 42}


# ---------------------------------------------------------------------------
# configure_aliases — env parsing
# ---------------------------------------------------------------------------

def test_configure_aliases_default_enabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=_AL_LOGGER):
        al.configure_aliases({})
    assert al.is_enabled() is True
    assert "[testrail-mcp] legacy aliases: ON (28 aliases registered)" in caplog.text


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1", True),
        ("true", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("no", False),
        ("off", False),
    ],
)
def test_configure_aliases_parses_truthy(value: str, expected: bool) -> None:
    al.configure_aliases({"TESTRAIL_LEGACY_ALIASES": value})
    assert al.is_enabled() is expected


def test_configure_aliases_off_logs_off(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger=_AL_LOGGER):
        al.configure_aliases({"TESTRAIL_LEGACY_ALIASES": "0"})
    assert al.is_enabled() is False
    assert "[testrail-mcp] legacy aliases: OFF" in caplog.text


# ---------------------------------------------------------------------------
# Tool definitions — alias defs surface in tools.py when enabled
# ---------------------------------------------------------------------------

def test_get_alias_tool_defs_returns_28_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(al, "_enabled", True)
    defs = al.get_alias_tool_defs()
    assert len(defs) == 28
    names = {tool.name for tool in defs}
    assert names == set(EXPECTED_ALIASES.keys())


def test_get_alias_tool_defs_returns_empty_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(al, "_enabled", False)
    assert al.get_alias_tool_defs() == []


# ---------------------------------------------------------------------------
# Gate semantics — gates check the CANONICAL name, not the alias
# ---------------------------------------------------------------------------

def test_read_only_blocks_alias_for_write_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bun913 alias that maps to a write tool must be blocked when
    TESTRAIL_READ_ONLY=1. The current 28-entry map only contains read
    tools, so we synthesize an alias for this test by extending the
    fixture's resolution: invoking the canonical name through resolve()
    and then enforce_access against that canonical name is the real
    flow at the dispatcher entry. Verify resolve + enforce_access
    composes correctly for the read-only scenario."""
    monkeypatch.setattr(ac, "_read_only", True)
    # Synthesize: pretend an "addCase" call comes in. resolve() must yield
    # the canonical "add_case", and enforce_access must block it.
    canonical_name, _ = al.resolve("addCase", {"projectId": 1})
    assert canonical_name == "add_case"
    with pytest.raises(McpError) as exc_info:
        ac.enforce_access(canonical_name)
    assert "read-only mode" in exc_info.value.error.message
    assert "Tool 'add_case'" in exc_info.value.error.message


def test_allowlist_blocks_alias_when_canonical_not_listed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ac, "_allowed_tools", frozenset({"get_projects"}))
    canonical_name, _ = al.resolve("getCase", {"caseId": 1})
    assert canonical_name == "get_case"
    with pytest.raises(McpError) as exc_info:
        ac.enforce_access(canonical_name)
    assert "allowlist" in exc_info.value.error.message
    assert "Tool 'get_case'" in exc_info.value.error.message


def test_allowlist_allows_alias_when_canonical_listed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ac, "_allowed_tools", frozenset({"get_case"}))
    canonical_name, _ = al.resolve("getCase", {"caseId": 1})
    ac.enforce_access(canonical_name)  # must not raise


# ---------------------------------------------------------------------------
# get_alias_handlers is intentionally NOT defined — aliases are dispatched
# via the resolve() shim at the top of stdio.py:call_tool(), so the alias
# names share the underlying canonical handlers. (See ADR-003 / plan-004.)
# ---------------------------------------------------------------------------
