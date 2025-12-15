# Feature Specification: HACS Publishing

**Feature Branch**: `014-hacs-publishing`
**Created**: 2025-12-15
**Status**: Draft
**Input**: User description: "Publish integration on HACS (Home Assistant Community Store)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install via HACS (Priority: P1)

A Home Assistant user discovers the Buderus WPS integration in the HACS store. They want to install it directly from HACS without manually copying files, ensuring they always get the latest version with easy update notifications.

**Why this priority**: This is the core value proposition - users can discover, install, and update the integration through HACS rather than manual installation.

**Independent Test**: Can be fully tested by adding the repository to HACS (as custom repository initially), searching for it, and completing the installation flow.

**Acceptance Scenarios**:

1. **Given** a Home Assistant instance with HACS installed, **When** the user adds the repository URL as a custom repository in HACS, **Then** the integration appears in the list and is marked as valid.
2. **Given** the integration is found in HACS, **When** the user clicks install, **Then** all integration files are downloaded to `custom_components/buderus_wps/` and the integration is ready for configuration.
3. **Given** the integration is installed via HACS, **When** a new version is released on GitHub, **Then** HACS notifies the user and offers an upgrade path.

---

### User Story 2 - View Integration Information (Priority: P2)

A potential user browses the HACS store and wants to learn about the Buderus WPS integration before installing. They need to see documentation links, version information, and understand what the integration does.

**Why this priority**: Discovery and informed decision-making are essential for adoption but secondary to actual installation capability.

**Independent Test**: Can be verified by viewing the integration's HACS page and confirming all metadata displays correctly.

**Acceptance Scenarios**:

1. **Given** the integration listing in HACS, **When** the user views the details, **Then** they see the integration name, version, description, documentation link, and issue tracker link.
2. **Given** the integration listing in HACS, **When** the user clicks the documentation link, **Then** they are directed to the project's documentation with installation and usage instructions.
3. **Given** the integration listing in HACS, **When** the user views available versions, **Then** they see the most recent GitHub releases to choose from.

---

### User Story 3 - See Proper Branding in Home Assistant (Priority: P3)

After installation, the user expects to see proper branding (icon and logo) for the Buderus WPS integration in the Home Assistant UI, consistent with other integrations.

**Why this priority**: Branding enhances professional appearance but the integration is fully functional without it.

**Independent Test**: Can be verified by checking the integration appears with correct icon in Home Assistant's Integrations page after installation.

**Acceptance Scenarios**:

1. **Given** the integration is installed, **When** the user views the Integrations page in Home Assistant, **Then** the Buderus WPS integration displays with its branded icon.
2. **Given** branding is submitted to home-assistant/brands, **When** the submission is approved, **Then** the icon appears automatically for all users.

---

### Edge Cases

- What happens when users have an existing manual installation when installing via HACS? (HACS overwrites files in `custom_components/buderus_wps/`)
- What happens if the GitHub repository is temporarily unavailable during install? (HACS shows appropriate error message)
- What happens if a user downgrades to an older version? (HACS allows selecting from available releases)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Repository MUST contain exactly one integration directory under `custom_components/`
- **FR-002**: All integration files MUST be located in `custom_components/buderus_wps/`
- **FR-003**: Integration MUST include a `manifest.json` with all required HACS fields: `domain`, `documentation`, `issue_tracker`, `codeowners`, `name`, `version`
- **FR-004**: Repository MUST include a `hacs.json` configuration file in the root directory specifying the integration type
- **FR-005**: Repository MUST use semantic versioning in GitHub releases for version management
- **FR-006**: Documentation link in manifest MUST point to a valid, accessible URL with installation and usage instructions
- **FR-007**: Issue tracker link in manifest MUST point to a valid GitHub issues URL
- **FR-008**: Repository MUST have a descriptive README.md that explains the integration's purpose, features, and installation via HACS
- **FR-009**: Branding assets (icon, logo) SHOULD be submitted to home-assistant/brands repository

### Key Entities

- **manifest.json**: Integration metadata file containing domain, name, version, and links - already exists, may need verification
- **hacs.json**: HACS-specific configuration file defining integration behavior in the store - needs to be created
- **GitHub Release**: Tagged version with release notes for HACS version selection - needs to be created
- **Branding Assets**: Icon and logo files for submission to home-assistant/brands - needs to be created

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Integration passes HACS validation when added as a custom repository (0 errors)
- **SC-002**: All required manifest.json fields are present and valid
- **SC-003**: Users can install the integration via HACS in under 2 minutes
- **SC-004**: Users can upgrade to new versions via HACS when releases are published
- **SC-005**: Integration listing shows accurate version, documentation, and issue tracker links

## Assumptions

- The GitHub repository is publicly accessible (required for HACS)
- The integration is already functional and tested before HACS publishing
- The repository owner has access to create GitHub releases
- The manifest.json already contains most required fields (verified: domain, documentation, issue_tracker, codeowners, name, version all present)
- Branding submission to home-assistant/brands is optional and may take time for review

## Out of Scope

- Submission to HACS default repository (can be done after initial custom repository availability)
- Changes to integration functionality or Home Assistant entities
- Adding new sensors, switches, or controls
- Performance optimizations
- Integration-level code changes beyond metadata files
