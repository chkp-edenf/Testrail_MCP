# TestRail MCP Server - User Guide

**Version 2.2.0 - Setup and Usage Instructions**

## Table of Contents
- [What You'll Learn](#what-youll-learn)
- [Prerequisites](#prerequisites)
- [Step 1: Get Your TestRail API Key](#step-1-get-your-testrail-api-key)
- [Step 2: Configure Your AI Client](#step-2-configure-your-ai-client)
- [Step 3: Test the Connection](#step-3-test-the-connection)
- [Step 4: Populate the Cache](#step-4-populate-the-cache)
- [Read-Only Mode](#read-only-mode)
- [Restricting the Tool Surface](#restricting-the-tool-surface)
- [Common Workflows](#common-workflows)
- [Working with Attachments](#working-with-attachments)
- [Filtering and Pagination](#filtering-and-pagination)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## What You'll Learn

This guide walks you through:
1. Setting up the TestRail MCP Server
2. Configuring it with Claude Code, Claude Desktop, VS Code, or Cursor
3. Using the 75 flat MCP tools effectively
4. Read-only mode and tool-allowlist gating
5. Uploading attachments and embedding images
6. Troubleshooting common issues

**Time Required:** 5 minutes

---

## Prerequisites

Before you begin, make sure you have:

- **Python 3.11+** and **uv** installed
  - Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Verify: `uvx --version`

- **TestRail Account** with API access
  - You need login credentials to your TestRail instance
  - Example: `https://your-instance.testrail.io`

- **One of these AI clients:**
  - Claude Code (CLI or IDE extension)
  - Claude Desktop
  - VS Code with GitHub Copilot
  - Cursor
  - Any MCP-compatible client

---

## Step 1: Get Your TestRail API Key

1. **Log in to TestRail** (e.g., `https://your-instance.testrail.io`)

2. **Navigate to your profile:**
   - Click your avatar (top right)
   - Select **"My Settings"**

3. **Generate API Key:**
   - Scroll to **"API Keys"** section
   - Click **"Add Key"**
   - Give it a name (e.g., "MCP Server")
   - **Copy the key** — you won't be able to see it again

**Reference:** [TestRail API Documentation](https://support.gurock.com/hc/en-us/articles/7077039051284-Accessing-the-TestRail-API)

---

## Step 2: Configure Your AI Client

Choose your AI client below. All use the same MCP server configuration — only the config file location differs.

### MCP Server Configuration

```json
{
  "mcpServers": {
    "testrail": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/chkp-edenf/Testrail_MCP.git", "testrail-mcp"],
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

### Option A: Claude Code (Recommended)

**Per-project** (add to your project root):
```bash
# Create .mcp.json in your project directory
```
Paste the configuration above into `.mcp.json`.

**Global** (available in all projects):
```bash
# Create or edit ~/.claude/mcp.json
```

Claude Code auto-detects `.mcp.json` — no restart needed.

### Option B: Claude Desktop

1. Open the config file:
   ```bash
   # macOS
   open ~/Library/Application\ Support/Claude/claude_desktop_config.json

   # Windows
   notepad %APPDATA%\Claude\claude_desktop_config.json

   # Linux
   nano ~/.config/Claude/claude_desktop_config.json
   ```

2. Paste the configuration above.

3. **Restart Claude Desktop** completely (Quit and reopen).

### Option C: VS Code (GitHub Copilot)

1. Open the MCP config:
   ```bash
   # Global
   ~/.vscode/mcp.json

   # Or workspace-level
   .vscode/mcp.json
   ```

2. Paste the configuration above.

3. **Reload VS Code** (Cmd+Shift+P → "Developer: Reload Window").

### Option D: Cursor

1. Open **Cursor Settings** → **MCP Servers**
2. Add a new server with the configuration above.
3. Restart Cursor.

---

## Step 3: Test the Connection

Ask your AI:

```
"Get all TestRail projects"
```

### Expected Result

You should see a formatted list of your TestRail projects with IDs, names, and URLs.

### If It Fails

See [Troubleshooting](#troubleshooting) section below.

---

## Step 4: Populate the Cache

**This is critical** — run these to enable natural language field values:

### Initialize Field, Priority, and Case Type Caches

```
"Get case fields from TestRail"
```

This fetches all custom field definitions, maps human-readable values to IDs, and detects required fields. It also populates priority and case type caches.

### Initialize Status Cache

```
"Get statuses from TestRail"
```

This maps status names to IDs (e.g., "Passed" → ID 1, "Failed" → ID 5).

### Cache Behavior

- **TTL:** 24 hours in-memory
- **Cleared on:** Server restart (MCP reconnect)
- **Auto-warm:** Not automatic — you must call these after each server restart

**Now you're ready!** You can use natural language field names in all commands.

> **Tip:** Set `TESTRAIL_PRELOAD_CACHE=1` in your MCP env block to skip Step 4 — the server will warm all four caches at startup. Failures are non-fatal; the caches still populate lazily on first use if preload couldn't reach TestRail.

---

## Read-Only Mode

Set `TESTRAIL_READ_ONLY=1` in your MCP env block to embed the server in environments that must not mutate TestRail data — production AI assistants, demos, shared sessions, untrusted prompts.

**What it does:** every write tool (the canonical 39-tool write set: `add_*`, `update_*`, `delete_*`, `close_*`, `copy_*`, `move_*`, `upload_attachment`) is blocked at the dispatcher and returns an error to the AI client. Read tools are unaffected.

```json
{
  "mcpServers": {
    "testrail-readonly": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/chkp-edenf/Testrail_MCP.git", "testrail-mcp"],
      "env": {
        "TESTRAIL_URL": "https://your-instance.testrail.io",
        "TESTRAIL_USERNAME": "your-email@company.com",
        "TESTRAIL_API_KEY": "your-api-key",
        "TESTRAIL_READ_ONLY": "1"
      }
    }
  }
}
```

**Recognized truthy values:** `1`, `true`, `yes`, `on` (case-insensitive). Anything else (including unset, empty, `0`, `false`) leaves write tools enabled and logs a warning if the value was unrecognized — that's deliberate so a typo like `treu` cannot silently disable the gate.

---

## Restricting the Tool Surface

Set `TESTRAIL_ALLOWED_TOOLS` to a comma-separated list of tool names to make the dispatcher reject every tool that isn't on the list. Useful when you want to expose a narrow, well-understood subset to an AI client.

```json
"env": {
  "TESTRAIL_URL": "...",
  "TESTRAIL_USERNAME": "...",
  "TESTRAIL_API_KEY": "...",
  "TESTRAIL_ALLOWED_TOOLS": "get_projects,get_suites,get_sections,get_cases,get_case,get_runs,get_results_for_run"
}
```

**Combines with `TESTRAIL_READ_ONLY`:**
- `TESTRAIL_READ_ONLY=1` blocks every write tool, regardless of the allowlist.
- `TESTRAIL_ALLOWED_TOOLS=...` blocks every tool not on the list, regardless of read/write.
- Both together: the tool must pass *both* gates.

**Tool names** are the canonical snake_case names listed in [README.md → Available Tools](README.md#available-tools).

---

## Common Workflows

### Getting Started

**1. Explore Your Structure**
```
"List all TestRail projects"
"Show me suites in project 1"
"Get sections in suite 5"
```

### Creating Test Cases

**Simple case:**
```
"Create a test case in section 10 with title 'Login Test'"
```

**With custom fields (using natural language):**
```
"Create a test case:
- Section: 20
- Title: 'Check VPN connection on Mac'
- Platform: Mac
- Test Phase: Regression
- Priority: High"
```

The system automatically converts "Mac" → Platform ID, "Regression" → Test Phase ID, etc.

### Managing Test Runs

```
"Create test run in project 1 named 'Sprint 24 Regression'"
"Add result to test 101: status=passed, comment='All checks passed'"
"Close test run 50"
```

**Bulk results:**
```
"Add multiple results to run 50:
- Test 201: passed
- Test 202: failed with comment 'Timeout error'
- Test 203: blocked"
```

### Managing Test Plans

```
"Create a test plan in project 1 named 'Release 3.0 Testing'"
"Add plan entry to plan 50 for suite 10"
"Close test plan 42"
```

### Organizing Tests

```
"Move cases 401,402,403 to section 40"
"Copy cases from section 10 to section 50"
"Update multiple cases in section 60: set priority to High"
```

---

## Working with Attachments

### Uploading Files

Upload images, documents, or other files to TestRail entities:

```
"Upload /path/to/screenshot.png to test case 12345"
```

The AI calls `upload_attachment`, which returns an `attachment_id`.

**Supported file types:** images (.png, .jpg, .gif, .webp), documents (.pdf, .doc, .xlsx), text (.txt, .csv, .json, .xml), archives (.zip, .tar, .gz), video (.mp4, .mov).

**Blocked:** Sensitive paths (.ssh, .env, credentials, private keys).

### Embedding Images in Test Cases (2-Step Process)

TestRail rich text fields use **HTML, not markdown**. To embed an uploaded image:

1. **Upload the image:**
   ```
   "Upload screenshot.png to case 12345"
   ```
   Returns: `attachment_id: 1000003243`

2. **Update the case field with an HTML img tag:**
   ```html
   <img src="index.php?/attachments/get/1000003243" />
   ```

**Common mistake:** Using markdown `![](url)` — this renders as plain text in TestRail. Always use HTML `<img>` tags.

### Updating Steps with Images

When updating `custom_steps_separated` (test steps with separate expected results):

- You **MUST send ALL steps** in the array, not just the one you're changing.
- Omitted steps will be deleted.
- Always GET the case first, modify the target step, then send the full array back.

### Attachment IDs

Attachment IDs may be **numeric** (older TestRail) or **alphanumeric UUIDs** (TestRail 7.1+). Always treat them as strings.

---

## Filtering and Pagination

Most GET tools support comprehensive filtering.

### Filtering Test Cases

```
"Get all high-priority test cases in project 1"
"Show test cases created in the last 30 days"
"Get automated test cases in suite 5"
```

**Available filters:** `priority_id`, `type_id`, `milestone_id`, `section_id`, `template_id`, `created_by`, `created_after`, `created_before`, `updated_by`, `updated_after`, `updated_before`, `limit`, `offset`.

### Filtering Test Runs

```
"Get active test runs in project 1"
"Show completed runs for milestone 10"
```

**Available filters:** `suite_id`, `milestone_id`, `is_completed`, `created_by`, `created_after`, `created_before`, `limit`, `offset`.

### Filtering Results

```
"Get all failed results from run 50"
"Show results from the last 7 days"
```

**Available filters:** `status_id`, `created_by`, `created_after`, `created_before`, `defects_filter`, `limit`, `offset`.

### Filtering Tests in a Run

```
"Get untested tests assigned to user 5 in run 7420"
"Show high priority tests in run 100"
```

**Available filters:** `status_id` (API-side), `assignedto_id`, `priority_id`, `type_id` (client-side), `limit`, `offset`.

### Pagination

All list operations support `limit` and `offset`:
```
"Get first 50 test cases in project 1"
"Get next 50 cases with offset 50"
```

---

## Server Health Monitoring

Check the server's operational status:

```
"Check TestRail server health"
```

Returns:
- **Cache status** — which caches are loaded and entry counts
- **Rate limiter** — available API calls and capacity
- **Request metrics** — total, successful, failed, error rate
- **Cache performance** — hit rate percentage
- **Uptime** — server runtime

---

## Troubleshooting

### "Connection Error" or server fails to start

1. Verify `uvx` is installed: `uvx --version`
2. Check your TestRail URL, username, and API key
3. Ensure your TestRail instance is reachable

### "Missing required fields" when creating test cases

Run cache initialization first:
```
"Get case fields from TestRail"
```
Then check which fields are required (marked in the response).

### Custom field values not recognized

1. Call `get_case_fields` to see valid values
2. Check spelling — matching is case-insensitive
3. Use numeric IDs as fallback

### Code changes not taking effect

The uvx cache needs clearing:
```bash
uv cache clean testrail-mcp --force
```
Then restart the MCP connection in your AI client.

### Images showing as text in TestRail

You're using markdown syntax. TestRail uses HTML:
- **Wrong:** `![](index.php?/attachments/get/123)`
- **Right:** `<img src="index.php?/attachments/get/123" />`

---

## FAQ

### Q: Do I need to warm caches every time?
**A:** Only after the MCP server restarts (reconnects). Caches persist for 24 hours in-memory. Call `get_case_fields` and `get_statuses` after each restart, or set `TESTRAIL_PRELOAD_CACHE=1` to warm them automatically at startup.

### Q: Can I use this with multiple TestRail projects?
**A:** Yes. All projects accessible to your API key are available through the same server.

### Q: Is my API key secure?
**A:**
- Keys are passed as environment variables (not in code)
- Never logged or stored persistently
- Don't commit `.mcp.json` files with real credentials to git

### Q: What TestRail API version is supported?
**A:** TestRail API v2 (current stable version). Attachment IDs support both numeric (pre-7.1) and alphanumeric UUID format (7.1+).

### Q: Can I use this in CI/CD pipelines?
**A:** This is designed for human-AI interaction via MCP. For automation, use TestRail's API directly.

---

## Getting Help

**Check logs:**
- Claude Code: check the MCP server output in terminal
- Claude Desktop: `~/Library/Logs/Claude/mcp*.log` (macOS)
- VS Code: Open "MCP" output channel

**Common commands:**
```bash
# Check uvx is working
uvx --version

# Clear cached server (after code changes)
uv cache clean testrail-mcp --force
```

---

**Version:** 2.2.0
**Maintainer:** Harmony SASE Team
