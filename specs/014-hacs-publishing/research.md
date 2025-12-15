# Research: HACS Publishing Requirements

**Feature**: 014-hacs-publishing
**Date**: 2025-12-15

## HACS Integration Requirements

### Source: https://www.hacs.xyz/docs/publish/integration/

#### Repository Structure Requirements

**Decision**: Single integration per repository
**Rationale**: HACS requires exactly one subdirectory under `custom_components/`
**Alternatives Considered**: Multi-integration repos - rejected by HACS spec

**Current State**: ✅ Compliant
- Single integration: `custom_components/buderus_wps/`

#### Required Files

**Decision**: Create `hacs.json` in repository root
**Rationale**: Required for HACS to identify and configure the integration
**Alternatives Considered**: None - mandatory requirement

**hacs.json Required Fields**:
- `name`: Integration display name (must match manifest.json)

**hacs.json Optional Fields**:
- `render_readme`: Boolean, display README in HACS (recommended: true)
- `content_in_root`: Boolean, if files are at root instead of subdirectory (false for standard layout)
- `zip_release`: Boolean, if using zip file releases (false - use source)
- `filename`: String, main file name (not needed for integrations)
- `homeassistant`: String, minimum HA version (optional)

#### manifest.json Requirements

**Decision**: Verify existing manifest.json has all required fields
**Rationale**: HACS validates manifest.json for required Home Assistant fields
**Alternatives Considered**: None - mandatory requirement

**Required Fields** (all present in current manifest.json):
| Field | Current Value | Status |
|-------|---------------|--------|
| domain | "buderus_wps" | ✅ |
| name | "Buderus WPS Heat Pump" | ✅ |
| codeowners | ["@reinlemmens"] | ✅ |
| documentation | "https://github.com/reinlemmens/buderus-wps-ha" | ✅ |
| issue_tracker | "https://github.com/reinlemmens/buderus-wps-ha/issues" | ✅ |
| version | "1.0.0" | ✅ |

**Additional Fields** (already present):
- config_flow: true
- requirements: ["pyserial>=3.5"]
- iot_class: "local_polling"
- integration_type: "device"

### GitHub Releases

**Decision**: Use GitHub releases with semantic versioning
**Rationale**: HACS displays 5 most recent releases for version selection; preferred over branch-only
**Alternatives Considered**: No releases (branch only) - functional but less user-friendly

**Release Format**:
- Tag: `v1.0.0` (semantic versioning with 'v' prefix)
- Version must match manifest.json `version` field
- Release notes recommended for user communication

### Branding Requirements

**Decision**: Create PNG icons, optionally submit to home-assistant/brands
**Rationale**: Required for integration icon in HA UI; without brands submission shows generic icon
**Alternatives Considered**: Skip branding - functional but less professional

**Source**: https://github.com/home-assistant/brands

**Icon Requirements**:
| File | Size | Status |
|------|------|--------|
| icon.png | 256×256 | ✅ Created |
| icon@2x.png | 512×512 | ✅ Created |
| logo.png | 256×128 max | Optional |
| dark_icon.png | 256×256 | Optional |

**Format Requirements**:
- PNG format
- Transparent background preferred
- Lossless compression preferred
- Square for icons (1:1 ratio)

**Submission Path**: `custom_integrations/buderus_wps/` in brands repo

### README Requirements

**Decision**: Add HACS badge and installation section
**Rationale**: User discoverability and installation guidance
**Alternatives Considered**: None - best practice for HACS integrations

**HACS Badge**:
```markdown
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
```

**Installation Section**:
- HACS custom repository URL
- Step-by-step installation via HACS
- Maintain existing manual installation for reference

## Validation Methods

### Local Validation

**Decision**: Test with HACS custom repository before default submission
**Rationale**: Immediate feedback on validation errors
**Alternatives Considered**: Submit directly to default repo - higher risk of rejection

**Steps**:
1. Push changes to GitHub
2. In HACS: Settings → Custom repositories
3. Add repository URL
4. Select "Integration" category
5. Verify no validation errors
6. Test install flow

### Automated Validation (Optional)

**Tool**: `hacs-action` GitHub Action
**Purpose**: CI validation of HACS requirements
**Status**: Optional for initial release, recommended for ongoing development

## Decisions Summary

| Decision | Choice | Confidence |
|----------|--------|------------|
| Repository structure | Keep existing single-integration layout | High |
| hacs.json | Create with minimal required fields | High |
| manifest.json | No changes needed | High |
| Releases | Create v1.0.0 matching manifest version | High |
| Branding | Submit to home-assistant/brands (P3) | Medium |
| README | Add HACS badge and installation section | High |
| Validation | Manual custom repository test first | High |
