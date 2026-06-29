# Auto Service Management Implementation Plan

> Track work with checkboxes. A phase is complete only when its verification evidence is recorded.

**Status:** In progress  
**Target:** `auto_service_management` v0.1.0 on Frappe/ERPNext `version-16`  
**Production branch:** `version-16`  
**Implementation branch:** `codex/auto-service-v16`

## Evidence Rules

- `[ ]` pending, `[-]` in progress, `[x]` verified, `[!]` blocked.
- Record exact commands and results under each phase.
- Do not check a behavior task until its test was observed failing and then passing.
- Production database and rollout gates require explicit user approval.

## Phase 0 — Repository Governance

- [x] Initialize Git on `version-16` and configure the public origin.
- [x] Add README, GPL-3.0 notice, `.gitignore`, and preserve `Automotive DMS.md` as research.
- [x] Add repository-specific `AGENTS.md`.
- [x] Add this trackable plan and the normalized specification.
- [x] Validate links, word counts, Markdown structure, Git status, branch, and remote.
- [ ] Commit the governance baseline and create the isolated implementation branch/worktree.

**Evidence:** `AGENTS.md` is 323 words; all seven expected files exist; headings, `version-16`, and the configured GitHub origin were verified on 2026-06-29.

## Phase 1 — Reproducible v16 Development

- [ ] Start Docker Desktop and confirm the official development container can run.
- [ ] Establish a v16 bench and validate it with `ls apps/ sites/ Procfile`.
- [ ] Enable developer mode.
- [ ] Create `auto-service.localhost` and `auto-service-test.localhost`.
- [ ] Install ERPNext on both sites.
- [ ] Generate the app scaffold with approved metadata and `required_apps = ["erpnext"]`.
- [ ] Install the app on both sites, migrate, build assets, and verify list-apps.
- [ ] Verify clean uninstall/reinstall on the test site.

**Evidence:** Pending.

## Phase 2 — Domain and Control Foundation

- [ ] Write failing unit tests for money, margin, transition, and credit-policy rules.
- [ ] Implement pure domain services until unit tests pass.
- [ ] Create and test Auto Service Settings, Customer Vehicle, Workshop Bay, Repair Job, Repair Service Line, Repair Job Override, and Repair Job Log.
- [ ] Add roles, DocType permissions, row-level permission hooks, and filtered fixtures.
- [ ] Add the Repair Job workflow and enforce all transitions server-side.
- [ ] Verify fixture export, repeat migration, and role isolation.

**Evidence:** Pending.

## Phase 3 — Intake and Workshop Operations

- [ ] Test and implement Customer Vehicle search.
- [ ] Test and implement Repair Job naming and idempotent Project creation on check-in.
- [ ] Test and implement Project Template Task creation and assignments.
- [ ] Create and test Walkaround Inspection, Vehicle Damage Mark, Diagnosis Report, and Customer Authorization.
- [ ] Extend Project, Task, and Timesheet Detail through filtered Custom Field fixtures.
- [ ] Test labour summaries and prevention of Timesheet/service-line double billing.

**Evidence:** Pending.

## Phase 4 — Estimates, Pricing, and Inventory

- [ ] Build version-16 integration contract tests before each ERPNext adapter.
- [ ] Test and implement Item pricing and Repair Service Line calculations.
- [ ] Test and implement Quotation and Sales Order generation.
- [ ] Test and implement Material Request and Stock Entry Material Issue generation.
- [ ] Track requested/issued quantities and test shortage/override gates.
- [ ] Verify no duplicate stock movement can occur during invoicing.

**Evidence:** Pending.

## Phase 5 — QC, Billing, Release, and Closure

- [ ] Create and test Quality Check and Road Test Report.
- [ ] Test and implement Sales Invoice generation and status synchronization.
- [ ] Test paid, allowed-credit, credit-limit-breach, and manager-override release paths.
- [ ] Create and test Gate Pass issue/use actions and print data.
- [ ] Test idempotent closure, Service History, and Customer Vehicle updates.

**Evidence:** Pending.

## Phase 6 — Fleet, Desk UX, Printing, and Reports

- [ ] Create and test Fleet Service Campaign grouping independent jobs.
- [ ] Add native Desk form actions, list indicators, dashboard links, and Workshop Management workspace.
- [ ] Add and render-test six Jinja print formats and the vehicle silhouette asset.
- [ ] Add all required reports with filters, explicit ordering, permission checks, and tests.
- [ ] Perform role-based UI walkthroughs.

**Evidence:** Pending.

## Phase 7 — Hardening and Release

- [ ] Run focused tests, full app tests, lint, format, asset build, and repeat migrate.
- [ ] Verify fresh install, fixture sync, uninstall, and reinstall.
- [ ] Render and inspect all PDFs.
- [ ] Execute the end-to-end acceptance scenario and record document identifiers.
- [ ] Complete staging UAT and tag `v0.1.0` only after approval.

**Evidence:** Pending.

## Phase 8 — Infrastructure and Deployment

- [ ] Prepare MariaDB 10.6 backup and MariaDB 11.8 restore rehearsal instructions.
- [ ] Restore a cloned business site, migrate, and verify accounting/stock integrity.
- [ ] **APPROVAL GATE:** Obtain approval after restore rehearsal.
- [ ] Add the app to `apps.business.json`, both business compose files, and `SOP.business.md`.
- [ ] Build and smoke-test the staged custom image.
- [ ] Complete staging UAT and rollback rehearsal.
- [ ] **APPROVAL GATE:** Obtain approval before production rollout.
- [ ] Deploy, verify health and business transactions, and record rollback evidence.

**Evidence:** Pending.
