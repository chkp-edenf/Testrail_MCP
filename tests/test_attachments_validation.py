"""Security tests for src/server/api/attachments._validate_file_path.

spektr v2.0 HIGH finding: substring matching on the original path
produced false positives (legit upload from /work/credentials-mgr/)
and false negatives (symlink from screenshot.png to ~/.aws/credentials
bypassed the check because the substring lookup ran on the symlink
path, not the resolved target).

These tests pin the new contract:
- Symlinks are rejected.
- Sensitive directories match path COMPONENTS, not substrings.
- Sensitive filenames match basename exactly or as a basename substring.
- Path resolution happens BEFORE the checks, so symlink targets are
  evaluated.
- A successful validate returns the resolved canonical Path so the
  caller `open()`s the same path that passed the checks (no TOCTOU
  re-resolve).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from src.server.api.attachments import (
    ALLOWED_EXTENSIONS,
    BLOCKED_DIR_NAMES,
    BLOCKED_FILE_NAMES,
    _validate_file_path,
)


# ---------------------------------------------------------------------------
# Happy path — benign uploads pass
# ---------------------------------------------------------------------------

def test_validate_accepts_allowed_extension(tmp_path: Path) -> None:
    target = tmp_path / "screenshot.png"
    target.write_bytes(b"fake png data")
    resolved = _validate_file_path(str(target))
    assert resolved == target.resolve()
    assert resolved.is_file()


def test_validate_accepts_uppercase_extension(tmp_path: Path) -> None:
    """`.PNG` is the same content type as `.png` — case-insensitive."""
    target = tmp_path / "ScreenShot.PNG"
    target.write_bytes(b"fake png")
    resolved = _validate_file_path(str(target))
    assert resolved.suffix.lower() == ".png"


def test_validate_accepts_benign_directory_with_keyword_in_name(
    tmp_path: Path,
) -> None:
    """spektr false-positive fix: `/work/credentials-mgr/` is benign.

    The pre-fix substring check blocked any path whose absolute string
    contained 'credentials' anywhere, including legit working dirs
    named 'credentials-mgr' or 'no-secrets'. The component-match check
    only blocks exact directory-name hits.
    """
    benign = tmp_path / "credentials-mgr" / "diagram.png"
    benign.parent.mkdir()
    benign.write_bytes(b"diagram")
    resolved = _validate_file_path(str(benign))
    assert resolved == benign.resolve()


# ---------------------------------------------------------------------------
# Blocked: symlinks rejected outright
# ---------------------------------------------------------------------------

@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need admin on Windows")
def test_validate_rejects_symlink_to_legit_target(tmp_path: Path) -> None:
    """Pre-fix bypass: screenshot.png symlinked to ~/.aws/credentials
    would resolve via open() to the real target but the substring
    check ran on 'screenshot.png' (no .aws / credentials substring),
    so it passed. New behavior: symlinks rejected before resolution.
    """
    real = tmp_path / "real.png"
    real.write_bytes(b"png")
    link = tmp_path / "screenshot.png"
    link.symlink_to(real)

    with pytest.raises(ValueError, match="symbolic link"):
        _validate_file_path(str(link))


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need admin on Windows")
def test_validate_rejects_symlink_to_sensitive_file(tmp_path: Path) -> None:
    """The motivating bypass: symlink with a benign name pointing at a
    real credentials file. Even if symlinks were resolved, the target
    must also fail the blocked-dir check — but rejecting the symlink
    upfront is the simpler, stricter rule.
    """
    fake_aws = tmp_path / ".aws"
    fake_aws.mkdir()
    creds = fake_aws / "credentials"
    creds.write_text("[default]\naws_access_key_id=AKIA…\n")

    link = tmp_path / "innocent.png"
    link.symlink_to(creds)

    with pytest.raises(ValueError, match="symbolic link"):
        _validate_file_path(str(link))


# ---------------------------------------------------------------------------
# Blocked: directory components
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dir_name", sorted(BLOCKED_DIR_NAMES))
def test_validate_rejects_sensitive_directory_component(
    tmp_path: Path, dir_name: str,
) -> None:
    """Any file inside a sensitive directory should be blocked — even
    if its own filename and extension would otherwise be allowed.
    """
    sensitive = tmp_path / dir_name / "screenshot.png"
    sensitive.parent.mkdir()
    sensitive.write_bytes(b"png")

    with pytest.raises(ValueError, match="sensitive directory"):
        _validate_file_path(str(sensitive))


def test_validate_rejects_nested_sensitive_directory(tmp_path: Path) -> None:
    """`.aws` deep in the path still trips the component check."""
    nested = tmp_path / "user" / "home" / ".aws" / "shot.png"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"png")

    with pytest.raises(ValueError, match="sensitive directory"):
        _validate_file_path(str(nested))


# ---------------------------------------------------------------------------
# Blocked: filenames
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(BLOCKED_FILE_NAMES))
def test_validate_rejects_exact_sensitive_filename(
    tmp_path: Path, name: str,
) -> None:
    target = tmp_path / name
    target.write_text("sensitive")
    with pytest.raises(ValueError, match="sensitive-files deny list"):
        _validate_file_path(str(target))


@pytest.mark.parametrize(
    "filename",
    [
        "aws_credentials.json",
        "production_secrets.txt",
        "my_private_key.pem",
        "CREDENTIALS.LOG",  # case-insensitive
    ],
)
def test_validate_rejects_basename_keyword_match(
    tmp_path: Path, filename: str,
) -> None:
    target = tmp_path / filename
    target.write_text("sensitive")
    # `.pem` isn't in ALLOWED_EXTENSIONS — keyword check runs first so
    # the error mentions the keyword, not the extension.
    if Path(filename).suffix.lower() in ALLOWED_EXTENSIONS:
        with pytest.raises(ValueError, match="sensitive keyword"):
            _validate_file_path(str(target))
    else:
        # For disallowed extensions, the keyword OR extension rule may
        # fire — assert one of them does.
        with pytest.raises(ValueError):
            _validate_file_path(str(target))


# ---------------------------------------------------------------------------
# Blocked: disallowed extensions
# ---------------------------------------------------------------------------

def test_validate_rejects_disallowed_extension(tmp_path: Path) -> None:
    target = tmp_path / "binary.exe"
    target.write_bytes(b"MZ\x90\x00")
    with pytest.raises(ValueError, match="extension '.exe' not allowed"):
        _validate_file_path(str(target))


def test_validate_rejects_no_extension(tmp_path: Path) -> None:
    target = tmp_path / "noextension"
    target.write_text("data")
    with pytest.raises(ValueError, match="extension '' not allowed"):
        _validate_file_path(str(target))


# ---------------------------------------------------------------------------
# Blocked: missing file / non-regular file
# ---------------------------------------------------------------------------

def test_validate_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="File not found"):
        _validate_file_path(str(tmp_path / "nope.png"))


def test_validate_rejects_directory(tmp_path: Path) -> None:
    subdir = tmp_path / "subdir.png"  # extension on a directory name
    subdir.mkdir()
    with pytest.raises(ValueError, match="Not a regular file"):
        _validate_file_path(str(subdir))
