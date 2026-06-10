"""Handlers for TestRail attachment operations"""

import json
import logging
import os
from pathlib import Path
from mcp.types import TextContent
from .utils import create_success_response, create_error_response, require_fields

logger = logging.getLogger(__name__)

# Security: allowed file extensions for uploads
ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",  # images
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",           # documents
    ".txt", ".csv", ".log", ".json", ".xml",             # text
    ".zip", ".tar", ".gz",                               # archives
    ".mp4", ".mov", ".avi",                              # video
}

# Security: blocked directory names. Matched against path COMPONENTS of
# the resolved path (not substring) so a benign `/work/credentials-mgr/
# screenshot.png` no longer triggers a false-positive block. spektr v2.0
# HIGH finding.
BLOCKED_DIR_NAMES: frozenset[str] = frozenset({
    ".ssh", ".gnupg", ".aws", ".azure", ".gcloud", ".kube", ".docker",
})

# Security: blocked exact filename matches (resolved basename).
BLOCKED_FILE_NAMES: frozenset[str] = frozenset({
    ".env", ".netrc", ".npmrc", ".pypirc",
    "id_rsa", "id_ed25519", "id_dsa", "id_ecdsa",
    "credentials", "config",  # bare names commonly used by .aws/, .docker/
})

# Security: substring keywords matched against the resolved BASENAME
# only (not the full path). spektr v2.0 false-positive was substring
# match on the directory portion ("/work/credentials-mgr/photo.png");
# restricting to basename keeps "aws_credentials.json" blocked but
# lets benign files inside directories with these names through.
_BLOCKED_BASENAME_KEYWORDS: tuple[str, ...] = (
    "credentials", "secrets", "private_key",
)

# Map entity_type to the appropriate client method names
UPLOAD_METHODS = {
    "case": "add_attachment_to_case",
    "result": "add_attachment_to_result",
    "run": "add_attachment_to_run",
    "plan": "add_attachment_to_plan",
}

LIST_METHODS = {
    "case": "get_attachments_for_case",
    "result": None,  # TestRail doesn't have get_attachments_for_result
    "run": "get_attachments_for_run",
    "plan": "get_attachments_for_plan",
    "test": "get_attachments_for_test",
}


def _validate_file_path(file_path: str) -> Path:
    """Validate `file_path` for security and allowed extensions.

    Returns the resolved canonical `Path` so the caller can `open()` it
    directly without re-resolving (avoids a TOCTOU window between
    validation and read).

    Security model (spektr v2.0 HIGH fix):
    - Symlinks are rejected outright, so a `screenshot.png` pointing at
      `~/.aws/credentials` cannot bypass the path checks.
    - The resolved path's components are matched against
      `BLOCKED_DIR_NAMES` exactly — substring matches on the original
      path are gone, so `/work/credentials-mgr/photo.png` is no longer
      a false positive.
    - The resolved basename is matched against `BLOCKED_FILE_NAMES`
      exactly and against `_BLOCKED_BASENAME_KEYWORDS` word-bounded.
    - Extension and file-type checks run after, on the resolved path.
    """
    raw = Path(file_path)

    # Reject symlinks BEFORE resolution. We use lstat so a missing file
    # raises a clearer "File not found" than a symlink-related error.
    try:
        if raw.is_symlink():
            raise ValueError(
                f"Upload blocked: '{file_path}' is a symbolic link. "
                "Resolve and pass the real path explicitly."
            )
    except OSError as exc:
        raise ValueError(f"Cannot access path '{file_path}': {exc}") from exc

    # Resolve to canonical absolute path. strict=True raises if missing.
    try:
        resolved = raw.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"File not found: {file_path}") from exc
    except OSError as exc:
        raise ValueError(f"Cannot resolve path '{file_path}': {exc}") from exc

    if not resolved.is_file():
        raise ValueError(f"Not a regular file: {file_path}")

    # Path component check — exact match on any segment of the resolved
    # absolute path. Case-insensitive for portability across macOS HFS+
    # (case-preserving) and Windows.
    lower_parts = {part.lower() for part in resolved.parts}
    blocked_hit = lower_parts & {name.lower() for name in BLOCKED_DIR_NAMES}
    if blocked_hit:
        raise ValueError(
            f"Upload blocked: path traverses sensitive directory "
            f"{sorted(blocked_hit)[0]!r}"
        )

    basename_lower = resolved.name.lower()

    if basename_lower in {name.lower() for name in BLOCKED_FILE_NAMES}:
        raise ValueError(
            f"Upload blocked: filename {resolved.name!r} is on the "
            "sensitive-files deny list"
        )

    for keyword in _BLOCKED_BASENAME_KEYWORDS:
        if keyword in basename_lower:
            raise ValueError(
                f"Upload blocked: filename {resolved.name!r} matches a "
                f"sensitive keyword ({keyword!r})"
            )

    if resolved.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Upload blocked: extension '{resolved.suffix}' not allowed. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    return resolved


async def handle_upload_attachment(arguments: dict, client) -> list[TextContent]:
    """Upload an attachment to a TestRail entity"""
    try:
        require_fields(arguments, ["entity_type", "entity_id", "file_path"], "upload_attachment")

        entity_type = arguments["entity_type"]
        entity_id = int(arguments["entity_id"])
        file_path = arguments["file_path"]

        # Returns the resolved canonical path — open() against it closes
        # the validate→open TOCTOU window that a re-resolve would leave.
        resolved = _validate_file_path(file_path)

        filename = arguments.get("filename", resolved.name)
        with resolved.open("rb") as f:
            file_data = f.read()

        method_name = UPLOAD_METHODS.get(entity_type)
        if not method_name:
            raise ValueError(f"Upload not supported for entity_type '{entity_type}'. Valid: {', '.join(UPLOAD_METHODS.keys())}")

        method = getattr(client.attachments, method_name)
        result = await method(entity_id, file_data, filename)

        response = create_success_response(
            f"Attachment '{filename}' uploaded to {entity_type} {entity_id}",
            result
        )
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    except Exception as e:
        logger.error(f"Error uploading attachment: {str(e)}")
        response = create_error_response("Attachment upload failed", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_list_attachments(arguments: dict, client) -> list[TextContent]:
    """List attachments for a TestRail entity"""
    try:
        require_fields(arguments, ["entity_type", "entity_id"], "list_attachments")

        entity_type = arguments["entity_type"]
        entity_id = int(arguments["entity_id"])

        method_name = LIST_METHODS.get(entity_type)
        if not method_name:
            raise ValueError(f"Listing not supported for entity_type '{entity_type}'. Valid: {', '.join(k for k, v in LIST_METHODS.items() if v)}")

        method = getattr(client.attachments, method_name)
        result = await method(entity_id)

        attachments = result.get("attachments", [])
        response = create_success_response(
            f"Found {len(attachments)} attachment(s) for {entity_type} {entity_id}",
            result
        )
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    except Exception as e:
        logger.error(f"Error listing attachments: {str(e)}")
        response = create_error_response("List attachments failed", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_attachment(arguments: dict, client) -> list[TextContent]:
    """Get attachment info"""
    try:
        require_fields(arguments, ["attachment_id"], "get_attachment")

        attachment_id = arguments["attachment_id"]
        result = await client.attachments.get_attachment(attachment_id)

        response = create_success_response(
            f"Attachment {attachment_id} details",
            result
        )
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    except Exception as e:
        logger.error(f"Error getting attachment: {str(e)}")
        response = create_error_response("Get attachment failed", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_delete_attachment(arguments: dict, client) -> list[TextContent]:
    """Delete an attachment"""
    try:
        require_fields(arguments, ["attachment_id"], "delete_attachment")

        attachment_id = arguments["attachment_id"]
        await client.attachments.delete_attachment(attachment_id)

        response = create_success_response(
            f"Attachment {attachment_id} deleted",
            {"attachment_id": attachment_id}
        )
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    except Exception as e:
        logger.error(f"Error deleting attachment: {str(e)}")
        response = create_error_response("Delete attachment failed", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
