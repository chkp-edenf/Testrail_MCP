# TestRail MCP Server

**Connect AI assistants to your TestRail instance via the Model Context Protocol**

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)]()
[![MCP Protocol](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)]()

> Talk to your AI assistant about test cases, and watch it create, update, and manage them in TestRail — all through natural conversation.

---

## Highlights

- **74 flat MCP tools** covering every TestRail v2 endpoint (cases, runs, plans, results, attachments, …)
- **Server-side gates** — `TESTRAIL_READ_ONLY` write-block, `TESTRAIL_ALLOWED_TOOLS` allowlist
- **bun913-compat aliases** — drop-in replacement for the bun913 fork (gated by `TESTRAIL_LEGACY_ALIASES`, default on)
- **Attachment support** — upload screenshots and files to cases, results, runs, plans
- **100% portable** — works with ANY TestRail instance (no hardcoded custom fields)
- **Smart field handling** — say "Regression" instead of memorizing numeric IDs
- **Auto rate-limited** — built-in throttling (180 req/min) protects your API quota
- **Optional cache warm-up** — `TESTRAIL_PRELOAD_CACHE=1` pre-fetches metadata at startup
- **Zero setup friction** — one `uvx` command, no Docker required

---

## Quick Install (Wizard)

One-liner installers that detect your AI client, prompt for your TestRail credentials, optionally validate them, and write the MCP config for you — backing up any existing config first. Non-interactive mode available via flags.

**macOS / Linux**
```sh
curl -LsSf https://raw.githubusercontent.com/chkp-edenf/HarmonySASE_Testrail_MCP/main/install.sh | sh
```

**Windows (PowerShell)**
```powershell
irm https://raw.githubusercontent.com/chkp-edenf/HarmonySASE_Testrail_MCP/main/install.ps1 | iex
```

The wizard walks you through picking Claude Code / Claude Desktop / both, entering the TestRail URL + login + API key, and writes the config.

> **Prefer manual config?** The step-by-step Quick Start below still works — the wizard is optional.

---

## Quick Start

### 1. Get Your TestRail API Key

1. Log in to TestRail → click your avatar → **My Settings**
2. Scroll to **API Keys** → click **Add Key**
3. Copy the key (you won't see it again)

### 2. Configure Your AI Client

Add this to your MCP client configuration:

```json
{
  "mcpServers": {
    "testrail": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/chkp-edenf/HarmonySASE_Testrail_MCP.git", "testrail-mcp"],
      "env": {
        "TESTRAIL_URL": "https://your-instance.testrail.io",
        "TESTRAIL_USERNAME": "your-email@company.com",
        "TESTRAIL_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Replace** the three env values with your TestRail credentials.

| AI Client | Config File Location |
|-----------|---------------------|
| **Claude Code** | `.mcp.json` in your project root, or `~/.claude/mcp.json` globally |
| **Claude Desktop** | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) |
| **VS Code (Copilot)** | `~/.vscode/mcp.json` or workspace `.vscode/mcp.json` |
| **Cursor** | Cursor Settings → MCP Servers |

### 3. Test It

Ask your AI:
```
"Get all TestRail projects"
```

If you see your projects list, you're ready.

### 4. Warm the Cache (Important)

Before creating or updating test cases, run these to populate metadata caches:

```
"Get case fields from TestRail"
"Get statuses from TestRail"
```

This enables natural language field values (e.g., "High" instead of priority ID 2).

---

## Available Tools

The dispatcher exposes **74 flat tools** — one per TestRail operation — grouped below by resource. Tool names are snake_case (e.g. `get_cases`, `add_case`, `update_run`, `upload_attachment`). The bun913 compatibility layer (`TESTRAIL_LEGACY_ALIASES=1`, default on) accepts the camelCase aliases used by the bun913 fork (`getCases`, `addCase`, …) and resolves them to the canonical names.

| Resource | Read | Write |
|---|---|---|
| Projects | `get_projects`, `get_project` | — |
| Suites | `get_suites`, `get_suite` | `add_suite`, `update_suite`, `delete_suite` |
| Sections | `get_sections`, `get_section` | `add_section`, `update_section`, `move_section`, `delete_section` |
| Cases | `get_cases`, `get_case`, `get_cases_by_ids`, `get_case_history` | `add_case`, `update_case`, `update_cases`, `delete_case`, `delete_cases`, `copy_cases_to_section`, `move_cases_to_section` |
| Tests | `get_tests`, `get_test` | — |
| Runs | `get_runs`, `get_run` | `add_run`, `update_run`, `close_run`, `delete_run` |
| Plans | `get_plans`, `get_plan` | `add_plan`, `update_plan`, `close_plan`, `delete_plan`, `add_plan_entry`, `update_plan_entry`, `delete_plan_entry` |
| Results | `get_results`, `get_results_for_case`, `get_results_for_run` | `add_result`, `add_results`, `add_result_for_case`, `add_results_for_cases` |
| Milestones | `get_milestones`, `get_milestone` | `add_milestone`, `update_milestone`, `delete_milestone` |
| Users | `get_users`, `get_user`, `get_user_by_email` | — |
| Configs | `get_configs` | `add_config_group`, `add_config` |
| Metadata | `get_case_fields`, `get_case_types`, `get_priorities`, `get_statuses`, `get_templates` | — |
| Attachments | `list_attachments`, `get_attachment` | `upload_attachment`, `delete_attachment` |
| Shared Steps | `get_shared_steps`, `get_shared_step`, `get_shared_step_history` | `add_shared_step`, `update_shared_step`, `delete_shared_step` |
| Health | `get_server_health` | — |

---

## Usage Examples

### Creating Test Cases

```
You: "Create 5 test cases in section 'API Tests' for the User Registration endpoint"
AI: Creates 5 cases with auto-generated titles — done in seconds.
```

### Smart Custom Fields

```
You: "Create a test case with priority High, type Regression, platform Mac"
AI: Automatically converts names to IDs using the cached metadata.
```

### Bulk Operations

```
You: "Update all test cases in suite 3 to priority Critical"
AI: Fetches cases, then bulk-updates in one API call.
```

### Uploading Screenshots to Test Cases

```
You: "Upload this screenshot to test case 12345 and add it to the expected result"
AI: 1. Uploads via testrail_attachments
    2. Updates the step's expected result with an HTML <img> tag
```

**Important:** TestRail rich text fields use HTML. To embed uploaded images, use:
```html
<img src="index.php?/attachments/get/{attachment_id}" />
```

### Analyzing Results

```
You: "Show me all failed tests from test run 142"
AI: Queries results, formats as a readable table.
```

---

## Architecture

```
┌─────────────────┐
│   AI Assistant   │  (Claude Code, Claude Desktop, VS Code, Cursor)
└────────┬─────────┘
         │ MCP Protocol (stdio JSON-RPC)
┌────────▼─────────┐
│   MCP Server     │  (This project — runs via uvx)
│   74 flat tools  │
└────────┬─────────┘
         │ HTTPS + Basic Auth
┌────────▼─────────┐
│  TestRail API v2 │  (Your TestRail instance)
└──────────────────┘
```

**Two-package layout** (uv workspace; ADR-003):
- **`testrail-core`** (`packages/testrail-core/`) — protocol-agnostic integration library: HTTP client, retry, rate-limit, four metadata caches, Pydantic schemas, exceptions, attachment handling. Importable directly by any Python consumer.
- **`testrail-mcp`** (this top-level package) — thin MCP wrapper: stdio entry point, 74-tool dispatcher, server-side gates (read-only, allowlist, aliases, preload), per-resource handlers that adapt MCP tool calls to `testrail-core`.

**Four independent caches** (24h TTL, in-memory):
- Field Cache — custom field name→ID mappings
- Status Cache — test status name→ID mappings
- Priority Cache — priority name→ID mappings
- Case Type Cache — case type name→ID mappings

---

## Security

- **No hardcoded credentials** — environment variables only
- **No persistent storage** — caches are in-memory, cleared on restart
- **Rate limiting** — 180 req/min prevents API quota exhaustion
- **Input validation** — Pydantic schemas validate all inputs
- **Attachment security** — blocked sensitive paths (.ssh, .env, credentials), allowed file types only
- **Never commit credentials** — use `.env` files or MCP client env config

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `TESTRAIL_URL` | Your TestRail instance URL (e.g., `https://your-instance.testrail.io`) |
| `TESTRAIL_USERNAME` | Your TestRail login email |
| `TESTRAIL_API_KEY` | API key from TestRail My Settings |

### Optional — server-side gates

| Variable | Default | Description |
|----------|---------|-------------|
| `TESTRAIL_READ_ONLY` | `0` | When truthy (`1`, `true`, `yes`, `on`), every write tool is blocked at the dispatcher and returns an error to the AI client. Read tools are unaffected. Use to embed the server in environments that must not mutate TestRail data. |
| `TESTRAIL_ALLOWED_TOOLS` | *(unset = all)* | Comma-separated allowlist of tool names. When set, any tool not in the list is rejected at the dispatcher. Combine with `TESTRAIL_READ_ONLY=1` to further narrow read access. |
| `TESTRAIL_LEGACY_ALIASES` | `1` | When on, accepts the 28 camelCase tool names from the bun913 fork (`getCases`, `addCase`, …) and resolves them to canonical snake_case names. Set to `0` once your client has migrated. |
| `TESTRAIL_PRELOAD_CACHE` | `0` | When truthy, eagerly fetches `case_fields`, `statuses`, `priorities`, and `case_types` at startup so the first tool call doesn't pay the cold-cache penalty. Failures during preload are non-fatal. |

### bun913 migration

If you're migrating from the bun913 fork, leave `TESTRAIL_LEGACY_ALIASES` at its default (`1`) — your existing camelCase tool names continue to work. Once your client is fully migrated to canonical snake_case names, set it to `0` to disable the alias resolver and reject the legacy names.

---

## Install Matrix

Pick whichever form fits your workflow. All four launch the same server.

| Source | Command | Pinning |
|---|---|---|
| **PyPI (latest)** | `uvx testrail-mcp` | tracks the newest published v2.x |
| **PyPI (pinned)** | `uvx testrail-mcp==2.0.0` | exact version |
| **Git (release tag)** | `uvx --from git+https://github.com/chkp-edenf/HarmonySASE_Testrail_MCP@v2.0.0 testrail-mcp` | exact tag, no PyPI required |
| **Git (pinned SHA)** | `uvx --from git+https://github.com/chkp-edenf/HarmonySASE_Testrail_MCP@<sha> testrail-mcp` | exact commit, audit-friendly |
| **Local source** | `uvx --from /path/to/local/repo testrail-mcp` | live dev |

Embedding `testrail-core` directly (no MCP):

```python
# uv pip install testrail-core
from testrail_core.client import TestRailClient, ClientConfig
from testrail_core.rate_limiter import rate_limiter

config = ClientConfig(
    base_url="https://your-instance.testrail.io",
    username="your-email@company.com",
    api_key="your-api-key",
)
client = TestRailClient(config, rate_limiter=rate_limiter)
projects = await client.projects.get_projects()
```

> The PyPI install paths require v2.0.0 to be tagged and the publish workflow to run. Until then, use the `git+` forms above.

---

## Development (Running from Source)

For local development, point uvx to the local repo:

```json
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
```

**After code changes:** clear the uvx cache and restart the MCP server:
```bash
uv cache clean testrail-mcp --force
```

---

## Troubleshooting

### "Connection Error" or server fails to start
1. Verify your TestRail URL, username, and API key are correct
2. Ensure your TestRail instance is reachable from your machine
3. Check that `uvx` is installed: `uvx --version`

### "Missing required fields" when creating test cases
Run `testrail_metadata` (action: `case_fields`) to populate the cache first.

### Custom field values not recognized
1. Run `testrail_metadata` (action: `case_fields`) to see valid values
2. Check spelling — the system converts to lowercase for matching
3. Use numeric IDs as fallback

### Changes to MCP server code not taking effect
The uvx cache needs clearing:
```bash
uv cache clean testrail-mcp --force
```
Then restart the MCP connection in your AI client.

---

## Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** — Complete setup and usage guide
- **[CLAUDE.md](CLAUDE.md)** — AI assistant guidance for this codebase

---

## Acknowledgments

- Built on the [Model Context Protocol](https://modelcontextprotocol.io) by Anthropic
- Integrates with [TestRail REST API v2](https://www.gurock.com/testrail/docs/api)

---

**Ready to supercharge your TestRail workflow?** → [Get Started](#quick-start)
