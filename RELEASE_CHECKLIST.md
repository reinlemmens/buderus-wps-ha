# Release Checklist

This checklist ensures all releases are properly validated before publication. **ALL items are MANDATORY** for any release (major, minor, or patch).

## Pre-Release Requirements

### 1. Code Quality (REQUIRED)

- [ ] All pytest tests pass: `pytest tests/unit/ tests/integration/ tests/acceptance/`
- [ ] Type checking passes: `mypy buderus_wps buderus_wps_cli`
- [ ] Linting passes: `ruff check .`
- [ ] Code formatted: `black .`
- [ ] No uncommitted changes: `git status`

### 2. End-to-End Validation (REQUIRED - NON-NEGOTIABLE)

**See [DEVELOPMENT.md - End-to-End Validation](DEVELOPMENT.md#end-to-end-validation-required-before-release) for detailed instructions.**

**CRITICAL**: Test the ACTUAL release zip file, not the development directory!

- [ ] **Release artifact built**: `./scripts/build-release.sh vX.Y.Z` creates zip file
- [ ] **Bundled library verified**: Zip contains `custom_components/buderus_wps/buderus_wps/` directory with 20 Python files
- [ ] **Release artifact extracted**: Unzipped to `/tmp/release-test` for inspection
- [ ] **Release artifact installed in HA**: Copied to `/config/custom_components/` (overwrites dev version)
- [ ] HA restarted to load release artifact (not development code)
- [ ] HA startup logs checked - no AttributeError, ImportError, ModuleNotFoundError
- [ ] Config entry created via UI without errors
- [ ] All expected entities appear (5 sensors, 1 binary sensor, 1 switch, 1 number)
- [ ] Entity attributes verified (no missing or undefined attributes)
- [ ] Staleness metadata present (as of v1.3.x): `last_update_age_seconds`, `data_is_stale`, `last_successful_update`
- [ ] State changes tested (toggle switches, check logs)
- [ ] Error handling tested (connection loss scenario if possible)
- [ ] HA logs reviewed - no unexpected errors or warnings

**E2E Validation Sign-Off:**

```
Tested in Home Assistant [VERSION]:
✅ Integration loads without errors
✅ All entities created successfully
✅ Entity attributes correct
✅ Error handling works
✅ Logs clean

Environment: [describe environment]
Tester: [your name]
Date: [YYYY-MM-DD]
```

### 3. Version Management (REQUIRED)

- [ ] Version bumped in `custom_components/buderus_wps/manifest.json`
- [ ] Version bumped in `custom_components/buderus_wps/entity.py` (sw_version)
- [ ] Version follows semantic versioning (major.minor.patch)
- [ ] Version matches intended release tag (e.g., manifest.json = "1.3.1" → tag = v1.3.1)

### 4. Documentation (REQUIRED)

- [ ] CHANGELOG updated (if exists) or release notes prepared
- [ ] Breaking changes documented (for major/minor releases)
- [ ] New features documented in release notes
- [ ] Bug fixes documented in release notes

## Release Process

### 5. Git Operations (REQUIRED)

- [ ] All changes committed to main branch
- [ ] Commit messages follow Conventional Commits format
- [ ] Version bump committed: `git commit -m "chore: bump version to X.Y.Z"`
- [ ] Changes pushed to origin: `git push origin main`

### 6. Build and Package (REQUIRED)

- [ ] Release script executed: `./scripts/build-release.sh vX.Y.Z`
- [ ] Build validation passes (imports, bundling, patching)
- [ ] Release archive created: `buderus-wps-ha-vX.Y.Z.zip`
- [ ] Archive size reasonable (~700KB expected)

### 7. GitHub Release (REQUIRED)

- [ ] Git tag created: `git tag vX.Y.Z`
- [ ] Tag pushed to origin: `git push origin vX.Y.Z`
- [ ] GitHub release created via `gh release create` or UI
- [ ] Release notes include:
  - Summary of changes
  - Bug fixes (if patch release)
  - New features (if minor/major release)
  - Breaking changes (if major release)
  - E2E validation sign-off
  - Upgrade instructions (if needed)
- [ ] Release archive attached to GitHub release
- [ ] Release published (not draft)
- [ ] Release verified on GitHub: `gh release view vX.Y.Z`

## Post-Release Validation

### 8. HACS Verification (REQUIRED)

- [ ] Wait 5-10 minutes for HACS to poll GitHub releases
- [ ] Verify release appears in HACS (if installed in test HA instance)
- [ ] Verify download count increments (check GitHub release stats)

### 9. User Communication (RECOMMENDED)

- [ ] Announcement in GitHub Discussions (if major/minor release)
- [ ] Note critical fixes in release notes (if patch release fixing a bug)
- [ ] Update README.md if installation instructions changed

## Rollback Plan (In Case of Critical Issues)

If a critical bug is discovered after release:

### Option 1: Immediate Patch Release (Preferred)

1. Fix the bug on main branch
2. Follow full release checklist for vX.Y.Z+1 (patch release)
3. Add "HOTFIX" tag to release notes
4. Include rollback instructions in release notes if needed

### Option 2: Delete Release (Only for Severe Breakage)

```bash
# Delete GitHub release
gh release delete vX.Y.Z --yes

# Delete git tag
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z

# Revert commits if needed
git revert <commit-hash>
git push origin main
```

**Note:** Deleting releases should be avoided. Prefer immediate patch release.

## Lessons Learned from v1.3.0 Bug

**Context:** v1.3.0 was released with an `AttributeError: 'BuderusCoordinator' object has no attribute '_stale_data_threshold'` that broke user installations.

**Root Cause:**
- Pytest tests all passed (using mocks)
- E2E validation was NOT performed
- Integration was never tested in actual Home Assistant instance
- Runtime error was not caught until users installed it

**Prevention:**
- **NEVER skip E2E validation** - this checklist now makes it mandatory
- Pytest tests alone are insufficient for Home Assistant integrations
- Always test in running HA instance before releasing
- Check logs for AttributeError, ImportError, and runtime exceptions

**Result:**
- Immediate patch release v1.3.1 required
- User trust impacted
- Additional testing burden

**Takeaway:** E2E validation is non-negotiable. Releases without it are considered incomplete.

## Lessons Learned from v1.3.1 Bug

**Context:** v1.3.1 was released to fix v1.3.0, but users reported `ModuleNotFoundError: No module named 'buderus_wps'` when running in devcontainer/development environments.

**Root Cause:**
- Release zip was CORRECT (build script properly bundled library and patched imports)
- Development version in git had ABSOLUTE imports, release had RELATIVE imports
- E2E validation tested development directory, NOT the actual release zip
- Development version and release version had different import structures

**Discovery:**
- Release artifact inspection revealed all imports were correctly patched to relative
- Development coordinator.py had 3 absolute imports (lines 164, 171, 396)
- Build script patches imports during release, but git repo still had absolute imports
- Testing dev directory ≠ testing what users actually install

**Prevention:**
- **ALWAYS test the actual release zip file** - this checklist now requires it
- Extract and install the zip to HA before releasing
- Verify bundled library exists in zip (`custom_components/buderus_wps/buderus_wps/`)
- Development code can diverge from release artifact
- Build process can introduce changes not visible in git

**Fix Applied:**
- Updated development version to use relative imports (matching release)
- Now dev and release have consistent import structure
- Commit 2365c8d: "fix: use relative imports for bundled library in development version"

**Result:**
- Development version now matches release version
- Easier to test locally without running build script
- Import consistency between dev and prod

**Takeaway:** Development code ≠ Release artifact. Always test what users actually install, not what's in your git repo.

---

## Checklist Summary

**Quick verification before release:**

```bash
# 1. Code Quality
pytest tests/unit/ tests/integration/ tests/acceptance/ && \
mypy buderus_wps buderus_wps_cli && \
ruff check . && \
black . && \
git status

# 2. E2E Validation (manual - see DEVELOPMENT.md)
# → Install in HA, create config entry, verify entities, check logs

# 3. Version Management
# → Update manifest.json and entity.py

# 4. Release Process
git push origin main
./scripts/build-release.sh vX.Y.Z
git tag vX.Y.Z && git push origin vX.Y.Z
gh release create vX.Y.Z buderus-wps-ha-vX.Y.Z.zip --title "..." --notes "..."

# 5. Post-Release
gh release view vX.Y.Z
# → Wait for HACS to poll, verify in UI
```

**Remember:** If you can't check all boxes, **don't release**. Incomplete releases cause more work than they save.
