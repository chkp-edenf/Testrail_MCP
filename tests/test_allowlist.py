"""Tests for the TESTRAIL_ALLOWED_TOOLS env flag.

Phase 2 of v2.0: granular tool allowlist. Verifies that enforce_access()
blocks any tool not in the configured allowlist, that empty/unset means
all tools are allowed, and that the read-only flag still takes precedence
when both are set.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from mcp.shared.exceptions import McpError
from mcp.types import METHOD_NOT_FOUND

import src.server.api.access_control as ac

_AC_LOGGER = "src.server.api.access_control"


@pytest.fixture(autouse=True)
def _reset_access_control(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(ac, "_read_only", False)
    monkeypatch.setattr(ac, "_allowed_tools", None)
    yield


# ---------------------------------------------------------------------------
# _parse_allowlist
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, None),                                   # unset
        ("", None),                                     # empty string
        ("  ", None),                                   # whitespace only
        (",,", None),                                   # only separators
        ("get_projects", frozenset({"get_projects"})),
        ("get_projects,get_cases", frozenset({"get_projects", "get_cases"})),
        ("  get_projects , get_cases  ", frozenset({"get_projects", "get_cases"})),
        ("get_projects,,get_cases", frozenset({"get_projects", "get_cases"})),
        ("get_projects,get_projects", frozenset({"get_projects"})),  # dedup
    ],
)
def test_parse_allowlist(raw: str | None, expected: frozenset[str] | None) -> None:
    assert ac._parse_allowlist(raw) == expected


# ---------------------------------------------------------------------------
# configure_access — allowlist parsing + logging
# ---------------------------------------------------------------------------

def test_configure_access_unset_means_all_allowed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=_AC_LOGGER):
        ac.configure_access({})
    assert ac._allowed_tools is None
    assert "[testrail-mcp] allowed tools: all" in caplog.text


def test_configure_access_empty_means_all_allowed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=_AC_LOGGER):
        ac.configure_access({"TESTRAIL_ALLOWED_TOOLS": ""})
    assert ac._allowed_tools is None
    assert "[testrail-mcp] allowed tools: all" in caplog.text
    # Empty string is the canonical "I haven't set this" — no fail-open warning.
    assert "parses to an empty allowlist" not in caplog.text


@pytest.mark.parametrize("noisy_empty", [",,,", "  ,  ", ",", "  ,  ,  "])
def test_configure_access_warns_on_set_but_empty_allowlist(
    noisy_empty: str, caplog: pytest.LogCaptureFixture
) -> None:
    """Set-but-parses-empty surfaces a fail-open warning to defend against
    an operator misinterpreting ',,,' as 'deny everything'."""
    with caplog.at_level(logging.INFO, logger=_AC_LOGGER):
        ac.configure_access({"TESTRAIL_ALLOWED_TOOLS": noisy_empty})
    assert ac._allowed_tools is None
    assert "WARNING: TESTRAIL_ALLOWED_TOOLS" in caplog.text
    assert "parses to an empty allowlist" in caplog.text
    assert "ALL TOOLS ALLOWED" in caplog.text
    assert "TESTRAIL_READ_ONLY=1" in caplog.text


def test_configure_access_logs_listed_tools(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=_AC_LOGGER):
        ac.configure_access({"TESTRAIL_ALLOWED_TOOLS": "get_projects, get_cases"})
    assert ac._allowed_tools == frozenset({"get_projects", "get_cases"})
    assert "[testrail-mcp] allowed tools: 2 listed" in caplog.text
    assert "get_cases" in caplog.text
    assert "get_projects" in caplog.text


def test_configure_access_warns_on_unknown_tool_names(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=_AC_LOGGER):
        ac.configure_access(
            {"TESTRAIL_ALLOWED_TOOLS": "get_projects,not_a_real_tool,also_fake"}
        )
    assert "WARNING: TESTRAIL_ALLOWED_TOOLS contains unknown tools" in caplog.text
    assert "not_a_real_tool" in caplog.text
    assert "also_fake" in caplog.text
    # Known tool should NOT appear in the unknown-tools warning line.
    warning_lines = [
        rec.message for rec in caplog.records
        if rec.levelno == logging.WARNING
        and "unknown tools" in rec.message
    ]
    assert warning_lines, "expected one WARNING line about unknown tools"
    assert "get_projects" not in warning_lines[0]


def test_configure_access_no_warning_when_all_known(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=_AC_LOGGER):
        ac.configure_access({"TESTRAIL_ALLOWED_TOOLS": "get_projects,get_cases"})
    assert "unknown tools" not in caplog.text


# ---------------------------------------------------------------------------
# enforce_access — allowlist semantics
# ---------------------------------------------------------------------------

def test_enforce_access_allows_all_when_allowlist_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ac, "_allowed_tools", None)
    for tool in ("get_projects", "add_case", "delete_run", "anything_at_all"):
        ac.enforce_access(tool)  # must not raise


def test_enforce_access_blocks_tool_not_in_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ac, "_allowed_tools", frozenset({"get_projects", "get_cases"}))
    with pytest.raises(McpError) as exc_info:
        ac.enforce_access("get_runs")
    err = exc_info.value
    assert err.error.code == METHOD_NOT_FOUND  # -32601 — tool unavailable to caller
    assert "Tool 'get_runs'" in err.error.message
    assert "TESTRAIL_ALLOWED_TOOLS" in err.error.message
    assert "allowlist" in err.error.message


def test_enforce_access_allows_tool_in_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ac, "_allowed_tools", frozenset({"get_projects", "get_cases"}))
    ac.enforce_access("get_projects")  # must not raise
    ac.enforce_access("get_cases")  # must not raise


# ---------------------------------------------------------------------------
# Precedence — read-only wins over allowlist for write tools
# ---------------------------------------------------------------------------

def test_read_only_wins_for_write_tool_even_in_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When TESTRAIL_READ_ONLY=1, a write tool listed in TESTRAIL_ALLOWED_TOOLS
    must still be blocked. The read-only message wins (safest interpretation
    surfaces, not a confusing dual-block trace)."""
    monkeypatch.setattr(ac, "_read_only", True)
    monkeypatch.setattr(ac, "_allowed_tools", frozenset({"add_case", "get_cases"}))

    with pytest.raises(McpError) as exc_info:
        ac.enforce_access("add_case")
    err = exc_info.value
    assert "read-only mode" in err.error.message
    assert "allowlist" not in err.error.message  # read-only path, not allowlist path


def test_allowlist_blocks_read_tool_not_in_list_even_with_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When both flags set, a READ tool not in allowlist is blocked by the
    allowlist (read-only doesn't apply to read tools)."""
    monkeypatch.setattr(ac, "_read_only", True)
    monkeypatch.setattr(ac, "_allowed_tools", frozenset({"get_projects"}))

    with pytest.raises(McpError) as exc_info:
        ac.enforce_access("get_runs")
    err = exc_info.value
    assert "allowlist" in err.error.message
    assert "read-only" not in err.error.message


def test_allowlist_allows_listed_read_tool_with_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ac, "_read_only", True)
    monkeypatch.setattr(ac, "_allowed_tools", frozenset({"get_projects"}))
    ac.enforce_access("get_projects")  # must not raise


# ---------------------------------------------------------------------------
# Smoke: configure_access reads both env vars in one pass
# ---------------------------------------------------------------------------

def test_configure_access_handles_both_env_vars(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=_AC_LOGGER):
        ac.configure_access({
            "TESTRAIL_READ_ONLY": "1",
            "TESTRAIL_ALLOWED_TOOLS": "get_projects,get_cases",
        })
    assert ac.is_read_only() is True
    assert ac._allowed_tools == frozenset({"get_projects", "get_cases"})
    assert "[testrail-mcp] read-only mode: ON" in caplog.text
    assert "[testrail-mcp] allowed tools: 2 listed" in caplog.text
