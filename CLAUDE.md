# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TestRail MCP Server v2.1.0 - A Model Context Protocol server that connects AI assistants to TestRail instances. The dispatcher exposes **75 flat MCP tools** (one per TestRail v2 endpoint), with the bun913-fork camelCase aliases resolved transparently at the dispatcher entry.

**Key Capabilities:**
- 75 flat MCP tools spanning every TestRail v2 endpoint
- Server-side gates: `TESTRAIL_READ_ONLY` write-block, `TESTRAIL_ALLOWED_TOOLS` allowlist
- bun913-compat aliases (gated by `TESTRAIL_LEGACY_ALIASES`, default on)
- Optional startup cache warm-up (`TESTRAIL_PRELOAD_CACHE`)
- Attachment support - upload screenshots and files to cases, results, runs, plans
- 100% portable - works with any TestRail instance (no hardcoded custom fields)
- Smart field handling - automatic conversion between human-readable names and numeric IDs
- Auto rate-limited - 180 req/min with token bucket algorithm
- Four independent in-memory caches (24h TTL) for metadata
- Installed via `uvx` (no Docker required)
- Two-package layout: `testrail-core` (importable library) + `testrail-mcp` (this MCP wrapper). See ADR-003.

## Development Commands

### Running (via uvx from local source)
```bash
# Configure in .mcp.json (or your AI client's MCP config):
{
  "mcpServers": {
    "testrail": {
      "command": "uvx",
      "args": ["--from", "/path/to/local/repo", "testrail-mcp"],
      "env": {
        "TESTRAIL_URL": "https://your-instance.testrail.io",
        "TESTRAIL_USERNAME": "your-email@company.com",
        "TESTRAIL_API_KEY": "your-api-key"
      }
    }
  }
}

# After code changes, clear uvx cache:
uv cache clean testrail-mcp --force
# Then restart the MCP connection in your AI client
```

## Architecture

**Two-package uv workspace** (ADR-003):

1. **`testrail-core`** (`packages/testrail-core/src/testrail_core/`) — protocol-agnostic integration library
   - `client/base_client.py` - HTTP client with auth, rate limiting, retry logic
   - `client/__init__.py` - `TestRailClient` aggregator + `ClientConfig` + exception hierarchy
   - `client/exceptions.py` - typed error hierarchy
   - `api/<resource>.py` - per-resource clients (cases, runs, plans, results, attachments, …)
   - `schemas/<resource>.py` - Pydantic validation models
   - `cache/{field,status,priority,case_type}_cache.py` - four metadata caches (24h TTL, in-memory)
   - `rate_limiter.py` - token bucket (180 req/min)

2. **`testrail-mcp`** (top-level `src/`) — thin MCP wrapper
   - `src/stdio.py` - Entry point, MCP server initialization, env validation
   - `src/server/api/tools.py` - 75 flat tool definitions
   - `src/server/api/__init__.py` - Tool handler registry / dispatcher
   - `src/server/api/access_control.py` - `TESTRAIL_READ_ONLY` + `TESTRAIL_ALLOWED_TOOLS` gates
   - `src/server/api/aliases.py` - bun913 28-alias compat layer
   - `src/server/api/cache_preload.py` - `TESTRAIL_PRELOAD_CACHE` startup warm-up
   - `src/server/api/<resource>.py` - per-resource handlers adapting MCP calls to `testrail-core`
   - `src/server/api/health.py` - server health monitoring (reads cache status, metrics)
   - `src/server/api/metrics.py` - request/cache metrics tracking

The legacy `src/client/` and `src/shared/` paths still exist as thin re-export shims so any external consumer pinned to those import paths keeps working through the v2 transition.

**Entry Point Flow (stdio):**
```
stdio.py → validates env vars → normalizes TestRail URL →
creates TestRailClient with rate_limiter → registers tools →
routes tool calls to handlers
```


## Critical Implementation Patterns

### Cache Warming
**IMPORTANT:** Always populate caches before operations requiring field lookups:

```python
# Cache population sequence
1. get_case_fields     # Populates field_cache, priority_cache, case_type_cache
2. get_statuses        # Populates status_cache
```

The four independent caches:
- **Field Cache** - Custom field name→ID mappings and required fields
- **Status Cache** - Test status name→ID mappings (Passed, Failed, etc.)
- **Priority Cache** - Priority name→ID mappings (Critical, High, Medium, Low)
- **Case Type Cache** - Case type name→ID mappings (Functional, Automated, etc.)

Cache TTL: 24 hours in-memory, cleared on container restart.

### Custom Field Handling
The server automatically converts human-readable field names to TestRail IDs:

```python
# User provides: {"test_phase": "Regression", "platforms": "Win,Mac"}
# Server converts to: {"custom_test_phase": 123, "custom_platforms": "Win,Mac"}
```

This portability design means NO hardcoded custom field IDs.

### Rate Limiting
Token bucket algorithm enforces 180 req/min:
- Auto-applied to all API requests
- No configuration needed
- Prevents TestRail API quota exhaustion

### URL Normalization
TestRail uses non-standard URL format:
```
https://instance.testrail.io/index.php?/api/v2/endpoint&param1=val1&param2=val2
```

The server normalizes URLs automatically in `stdio.py` and `base_client.py`.

## Tool Organization

**75 flat MCP tools** — one per TestRail operation. Tool names are snake_case (`get_cases`, `add_case`, `update_run`, `upload_attachment`). The bun913 alias layer (`TESTRAIL_LEGACY_ALIASES=1`, default) accepts the camelCase variants from the bun913 fork.

| Resource | Tools |
|---|---|
| Projects | `get_projects`, `get_project` |
| Suites | `get_suites`, `get_suite`, `add_suite`, `update_suite`, `delete_suite` |
| Sections | `get_sections`, `get_section`, `add_section`, `update_section`, `move_section`, `delete_section` |
| Cases | `get_cases`, `get_case`, `get_cases_by_ids`, `get_case_history`, `add_case`, `update_case`, `update_cases`, `delete_case`, `delete_cases`, `copy_cases_to_section`, `move_cases_to_section` |
| Tests | `get_tests`, `get_test` |
| Runs | `get_runs`, `get_run`, `add_run`, `update_run`, `close_run`, `delete_run` |
| Plans | `get_plans`, `get_plan`, `add_plan`, `update_plan`, `close_plan`, `delete_plan`, `add_plan_entry`, `update_plan_entry`, `delete_plan_entry` |
| Results | `get_results`, `get_results_for_case`, `get_results_for_run`, `add_result`, `add_results`, `add_result_for_case`, `add_results_for_cases` |
| Milestones | `get_milestones`, `get_milestone`, `add_milestone`, `update_milestone`, `delete_milestone` |
| Users | `get_users`, `get_user`, `get_user_by_email` |
| Configs | `get_configs`, `add_config_group`, `add_config` |
| Metadata | `get_case_fields`, `get_case_types`, `get_priorities`, `get_statuses`, `get_templates` |
| Attachments | `list_attachments`, `get_attachment`, `upload_attachment`, `delete_attachment` |
| Shared Steps | `get_shared_steps`, `get_shared_step`, `get_shared_step_history`, `add_shared_step`, `update_shared_step`, `delete_shared_step` |
| Health | `get_server_health` |

**Dispatcher path** (every tool call):
1. Alias resolution (`aliases.py`) — camelCase → snake_case if `TESTRAIL_LEGACY_ALIASES=1`
2. Allowlist gate (`access_control.py`) — reject if `TESTRAIL_ALLOWED_TOOLS` is set and the tool isn't in it
3. Read-only gate (`access_control.py`) — reject all 39 write tools if `TESTRAIL_READ_ONLY` is truthy
4. Handler dispatch (`server/api/__init__.py`) — route to per-resource handler

## Environment Variables

**Required:**
- `TESTRAIL_URL` - TestRail instance URL (e.g., https://company.testrail.io)
- `TESTRAIL_USERNAME` - Login email
- `TESTRAIL_API_KEY` - API key from TestRail My Settings

**Optional — server-side gates:**
- `TESTRAIL_READ_ONLY` (default `0`) - When truthy (`1`/`true`/`yes`/`on`), the dispatcher blocks every write tool (the canonical 39-tool write set) and returns an error to the AI client. Read tools unaffected.
- `TESTRAIL_ALLOWED_TOOLS` (default *unset* = all) - Comma-separated allowlist. When set, any tool not listed is rejected at the dispatcher. Combine with `TESTRAIL_READ_ONLY` to narrow further.
- `TESTRAIL_LEGACY_ALIASES` (default `1` = on) - Resolve the 28 bun913 camelCase aliases to canonical snake_case names. Set to `0` once your client has migrated.
- `TESTRAIL_PRELOAD_CACHE` (default `0`) - When truthy, eagerly fetches `case_fields`, `statuses`, `priorities`, `case_types` at startup. Failures are non-fatal.

**Validation:** `validate_environment()` in `stdio.py` checks required vars at startup. Optional gates are resolved at module import (idempotent) and logged via stderr.

## Error Handling

Custom exception hierarchy in `testrail_core.client.exceptions` (re-exported via `testrail_core.client` and the legacy shim `src.client.api`):
- `TestRailError` - Base exception
- `TestRailAPIError` - API errors (400-599)
- `TestRailAuthenticationError` - 401
- `TestRailPermissionError` - 403
- `TestRailNotFoundError` - 404
- `TestRailRateLimitError` - 429
- `TestRailServerError` - 500+
- `TestRailTimeoutError` - Request timeout
- `TestRailNetworkError` - Network issues

Retry logic (v1.4.0): Automatic retry with exponential backoff for GET requests on transient failures.

## Filtering and Pagination

Most GET tools support comprehensive filtering:
- **API-supported filters:** priority_id, type_id, milestone_id, created_by, is_completed, etc.
- **Date filters:** created_after, created_before (Unix timestamp or ISO 8601)
- **Pagination:** limit/offset for result sets

Example: `get_cases` with filters:
```json
{
  "project_id": "1",
  "suite_id": "5872",
  "priority_id": [1, 2],
  "created_after": "2024-01-01T00:00:00Z",
  "limit": 100,
  "offset": 0
}
```

## Common Development Tasks

### Adding a New Tool (existing resource)
1. Add a `Tool(...)` definition to `src/server/api/tools.py`
2. Add the handler in `src/server/api/<resource>.py`
3. Register the handler in `src/server/api/__init__.py`
4. If new TestRail endpoint: add the client method in `packages/testrail-core/src/testrail_core/api/<resource>.py`
5. If new request shape: add Pydantic schema in `packages/testrail-core/src/testrail_core/schemas/<resource>.py`
6. If write tool: add to `_WRITE_TOOL_NAMES` in `src/server/api/access_control.py`

### Adding a New Tool (new resource)
1. Client: `packages/testrail-core/src/testrail_core/api/<resource>.py`
2. Schemas: `packages/testrail-core/src/testrail_core/schemas/<resource>.py`
3. Register the new resource client on `TestRailClient` in `packages/testrail-core/src/testrail_core/client/__init__.py`
4. Server handler + dispatcher: `src/server/api/<resource>.py`
5. Tool definitions: `src/server/api/tools.py`
6. Wire dispatcher into `src/server/api/__init__.py`

### Debugging
1. Verify cache population: call `get_server_health`
2. Warm caches: call `get_case_fields` then `get_statuses` (or set `TESTRAIL_PRELOAD_CACHE=1`)
3. Clear caches: restart the MCP server connection
4. Clear uvx cache after code changes: `uv cache clean testrail-mcp --force`

## Key Files Reference

**MCP wrapper (`src/`):**
- `src/stdio.py` - Entry point (stdio mode)
- `src/server/api/tools.py` - 75 flat tool definitions
- `src/server/api/__init__.py` - Dispatcher (alias resolve → allowlist → read-only → handler)
- `src/server/api/access_control.py` - Read-only + allowlist gates
- `src/server/api/aliases.py` - 28 bun913 camelCase aliases
- `src/server/api/cache_preload.py` - Startup cache warm-up
- `src/server/api/health.py` - `get_server_health` handler
- `src/server/api/metrics.py` - Request/cache metrics

**Integration core (`packages/testrail-core/`):**
- `src/testrail_core/client/__init__.py` - `TestRailClient` aggregator + `ClientConfig`
- `src/testrail_core/client/base_client.py` - HTTP client with auth, rate limiting, retry, file upload
- `src/testrail_core/client/exceptions.py` - Typed error hierarchy
- `src/testrail_core/api/<resource>.py` - Per-resource clients (attachments, cases, runs, …)
- `src/testrail_core/schemas/<resource>.py` - Pydantic models
- `src/testrail_core/cache/{field,status,priority,case_type}_cache.py` - Four metadata caches
- `src/testrail_core/rate_limiter.py` - Token bucket (180 req/min)

**Configuration:**
- `pyproject.toml` - Package metadata and dependencies (mcp, httpx, pydantic)
- `mcp_config_example.json` - MCP client configuration template
- `.env.example` - Environment variable template

**Documentation:**
- `README.md` - Project overview and quick start
- `USER_GUIDE.md` - Complete setup and usage guide
- `CLAUDE.md` - AI assistant guidance

## Important Notes

- **Cache warming is critical** - Always populate caches before field-dependent operations (use `testrail_metadata` actions: case_fields, statuses)
- **Rate limiter** - Global 180 req/min per container
- **Custom fields are dynamic** - Never hardcode field IDs, always use cache lookups
- **All test resources should use `[AUTOTEST]` prefix** for easy cleanup

## Rich Text & Attachments

### HTML, Not Markdown
All TestRail rich text fields (preconditions, steps, expected results, comments) use **HTML**. Markdown syntax like `**bold**` or `![](url)` renders as plain text.

```html
<!-- CORRECT -->
<p>Step description with <b>bold</b> text</p>
<br />
<img src="index.php?/attachments/get/1000003243" />

<!-- WRONG — rendered as plain text -->
**bold text**
![](index.php?/attachments/get/1000003243)
```

### Embedding Images in Cases (2-Step Process)
1. **Upload** the image via `testrail_attachments` (action: upload, entity_type: case)
2. **Update** the case field with an HTML `<img>` tag:
   ```html
   <img src="index.php?/attachments/get/{attachment_id}" />
   ```

### Updating Steps (custom_steps_separated)
When updating `custom_steps_separated`, you **MUST send ALL steps** in the array. Omitted steps are deleted. Always:
1. GET the case first to read current steps
2. Modify only the target step(s)
3. Send the complete array back in the update

### Attachment IDs
Attachment IDs may be **numeric** (pre-7.1) or **alphanumeric UUIDs** (TestRail 7.1+). Always treat as strings, never cast to int.
