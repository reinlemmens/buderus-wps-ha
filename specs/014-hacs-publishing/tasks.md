# Tasks: HACS Publishing

**Input**: Design documents from `/specs/014-hacs-publishing/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not applicable - this feature creates configuration/metadata files only (no executable code).

**Organization**: Tasks grouped by user story. US1 and US2 share implementation (both enabled by same metadata).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Verification)

**Purpose**: Verify prerequisites and existing assets before creating new files

- [x] T001 Verify manifest.json has all required HACS fields in custom_components/buderus_wps/manifest.json
- [x] T002 [P] Verify documentation URL is accessible (https://github.com/reinlemmens/buderus-wps-ha)
- [x] T003 [P] Verify issue tracker URL is accessible (https://github.com/reinlemmens/buderus-wps-ha/issues)
- [x] T004 [P] Verify branding assets exist in custom_components/buderus_wps/branding/

**Checkpoint**: All prerequisites verified - can proceed with HACS configuration

---

## Phase 2: Foundational (HACS Configuration)

**Purpose**: Create core HACS configuration that enables US1 and US2

**⚠️ CRITICAL**: US1 and US2 cannot be tested until this phase is complete

- [x] T005 Create hacs.json with name and render_readme fields in /hacs.json
- [x] T006 Validate hacs.json is valid JSON using `python -c "import json; json.load(open('hacs.json'))"`

**Checkpoint**: HACS configuration ready - README and release can proceed

---

## Phase 3: User Story 1 & 2 - Install via HACS / View Information (Priority: P1, P2) 🎯 MVP

**Goal**: Users can install the integration via HACS and view metadata

**Independent Test**: Add repository as custom repository in HACS, verify validation passes and install works

### Implementation for User Stories 1 & 2

- [x] T007 [P] [US1] Add HACS badge to top of README.md
- [x] T008 [P] [US1] Add "Installation via HACS" section to README.md
- [ ] T009 [US1] Commit hacs.json and README changes with message "feat: add HACS support"
- [ ] T010 [US1] Push changes to GitHub main branch
- [ ] T011 [US1] Create GitHub release v1.0.0 matching manifest.json version
- [ ] T012 [US1] [US2] Test HACS validation by adding as custom repository in HACS
- [ ] T013 [US1] Test integration install flow via HACS
- [ ] T014 [US2] Verify metadata displays correctly (name, version, documentation link, issue tracker)

**Checkpoint**: US1 and US2 complete - integration installable and discoverable via HACS

---

## Phase 4: User Story 3 - Branding (Priority: P3, Optional)

**Goal**: Integration displays branded icon in Home Assistant UI

**Independent Test**: After branding PR is merged, verify icon appears in HA Integrations page

### Implementation for User Story 3

- [ ] T015 [US3] Fork home-assistant/brands repository
- [ ] T016 [US3] Create custom_integrations/buderus_wps/ directory in forked brands repo
- [ ] T017 [P] [US3] Copy icon.png (256x256) to brands repo custom_integrations/buderus_wps/
- [ ] T018 [P] [US3] Copy icon@2x.png (512x512) to brands repo custom_integrations/buderus_wps/
- [ ] T019 [US3] Submit PR to home-assistant/brands with integration description
- [ ] T020 [US3] Monitor PR for feedback and address review comments

**Checkpoint**: Branding PR submitted - awaiting review (async, may take days/weeks)

---

## Phase 5: Polish & Documentation

**Purpose**: Final cleanup and documentation updates

- [ ] T021 Update spec.md status from Draft to Complete
- [ ] T022 Update checklists/requirements.md with validation results
- [ ] T023 [P] Run quickstart.md validation checklist to confirm all steps work

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verification only
- **Foundational (Phase 2)**: Depends on Setup verification passing
- **US1 & US2 (Phase 3)**: Depends on Foundational (hacs.json must exist)
- **US3 (Phase 4)**: Can start after Phase 2, independent of US1/US2 completion
- **Polish (Phase 5)**: Depends on US1 & US2 completion (US3 optional)

### User Story Dependencies

- **User Story 1 (P1)**: Requires hacs.json + README + GitHub release
- **User Story 2 (P2)**: Same requirements as US1 (shared implementation)
- **User Story 3 (P3)**: Only requires icon assets (already created) - independent PR to external repo

### Critical Path

```
T001-T004 (Setup) → T005-T006 (hacs.json) → T007-T010 (README + Commit) → T011 (Release) → T012-T014 (Validation)
```

### Parallel Opportunities

- **Setup phase**: T002, T003, T004 can run in parallel
- **Phase 3**: T007, T008 can run in parallel (different README sections)
- **Phase 4**: T017, T018 can run in parallel (different files in brands repo)
- **US3 vs US1/US2**: US3 can be started independently after Phase 2

---

## Parallel Example: Phase 3

```bash
# These can run in parallel:
Task: "Add HACS badge to top of README.md"
Task: "Add Installation via HACS section to README.md"

# Then sequentially:
Task: "Commit hacs.json and README changes"
Task: "Push changes to GitHub"
Task: "Create GitHub release v1.0.0"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup verification
2. Complete Phase 2: Create hacs.json
3. Complete Phase 3: README + Release + Validation
4. **STOP and VALIDATE**: Test HACS installation
5. Feature is usable (branding is optional enhancement)

### Full Implementation

1. Complete MVP (US1 + US2)
2. Complete Phase 4: Submit branding PR (async)
3. Complete Phase 5: Documentation cleanup
4. Monitor branding PR for approval

### Time Estimate

- **MVP (US1 + US2)**: ~30 minutes (configuration + testing)
- **US3 (Branding)**: ~15 minutes to submit PR + async review time
- **Total active work**: ~45 minutes

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] labels: US1 (Install), US2 (View Info), US3 (Branding)
- US1 and US2 share implementation - both enabled by same configuration
- US3 is external PR to home-assistant/brands repo - tracked separately
- No automated tests needed - manual HACS validation is the test
- GitHub release is blocking for version selection in HACS
