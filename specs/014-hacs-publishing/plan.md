# Implementation Plan: HACS Publishing

**Branch**: `014-hacs-publishing` | **Date**: 2025-12-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/014-hacs-publishing/spec.md`

## Summary

Enable HACS (Home Assistant Community Store) distribution for the Buderus WPS Heat Pump integration. This involves creating the required `hacs.json` configuration file, verifying manifest.json compliance, updating README documentation, creating a GitHub release, and optionally submitting branding to home-assistant/brands.

**Technical Approach**: Configuration-only changes - no code modifications. Create required metadata files and documentation updates to meet HACS validation requirements.

## Technical Context

**Language/Version**: N/A (JSON configuration files only)
**Primary Dependencies**: HACS validation requirements, GitHub Releases API
**Storage**: N/A
**Testing**: Manual HACS validation (add as custom repository)
**Target Platform**: Home Assistant with HACS installed
**Project Type**: Configuration/metadata
**Performance Goals**: N/A
**Constraints**: Must pass HACS validation, must follow home-assistant/brands guidelines
**Scale/Scope**: Single integration publishing

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies | Status | Notes |
|-----------|---------|--------|-------|
| I. Library-First | No | N/A | No new library code |
| II. Hardware Abstraction | No | N/A | No protocol changes |
| III. Safety & Reliability | No | N/A | No operational code changes |
| IV. Comprehensive Test Coverage | No | N/A | Metadata files only - no testable code |
| V. Protocol Documentation | No | N/A | No protocol changes |

**Gate Status**: PASS - This feature adds only configuration/metadata files, not executable code. Constitution principles apply to code changes, not publishing infrastructure.

## Project Structure

### Documentation (this feature)

```text
specs/014-hacs-publishing/
├── plan.md              # This file
├── research.md          # HACS requirements research
├── data-model.md        # hacs.json and manifest.json schemas
├── quickstart.md        # Validation testing guide
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (repository root)

```text
# Files to create/modify
hacs.json                                    # NEW: HACS configuration
README.md                                    # UPDATE: Add HACS badge and installation
custom_components/buderus_wps/
├── manifest.json                            # VERIFY: All required fields present
└── branding/                                # CREATED: Icon assets
    ├── icon.svg
    ├── icon-transparent.svg
    ├── icon.png                             # 256x256
    ├── icon@2x.png                          # 512x512
    ├── icon-circle.png
    └── icon-circle@2x.png

# GitHub (manual steps)
- Create GitHub Release v1.0.0
- Submit PR to home-assistant/brands (optional, P3)
```

**Structure Decision**: Minimal file additions - only `hacs.json` in repo root and README updates. Branding assets already created in `custom_components/buderus_wps/branding/`.

## Implementation Phases

### Phase 1: HACS Configuration (P1)

1. **Create hacs.json** in repository root
   - Set `name` to match manifest.json
   - Set `render_readme` to true for documentation display
   - Specify integration type

2. **Verify manifest.json** compliance
   - All required fields present (verified)
   - URLs are valid and accessible

3. **Update README.md**
   - Add HACS badge at top
   - Add HACS installation instructions section
   - Keep existing manual installation for reference

### Phase 2: GitHub Release (P1)

1. **Create release v1.0.0**
   - Tag: `v1.0.0` (matches manifest.json version)
   - Title: "v1.0.0 - Initial HACS Release"
   - Release notes: Feature summary, installation instructions

2. **Verify release assets**
   - Source code auto-included by GitHub
   - No additional assets needed (HACS downloads from source)

### Phase 3: Branding Submission (P3, Optional)

1. **Prepare brand assets**
   - icon.png (256x256) - Created
   - icon@2x.png (512x512) - Created

2. **Fork home-assistant/brands**
   - Create `custom_integrations/buderus_wps/` directory
   - Add icon.png and icon@2x.png
   - Submit PR with integration description

### Phase 4: Validation (P1)

1. **Test HACS installation**
   - Add repository as custom repository in HACS
   - Verify no validation errors
   - Test install flow
   - Verify upgrade detection

## Complexity Tracking

No complexity violations - this feature adds only configuration files.

## Dependencies

| Dependency | Type | Status |
|------------|------|--------|
| manifest.json | Internal | Complete - all required fields present |
| GitHub repository | External | Exists |
| HACS | External | Standard requirement |
| home-assistant/brands | External | Optional (P3) |

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| HACS validation fails | Blocks P1 | Test with `hacs-action` locally before release |
| Branding PR rejected | Delays P3 | Not blocking - icon shows as generic until approved |
| Version mismatch | Confusing UX | Ensure manifest.json and release tag match |

## Success Validation

- [ ] `hacs.json` created and valid JSON
- [ ] HACS accepts repository as custom repository (0 errors)
- [ ] Integration installs successfully via HACS
- [ ] README shows HACS badge and installation instructions
- [ ] GitHub release v1.0.0 created with release notes
- [ ] (Optional) Branding PR submitted to home-assistant/brands
