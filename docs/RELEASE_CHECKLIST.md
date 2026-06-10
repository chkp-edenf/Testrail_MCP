# Release Checklist

Follow this every time a new version tag is pushed (e.g., `v2.1.0`).

## Release steps

1. **Bump `version`** in `pyproject.toml` to the new semver (e.g., `"2.1.0"`).
2. **Update `TESTRAIL_MCP_REF` default** in `install.sh` — search for `DEFAULT_REF="main"` and change to the new tag.
3. **Update `$DefaultRef`** in `install.ps1` — search for `$DefaultRef = 'main'` and change to the new tag.
4. **Update Quick Install URLs** in `README.md` — replace `main` with the new tag in both curl and irm one-liners (`raw.githubusercontent.com/.../main/install.sh` → `.../vX.Y.Z/install.sh`).
5. **Tag and push**: `git tag vX.Y.Z && git push origin vX.Y.Z`.
6. **Smoke-test the one-liners** from a clean shell (new terminal, no cached `uv`):
   - `curl -LsSf https://raw.githubusercontent.com/chkp-edenf/Testrail_MCP/vX.Y.Z/install.sh | sh` on macOS/Linux.
   - `irm https://raw.githubusercontent.com/chkp-edenf/Testrail_MCP/vX.Y.Z/install.ps1 | iex` on Windows.
   - Both should end up prompting the wizard (or failing cleanly if `uv` is missing).

## Why these steps matter

The wizard's default git ref is `main` until a tag is published. Shipping a tagged release without flipping the default in `install.sh`/`install.ps1` leaves new users pulling unreleased `main` — possibly with breaking changes. The README one-liners reference `main/install.sh`; after a release, pointing them at the tag makes the URL immutable (a shared link won't 404 or silently upgrade).

## Related

- ADR-001 D3 decides the uvx ref pinning strategy.
- plan-001 Step 10.1 records this checklist as the mitigation for the "non-reproducible `main` default" risk.
