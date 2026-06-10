"""Optional startup warm-up of metadata caches.

Gated by `TESTRAIL_PRELOAD_CACHE`. When truthy, `preload_caches(client)`
runs once at server startup to populate the four metadata caches
(case_fields, case_types, priorities, statuses) so the first agent
call doesn't pay for a 4-round-trip cache-warming dance.

Failures are non-fatal: a single fetcher raising does not crash the
server or block the others. Each failure logs a WARNING for ops
visibility; the summary line at the end reports `<cache>(0)` for any
cache whose preload failed.

Templates are excluded from preload because (a) templates are
per-project and the MCP isn't pinned to a single project at boot,
and (b) the existing template fetcher does not back any module-level
cache the way the four metadata caches do.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from testrail_core.client.exceptions import (
    TestRailAuthenticationError,
    TestRailPermissionError,
)

from . import case_type_cache, field_cache, priority_cache, status_cache

logger = logging.getLogger(__name__)


# Errors that mean the server will never recover by lazy retry. Surfacing
# them at ERROR level (vs WARNING) prevents an operator from misreading
# the "case_fields(0) statuses(0)" summary as "no data yet" when the
# real cause is bad credentials or revoked API access.
_FATAL_PRELOAD_ERRORS: tuple[type[BaseException], ...] = (
    TestRailAuthenticationError,
    TestRailPermissionError,
)


_TRUTHY_VALUES: frozenset[str] = frozenset({"1", "true", "yes", "on"})


# Module-level state mutated by configure_preload().
_enabled: bool = False


def is_enabled() -> bool:
    return _enabled


def configure_preload(env: Mapping[str, str] | None = None) -> None:
    """Resolve `TESTRAIL_PRELOAD_CACHE` from env.

    No-op (and silent) at log level until `preload_caches()` actually
    runs — that's where the summary line surfaces.
    """
    global _enabled
    src: Mapping[str, str] = env if env is not None else os.environ
    raw = src.get("TESTRAIL_PRELOAD_CACHE")
    _enabled = raw is not None and raw.strip().lower() in _TRUTHY_VALUES


def _build_field_map(
    fields: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, int | str]], list[str]]:
    """Parse case-field definitions into the shape `field_cache` expects.

    Mirrors the inline parser in `src/server/api/cases.py:_get_field_mapping`.
    Kept here so preload doesn't have to import the cases module (which
    pulls every resource handler). Phase 5's `testrail-core` extraction
    is the right place to dedupe.
    """
    field_map: dict[str, dict[str, int | str]] = {}
    required: list[str] = []
    for field in fields:
        system_name = field.get("system_name", "")
        if field.get("is_required"):
            required.append(system_name)

        configs = field.get("configs", [])
        if not configs:
            continue
        items_str = configs[0].get("options", {}).get("items", "")
        if not items_str:
            continue
        mapping: dict[str, int | str] = {}
        for line in items_str.split("\n"):
            if "," not in line:
                continue
            parts = line.split(",", 1)
            if len(parts) != 2:
                continue
            try:
                id_val = int(parts[0].strip())
            except ValueError:
                continue
            name = parts[1].strip().lower()
            mapping[name] = id_val
            mapping[str(id_val)] = id_val
        if mapping:
            field_map[system_name] = mapping
    return field_map, required


async def _preload_one(
    label: str,
    fetch: Callable[[], Awaitable[list[Any]]],
    update: Callable[[list[Any]], None],
    counts: dict[str, int],
) -> None:
    """Run a single preload step.

    Auth / permission errors log at ERROR level so operators don't read
    a `<cache>(0)` summary as "no data yet" when credentials are wrong.
    Other failures log at WARNING and the cache populates lazily on
    first tool use.
    """
    try:
        result = await fetch()
        update(result)
        counts[label] = len(result)
    except _FATAL_PRELOAD_ERRORS as exc:
        counts[label] = 0
        logger.error(
            "[testrail-mcp] preload auth/permission failure for %s: %s: %s — "
            "lazy retry will not recover; check TESTRAIL_USERNAME / TESTRAIL_API_KEY",
            label,
            type(exc).__name__,
            exc,
        )
    except Exception as exc:
        counts[label] = 0
        logger.warning(
            "[testrail-mcp] preload failed for %s: %s: %s",
            label,
            type(exc).__name__,
            exc,
        )


async def preload_caches(client: Any) -> None:
    """Pre-fetch metadata into the four module-level caches.

    No-op when `TESTRAIL_PRELOAD_CACHE` is off. Always returns cleanly:
    even if every fetcher raises, the server can still start and the
    caches will populate lazily on first tool use.
    """
    if not _enabled:
        return

    counts: dict[str, int] = {}

    # case_fields requires a parse pass before update_cache.
    try:
        fields = await client.case_fields.get_case_fields()
        field_map, required = _build_field_map(fields)
        field_cache.update_cache(field_map, required)
        counts["case_fields"] = len(fields)
    except _FATAL_PRELOAD_ERRORS as exc:
        counts["case_fields"] = 0
        logger.error(
            "[testrail-mcp] preload auth/permission failure for case_fields: %s: %s — "
            "lazy retry will not recover; check TESTRAIL_USERNAME / TESTRAIL_API_KEY",
            type(exc).__name__,
            exc,
        )
    except Exception as exc:
        counts["case_fields"] = 0
        logger.warning(
            "[testrail-mcp] preload failed for case_fields: %s: %s",
            type(exc).__name__,
            exc,
        )

    await _preload_one(
        "case_types",
        client.case_fields.get_case_types,
        case_type_cache.update_cache,
        counts,
    )
    await _preload_one(
        "priorities",
        client.case_fields.get_priorities,
        priority_cache.update_cache,
        counts,
    )
    await _preload_one(
        "statuses",
        client.statuses.get_statuses,
        status_cache.update_cache,
        counts,
    )

    logger.info(
        "[testrail-mcp] preloaded caches: case_fields(%d) case_types(%d) "
        "priorities(%d) statuses(%d)",
        counts.get("case_fields", 0),
        counts.get("case_types", 0),
        counts.get("priorities", 0),
        counts.get("statuses", 0),
    )
