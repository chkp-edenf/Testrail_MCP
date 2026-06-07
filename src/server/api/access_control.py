"""Server-side access control for tool dispatch.

`configure_access()` reads env flags once at startup and stores them on
module-level state. `enforce_access()` runs before every tool dispatch in
`stdio.py:call_tool()` and raises `McpError` (-32603) when a call is
disallowed. The dispatcher must call `enforce_access()` BEFORE invoking
the handler so no work touches the TestRail HTTP client when blocked.

Env flags handled here:
- `TESTRAIL_READ_ONLY` (Phase 1) — when truthy, every tool name in
  `WRITE_TOOL_NAMES` is rejected.
- `TESTRAIL_ALLOWED_TOOLS` (Phase 2) — comma-separated allowlist;
  unset/empty means all tools allowed (current behavior).

Precedence: when both flags are set, `TESTRAIL_READ_ONLY=1` wins for
write tools (read-only message surfaces — the safest interpretation),
while `TESTRAIL_ALLOWED_TOOLS` wins for read tools not in the list.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Mapping

from mcp.shared.exceptions import McpError
from mcp.types import INVALID_REQUEST, METHOD_NOT_FOUND, ErrorData

logger = logging.getLogger(__name__)

# Tool names that mutate state. Sourced from `get_tool_handlers()` in
# src/server/api/__init__.py. A test asserts this set matches the
# verb-prefix-derived set so adding a new write tool without updating
# this constant fails CI.
WRITE_TOOL_NAMES: frozenset[str] = frozenset({
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


_TRUTHY_VALUES: frozenset[str] = frozenset({"1", "true", "yes", "on"})
_FALSY_VALUES: frozenset[str] = frozenset({"0", "false", "no", "off", ""})


# Module-level state mutated by configure_access().
_read_only: bool = False
_allowed_tools: frozenset[str] | None = None


def _parse_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in _TRUTHY_VALUES


def _parse_allowlist(value: str | None) -> frozenset[str] | None:
    """Parse a comma-separated tool-name list.

    Returns None for unset / empty / whitespace-only / separators-only
    inputs (semantically: "no allowlist configured, all tools allowed").
    Returns a frozenset of stripped, deduplicated names otherwise.
    """
    if value is None:
        return None
    parts = [token.strip() for token in value.split(",")]
    parts = [token for token in parts if token]
    if not parts:
        return None
    return frozenset(parts)


def _warn_unrecognized(env_var: str, raw_value: str) -> None:
    """Surface unrecognized boolean env values as a warning.

    Without this, `TESTRAIL_READ_ONLY=treu` silently disables the guard.
    """
    logger.warning(
        "[testrail-mcp] WARNING: unrecognized %s='%s', defaulting to OFF "
        "(expected one of: 1/true/yes/on, 0/false/no/off)",
        env_var,
        raw_value,
    )


def configure_access(env: Mapping[str, str] | None = None) -> None:
    """Resolve access-control flags from env and log the resolved mode.

    Call once from `main()` before registering the call_tool handler.
    """
    global _read_only, _allowed_tools
    src: Mapping[str, str] = env if env is not None else os.environ

    # TESTRAIL_READ_ONLY
    raw = src.get("TESTRAIL_READ_ONLY")
    _read_only = _parse_truthy(raw)
    if raw is not None:
        normalized = raw.strip().lower()
        if normalized not in _TRUTHY_VALUES and normalized not in _FALSY_VALUES:
            _warn_unrecognized("TESTRAIL_READ_ONLY", raw)
    logger.info(
        "[testrail-mcp] read-only mode: %s",
        "ON" if _read_only else "OFF",
    )

    # TESTRAIL_ALLOWED_TOOLS
    raw_allowlist = src.get("TESTRAIL_ALLOWED_TOOLS")
    _allowed_tools = _parse_allowlist(raw_allowlist)
    if _allowed_tools is None:
        if raw_allowlist is not None and raw_allowlist.strip():
            # The var is set to a non-blank value that nonetheless parses to
            # zero tool names (e.g. ",,," or "  ,  "). A naive operator
            # might assume "set to 'nothing' = deny everything", so make the
            # actual fail-open behavior explicit.
            logger.warning(
                "[testrail-mcp] WARNING: TESTRAIL_ALLOWED_TOOLS=%r parses to "
                "an empty allowlist; defaulting to ALL TOOLS ALLOWED. To "
                "block writes, use TESTRAIL_READ_ONLY=1.",
                raw_allowlist,
            )
        logger.info("[testrail-mcp] allowed tools: all")
    else:
        # Lazy import to avoid loading every resource handler at module-import
        # time (keeps unit tests for this module fast and side-effect free).
        from src.server.api import get_tool_handlers  # noqa: PLC0415

        known = set(get_tool_handlers().keys())
        unknown = _allowed_tools - known
        if unknown:
            logger.warning(
                "[testrail-mcp] WARNING: TESTRAIL_ALLOWED_TOOLS contains "
                "unknown tools (will be ignored at dispatch time): %s",
                ", ".join(sorted(unknown)),
            )
        logger.info(
            "[testrail-mcp] allowed tools: %d listed (%s)",
            len(_allowed_tools),
            ", ".join(sorted(_allowed_tools)),
        )


def is_read_only() -> bool:
    return _read_only


def enforce_access(tool_name: str) -> None:
    """Raise McpError if dispatch of `tool_name` is disallowed.

    Order matters: the read-only check runs first so a write tool that
    happens to be in the allowlist still gets the read-only message
    (safer to surface "read-only mode" than "tool allowed" when both
    flags conflict).

    Error codes follow JSON-RPC 2.0 semantics so programmatic consumers
    (e.g. an AaaS scheduler) can distinguish a policy denial from an
    unknown method or a server bug:

    - Read-only denial -> `INVALID_REQUEST` (-32600). The request is
      well-formed and the tool exists, but the server's current policy
      forbids it. A retry with the same body will keep failing; a retry
      with a read tool may succeed.
    - Allowlist denial -> `METHOD_NOT_FOUND` (-32601). From the caller's
      perspective the tool is not available. Use the same code regular
      MCP servers use for unknown methods so generic agent code that
      already handles -32601 (e.g. "discover available tools and try
      another") works without special-casing this server.

    No-op when access is allowed.
    """
    if _read_only and tool_name in WRITE_TOOL_NAMES:
        raise McpError(ErrorData(
            code=INVALID_REQUEST,
            message=(
                f"TestRail MCP is in read-only mode (TESTRAIL_READ_ONLY=1). "
                f"Tool '{tool_name}' is blocked."
            ),
        ))
    if _allowed_tools is not None and tool_name not in _allowed_tools:
        raise McpError(ErrorData(
            code=METHOD_NOT_FOUND,
            message=(
                f"Tool '{tool_name}' not in TESTRAIL_ALLOWED_TOOLS allowlist."
            ),
        ))
