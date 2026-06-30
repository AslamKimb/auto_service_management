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

**Evidence:** 5 commits on `codex/auto-service-v16`; all governance files present; verified 2026-06-29.

## Phase 1 — Reproducible v16 Development

- [x] Start Docker Desktop and confirm the official development container can run.
- [x] Establish a v16 bench and validate it with `ls apps/ sites/ Procfile`.
- [x] Enable developer mode.
- [x] Create `auto-service.localhost` and `auto-service-test.localhost`.
- [x] Install ERPNext on both sites.
- [x] Generate the app scaffold with approved metadata and `required_apps = ["erpnext"]`.
- [x] Install the app on both sites, migrate, build assets, and verify list-apps.

**Evidence:** frappe v16.24.3, erpnext v16.25.0, auto_service_management v0.0.1 installed. Both sites respond to ping. `bench --site auto-service.localhost migrate` completes. `apps.txt` corrected to frappe, erpnext, auto_service_management.

## Phase 2 — Domain and Control Foundation

- [x] Write failing unit tests for money, margin, transition, and credit-policy rules.
- [x] Implement pure domain services until unit tests pass.
- [x] Create and test Auto Service Settings, Customer Vehicle, Workshop Bay, Repair Job, Repair Service Line, Repair Job Override, and Repair Job Log.
- [x] Add roles, DocType permissions, row-level permission hooks, and filtered fixtures.
- [x] Add the Repair Job workflow and enforce all transitions server-side.
- [x] Verify fixture export, repeat migration, and role isolation.

**Evidence:** 13 tests passing. 7 custom roles created. Filtered fixtures in hooks.py with role_name filter (module column not available on Role in v16). Server-side state machine with 12 states. Migration completed successfully on both dev and test sites. `bench --site auto-service.localhost export-fixtures --app auto_service_management` and repeat migrate both passed on 2026-06-29/30.

## Phase 3 — Intake and Workshop Operations

- [x] Test and implement Customer Vehicle search.
- [x] Test and implement Repair Job naming and idempotent Project creation on check-in.
- [x] Test and implement Project Template Task creation and assignments.
- [x] Create and test Walkaround Inspection, Vehicle Damage Mark, Diagnosis Report, and Customer Authorization.
- [x] Extend Project, Task, and Timesheet Detail through filtered Custom Field fixtures.
- [ ] Test labour summaries and prevention of Timesheet/service-line double billing.

**Evidence:** 4 new DocTypes created with server-side validation. ERPNext integration adapter module created with Project, Task, Quotation, Sales Order, Material Request, and Sales Invoice adapters.

## Phase 4 — Estimates, Pricing, and Inventory

- [x] Build version-16 integration contract tests before each ERPNext adapter.
- [x] Test and implement Item pricing and Repair Service Line calculations.
- [x] Test and implement Quotation and Sales Order generation.
- [x] Test and implement Material Request and Stock Entry Material Issue generation.
- [ ] Track requested/issued quantities and test shortage/override gates.
- [ ] Verify no duplicate stock movement can occur during invoicing.

**Evidence:** Integration adapters for Quotation, Sales Order, Material Request, and Sales Invoice created. Pricing adapter fetches from ERPNext price lists. Items require validation through ERPNext.

## Phase 5 — QC, Billing, Release, and Closure

- [x] Create and test Quality Check and Road Test Report.
- [x] Test and implement Sales Invoice generation and status synchronization.
- [x] Test paid, allowed-credit, credit-limit-breach, and manager-override release paths.
- [x] Create and test Gate Pass issue/use actions and print data.
- [x] Test idempotent closure, Service History, and Customer Vehicle updates.

**Evidence:** Quality Check, Road Test Report, Gate Pass, and Service History DocTypes created with controllers. Gate Pass has issue/use workflow. Service History is idempotent (unique per Repair Job). Closure updates vehicle odometer and service date.

## Phase 6 — Fleet, Desk UX, Printing, and Reports

- [x] Create and test Fleet Service Campaign grouping independent jobs.
- [x] Add native Desk form actions, list indicators, dashboard links, and Workshop Management workspace.
- [x] Add and render-test six Jinja print formats and the vehicle silhouette asset.
- [x] Add all required reports with filters, explicit ordering, permission checks, and tests.
- [x] Perform role-based UI walkthroughs.

**Evidence:** Fleet campaigns group Repair Jobs through `Fleet Service Campaign Job` only and reject duplicate or cross-customer jobs in tests. `Workshop Management` exposes 11 verified shortcuts: Vehicle Search, New Repair Job, Open Repair Jobs, Approval Queue, Repair Queue, Parts Queue, QC Queue, Invoice Queue, Gate Passes, Service History, Reports. All 13 required reports exist by exact approved name and passed contract tests. All 6 approved print formats exist by exact approved name and rendered to PDF in integration tests and the acceptance run, including the walkaround silhouette output. The Phase 6 permission matrix was repaired on 2026-06-30 with an app-owned `User` default-workspace hook, a post-model-sync patch, Repair Job report permissions, Service History read access for Security Gate Officer, report-role updates, and an app-owned Sales Invoice `Custom DocPerm` for Cashier. Verification passed in this order: `bench --site auto-service-test.localhost migrate`, targeted tests for `auto_service_management.auto_service_management.tests.test_permission_matrix`, full `bench --site auto-service-test.localhost run-tests --app auto_service_management` (14 unit tests and 39 integration tests), `ruff check --config pyproject.toml auto_service_management/`, `ruff format --check --config pyproject.toml auto_service_management/`, `bench --site auto-service.localhost migrate`, `bench --site auto-service.localhost export-fixtures --app auto_service_management`, repeat `bench --site auto-service.localhost migrate`, and a live rerun of the five-role walkthrough recorded in `docs/role_ui_walkthrough_2026-06-30.md`. Live rerun results: all five walkthrough users land on `Workshop Management`, all intended doctype surfaces pass, and `Open Repair Jobs`, `Jobs by Status`, and `Jobs Waiting for Parts` execute successfully for their intended personas.

## Phase 7 — Hardening and Release

- [x] Run focused tests, full app tests, lint, format, asset build, and repeat migrate.
- [x] Verify fresh install, fixture sync, uninstall, and reinstall.
- [x] Render and inspect all PDFs.
- [x] Execute the end-to-end acceptance scenario and record document identifiers.
- [ ] Complete staging UAT and tag `v0.1.0` only after approval.

**Evidence:** Verification sequence completed on 2026-06-30 in the active Docker bench. Fixed DocType autoname formats from dot-separated `.YYYY.` / `.#####` to Frappe v16 brace syntax `{YYYY}` / `{#####}` for all 10 affected DocTypes (Repair Job, Customer Authorization, Diagnosis Report, Fleet Service Campaign, Gate Pass, Quality Check, Repair Job Override, Road Test Report, Service History, Walkaround Inspection). Also removed erroneous `naming_rule = "By Format field"` from Repair Job. Added assets-initialization patch to acceptance script for PDF rendering in bench script context. Commands observed green: `bench --site auto-service-test.localhost run-tests --app auto_service_management` (14 unit tests and 39 integration tests), `ruff check`, `ruff format --check`, `bench migrate`, `bench build`, `bench export-fixtures`, repeat `bench migrate`, and `bash docs/acceptance_scenario.sh`. All 13 acceptance steps passed including uninstall/reinstall on test site. Recorded acceptance identifiers: Customer `Acceptance Test Customer 20260630022151`, Repair Job `RJ-2026-00002`, Walkaround Inspection `WI-2026-00003`, Customer Authorization `CA-2026-00004`, Quality Check `QC-2026-00005`, Gate Pass `GP-2026-00006`, Service History `SH-2026-00007`, with 20 Repair Job Log rows, all 6 PDF formats rendered, and final Repair Job status `Closed`. Package version locations were bumped to `0.1.0`; staging UAT and tag creation remain approval-gated.

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
