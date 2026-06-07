"""Tests for the TESTRAIL_READ_ONLY env flag.

Phase 1 of v2.0: server-side write block. Verifies that enforce_access()
raises McpError(INVALID_REQUEST, -32600) for every write tool when
read-only mode is on, and is a no-op for read tools or when the flag
is off. v2.0.1 hardening swapped INTERNAL_ERROR -> INVALID_REQUEST so
JSON-RPC consumers can distinguish policy denial from a server bug.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_REQUEST

import src.server.api.access_control as ac

_AC_LOGGER = "src.server.api.access_control"

# Sample of read tools used to assert they are never blocked.
READ_TOOL_SAMPLES: tuple[str, ...] = (
    "get_projects",
    "get_cases",
    "get_runs",
    "get_results",
    "get_server_health",
)


@pytest.fixture(autouse=True)
def _reset_access_control(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(ac, "_read_only", False)
    yield


# ---------------------------------------------------------------------------
# WRITE_TOOL_NAMES coverage
# ---------------------------------------------------------------------------

EXPECTED_WRITE_TOOLS: frozenset[str] = frozenset({
    "add_suite", "update_suite", "delete_suite",
    "add_section", "update_section", "delete_section", "move_section",
    "add_case", "update_case", "delete_case",
    "copy_cases_to_section", "move_cases_to_section",
    "update_cases", "delete_cases",
    "add_run", "update_run", "close_run", "delete_run",
    "add_plan", "update_plan", "close_plan", "delete_plan",
    "add_plan_entry", "update_plan_entry", "delete_plan_entry",
    "add_result", "add_results", "add_result_for_case", "add_results_for_cases",
    "add_milestone", "update_milestone", "delete_milestone",
    "add_config_group", "add_config",
    "upload_attachment", "delete_attachment",
    "add_shared_step", "update_shared_step", "delete_shared_step",
})


def test_write_tool_set_matches_dispatcher_registry() -> None:
    """WRITE_TOOL_NAMES must stay in sync with the dispatcher's write tools.

    If a future PR adds a new write tool to get_tool_handlers() without
    listing it here, this test fails — preventing silent gating gaps.
    """
    from src.server.api import get_tool_handlers  # noqa: PLC0415

    registered = set(get_tool_handlers().keys())
    write_prefixes = ("add_", "update_", "delete_", "move_", "copy_", "close_", "upload_")
    inferred_writes = {
        name for name in registered
        if name.startswith(write_prefixes)
    }
    assert ac.WRITE_TOOL_NAMES == EXPECTED_WRITE_TOOLS == inferred_writes


# ---------------------------------------------------------------------------
# enforce_access — read-only ON blocks every write tool
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tool", sorted(EXPECTED_WRITE_TOOLS))
def test_enforce_access_blocks_write_tool_when_read_only(
    tool: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ac, "_read_only", True)

    with pytest.raises(McpError) as exc_info:
        ac.enforce_access(tool)

    err = exc_info.value
    assert err.error.code == INVALID_REQUEST  # -32600 — well-formed request, policy denied
    assert "read-only mode" in err.error.message
    assert "TESTRAIL_READ_ONLY=1" in err.error.message
    assert f"Tool '{tool}'" in err.error.message
    assert "is blocked" in err.error.message


# ---------------------------------------------------------------------------
# enforce_access — read-only OFF is a no-op for every tool
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tool", sorted(EXPECTED_WRITE_TOOLS))
def test_enforce_access_allows_write_tool_when_read_only_off(
    tool: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ac, "_read_only", False)
    ac.enforce_access(tool)  # must not raise


@pytest.mark.parametrize("tool", READ_TOOL_SAMPLES)
def test_enforce_access_never_blocks_read_tool(
    tool: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    for flag in (True, False):
        monkeypatch.setattr(ac, "_read_only", flag)
        ac.enforce_access(tool)  # must not raise


# ---------------------------------------------------------------------------
# configure_access — env parsing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "value,expected",
    [
        ("1", True),
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("yes", True),
        ("YES", True),
        ("on", True),
        ("On", True),
        ("  1  ", True),  # whitespace tolerant
        ("0", False),
        ("false", False),
        ("no", False),
        ("off", False),
        ("maybe", False),  # bogus -> OFF (safe-fallback to current behavior)
        ("", False),
    ],
)
def test_configure_access_parses_truthy_values(
    value: str, expected: bool, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=_AC_LOGGER):
        ac.configure_access({"TESTRAIL_READ_ONLY": value})
    assert ac.is_read_only() is expected
    expected_token = "ON" if expected else "OFF"
    assert f"[testrail-mcp] read-only mode: {expected_token}" in caplog.text


def test_configure_access_unset_defaults_to_off(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=_AC_LOGGER):
        ac.configure_access({})
    assert ac.is_read_only() is False
    assert "[testrail-mcp] read-only mode: OFF" in caplog.text


def test_configure_access_reads_from_real_environ_when_no_arg(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("TESTRAIL_READ_ONLY", "true")
    with caplog.at_level(logging.INFO, logger=_AC_LOGGER):
        ac.configure_access()
    assert ac.is_read_only() is True
    assert "[testrail-mcp] read-only mode: ON" in caplog.text


@pytest.mark.parametrize("bogus", ["maybe", "treu", "enabled", "yep", "TBD"])
def test_configure_access_warns_on_unrecognized_value(
    bogus: str, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=_AC_LOGGER):
        ac.configure_access({"TESTRAIL_READ_ONLY": bogus})
    assert ac.is_read_only() is False
    assert "WARNING: unrecognized TESTRAIL_READ_ONLY" in caplog.text
    assert f"'{bogus}'" in caplog.text
    assert "[testrail-mcp] read-only mode: OFF" in caplog.text


@pytest.mark.parametrize("recognized", ["1", "true", "yes", "on", "0", "false", "no", "off", ""])
def test_configure_access_no_warning_on_recognized_value(
    recognized: str, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=_AC_LOGGER):
        ac.configure_access({"TESTRAIL_READ_ONLY": recognized})
    assert "WARNING: unrecognized" not in caplog.text
