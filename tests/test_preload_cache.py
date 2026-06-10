"""Tests for the TESTRAIL_PRELOAD_CACHE startup warm-up.

Phase 4 of v2.0: opt-in startup warm-up of the four metadata caches
(case_fields, case_types, priorities, statuses). Verifies that the
preload calls each fetcher exactly once when enabled, that subsequent
metadata tool calls hit the cache (no additional HTTP), and that a
failure in one fetcher does not crash the server or block the others.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest

import src.server.api.cache_preload as cp
import src.server.api.case_type_cache as case_type_cache
import src.server.api.field_cache as field_cache
import src.server.api.priority_cache as priority_cache
import src.server.api.status_cache as status_cache

_CP_LOGGER = "src.server.api.cache_preload"


# ---------------------------------------------------------------------------
# Fixtures — mocked client + cache reset
# ---------------------------------------------------------------------------

_FAKE_CASE_FIELDS = [
    {
        "system_name": "custom_test_phase",
        "is_required": True,
        "configs": [{"options": {"items": "1, Smoke\n2, Regression"}}],
    },
    {
        "system_name": "custom_platforms",
        "is_required": False,
        "configs": [{"options": {"items": "1, Win\n2, Mac\n3, Linux"}}],
    },
]
_FAKE_CASE_TYPES = [{"id": 1, "name": "Functional"}, {"id": 2, "name": "Automated"}]
_FAKE_PRIORITIES = [
    {"id": 1, "name": "Low", "short_name": "Low"},
    {"id": 4, "name": "Critical", "short_name": "Crit"},
]
_FAKE_STATUSES = [
    {"id": 1, "name": "passed", "label": "Passed"},
    {"id": 5, "name": "failed", "label": "Failed"},
]


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock TestRailClient with the four metadata fetchers stubbed."""
    client = MagicMock()
    client.case_fields = MagicMock()
    client.case_fields.get_case_fields = AsyncMock(return_value=_FAKE_CASE_FIELDS)
    client.case_fields.get_case_types = AsyncMock(return_value=_FAKE_CASE_TYPES)
    client.case_fields.get_priorities = AsyncMock(return_value=_FAKE_PRIORITIES)
    client.statuses = MagicMock()
    client.statuses.get_statuses = AsyncMock(return_value=_FAKE_STATUSES)
    return client


@pytest.fixture(autouse=True)
def _reset_caches(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Reset every cache + module state between tests."""
    field_cache.invalidate_cache()
    monkeypatch.setattr(cp, "_enabled", False)
    # case_type / priority / status caches don't expose invalidate(); reset
    # them by mutating their module-level dicts directly.
    case_type_cache._case_type_cache.update({  # noqa: SLF001
        "case_types": [], "name_to_id": {}, "id_to_name": {}, "last_updated": None,
    })
    priority_cache._priority_cache.update({  # noqa: SLF001
        "priorities": [], "name_to_id": {}, "id_to_name": {}, "last_updated": None,
    })
    status_cache._status_cache.update({  # noqa: SLF001
        "statuses": [], "name_to_id": {}, "id_to_name": {}, "last_updated": None,
    })
    yield


# ---------------------------------------------------------------------------
# configure_preload — env parsing
# ---------------------------------------------------------------------------

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
        ("", False),
        ("maybe", False),
    ],
)
def test_configure_preload_parses_truthy(value: str, expected: bool) -> None:
    cp.configure_preload({"TESTRAIL_PRELOAD_CACHE": value})
    assert cp.is_enabled() is expected


def test_configure_preload_unset_defaults_to_off() -> None:
    cp.configure_preload({})
    assert cp.is_enabled() is False


# ---------------------------------------------------------------------------
# preload_caches — happy path
# ---------------------------------------------------------------------------

def test_preload_calls_each_fetcher_once_when_enabled(
    mock_client: MagicMock, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cp, "_enabled", True)
    asyncio.run(cp.preload_caches(mock_client))

    mock_client.case_fields.get_case_fields.assert_called_once()
    mock_client.case_fields.get_case_types.assert_called_once()
    mock_client.case_fields.get_priorities.assert_called_once()
    mock_client.statuses.get_statuses.assert_called_once()


def test_preload_skips_when_disabled(
    mock_client: MagicMock, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cp, "_enabled", False)
    asyncio.run(cp.preload_caches(mock_client))

    mock_client.case_fields.get_case_fields.assert_not_called()
    mock_client.case_fields.get_case_types.assert_not_called()
    mock_client.case_fields.get_priorities.assert_not_called()
    mock_client.statuses.get_statuses.assert_not_called()


def test_preload_populates_each_cache(
    mock_client: MagicMock, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cp, "_enabled", True)
    asyncio.run(cp.preload_caches(mock_client))

    assert field_cache.is_cache_valid()
    assert case_type_cache.is_cache_valid()
    assert priority_cache.is_cache_valid()
    assert status_cache.is_cache_valid()


def test_preload_logs_summary_with_counts(
    mock_client: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(cp, "_enabled", True)
    with caplog.at_level(logging.INFO, logger=_CP_LOGGER):
        asyncio.run(cp.preload_caches(mock_client))
    text = caplog.text
    assert "[testrail-mcp] preloaded caches:" in text
    assert "case_fields(2)" in text
    assert "case_types(2)" in text
    assert "priorities(2)" in text
    assert "statuses(2)" in text


# ---------------------------------------------------------------------------
# Cache hit on subsequent metadata calls (zero additional HTTP)
# ---------------------------------------------------------------------------

def test_subsequent_metadata_calls_hit_preloaded_cache(
    mock_client: MagicMock, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After preload, calling ensure_metadata_caches must not refetch."""
    monkeypatch.setattr(cp, "_enabled", True)
    asyncio.run(cp.preload_caches(mock_client))

    # Reset call counts to baseline for the assertion
    mock_client.case_fields.get_priorities.reset_mock()
    mock_client.case_fields.get_case_types.reset_mock()

    # Lazy import to mirror the runtime load order (ensure_metadata_caches
    # is exposed by the cases module).
    from src.server.api.cases import ensure_metadata_caches  # noqa: PLC0415

    asyncio.run(ensure_metadata_caches(mock_client))

    mock_client.case_fields.get_priorities.assert_not_called()
    mock_client.case_fields.get_case_types.assert_not_called()


# ---------------------------------------------------------------------------
# Failure handling — one fetcher raises, others still run, server still starts
# ---------------------------------------------------------------------------

def test_preload_continues_when_one_fetcher_raises(
    mock_client: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(cp, "_enabled", True)
    mock_client.case_fields.get_priorities = AsyncMock(
        side_effect=RuntimeError("simulated network error"),
    )

    with caplog.at_level(logging.WARNING, logger=_CP_LOGGER):
        # Must NOT raise — server start cannot fail because of preload.
        asyncio.run(cp.preload_caches(mock_client))

    # Other fetchers still ran.
    mock_client.case_fields.get_case_fields.assert_called_once()
    mock_client.case_fields.get_case_types.assert_called_once()
    mock_client.statuses.get_statuses.assert_called_once()

    # Warning surfaces the failure for ops visibility.
    assert "preload failed for priorities" in caplog.text
    assert "RuntimeError" in caplog.text or "simulated network error" in caplog.text


def test_preload_marks_failed_cache_with_zero_count(
    mock_client: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(cp, "_enabled", True)
    mock_client.statuses.get_statuses = AsyncMock(
        side_effect=ConnectionError("offline"),
    )

    with caplog.at_level(logging.INFO, logger=_CP_LOGGER):
        asyncio.run(cp.preload_caches(mock_client))

    # Summary should report 0 for the failed cache, real counts for the rest.
    assert "statuses(0)" in caplog.text
    assert "case_fields(2)" in caplog.text
    assert "case_types(2)" in caplog.text
    assert "priorities(2)" in caplog.text


# ---------------------------------------------------------------------------
# Auth/permission errors log at ERROR — operators must not confuse a
# bad-credentials failure with "no data yet". spektr HIGH from v2 review.
# ---------------------------------------------------------------------------

def test_preload_logs_auth_error_at_error_level_for_case_fields(
    mock_client: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from testrail_core.client.exceptions import TestRailAuthenticationError

    monkeypatch.setattr(cp, "_enabled", True)
    mock_client.case_fields.get_case_fields = AsyncMock(
        side_effect=TestRailAuthenticationError("401 Unauthorized"),
    )

    with caplog.at_level(logging.WARNING, logger=_CP_LOGGER):
        asyncio.run(cp.preload_caches(mock_client))

    # Find the auth-failure record — must be ERROR, not WARNING.
    auth_records = [
        r for r in caplog.records
        if r.name == _CP_LOGGER and "case_fields" in r.getMessage()
        and "auth/permission" in r.getMessage()
    ]
    assert len(auth_records) == 1
    assert auth_records[0].levelno == logging.ERROR
    assert "TESTRAIL_USERNAME" in auth_records[0].getMessage()


def test_preload_logs_permission_error_at_error_level_for_subsequent_fetcher(
    mock_client: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from testrail_core.client.exceptions import TestRailPermissionError

    monkeypatch.setattr(cp, "_enabled", True)
    mock_client.statuses.get_statuses = AsyncMock(
        side_effect=TestRailPermissionError("403 Forbidden"),
    )

    with caplog.at_level(logging.WARNING, logger=_CP_LOGGER):
        asyncio.run(cp.preload_caches(mock_client))

    perm_records = [
        r for r in caplog.records
        if r.name == _CP_LOGGER and "statuses" in r.getMessage()
        and "auth/permission" in r.getMessage()
    ]
    assert len(perm_records) == 1
    assert perm_records[0].levelno == logging.ERROR


def test_preload_logs_non_auth_failure_at_warning_level(
    mock_client: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Regression guard — only auth/permission failures escalate to ERROR.

    Network glitches, timeouts, and other transient errors stay at
    WARNING because lazy retry on first tool call may recover.
    """
    monkeypatch.setattr(cp, "_enabled", True)
    mock_client.case_fields.get_priorities = AsyncMock(
        side_effect=ConnectionError("transient network glitch"),
    )

    with caplog.at_level(logging.WARNING, logger=_CP_LOGGER):
        asyncio.run(cp.preload_caches(mock_client))

    priorities_records = [
        r for r in caplog.records
        if r.name == _CP_LOGGER and "priorities" in r.getMessage()
        and r.levelno >= logging.WARNING
    ]
    assert len(priorities_records) == 1
    assert priorities_records[0].levelno == logging.WARNING
    assert "auth/permission" not in priorities_records[0].getMessage()
