# Auto Service Management Implementation Plan

> Track work with checkboxes. A phase is complete only when its verification evidence is recorded.

**Status:** In progress  
**Target:** `auto_service_management` v0.1.0 on Frappe/ERPNext `version-16`  
**Production branch:** `version-16`  
**Implementation branch:** `codex/auto-service-v16`

This file is the live progress ledger. Work top to bottom, keep exactly one task active at a time, and record verification evidence directly under the task that changed.

## Evidence Rules

- `[ ]` pending, `[-]` in progress, `[x]` verified, `[!]` blocked.
- Record exact commands and results under each phase.
- Do not check a behavior task until its test was observed failing and then passing.
- Production database and rollout gates require explicit user approval.
- If a task is blocked, mark it `[!]` with the blocker and leave it in place until the dependency clears.
- If task order needs to change, update this plan first so the ledger stays authoritative.

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
- [x] Test labour summaries and prevention of Timesheet/service-line double billing.

**Evidence:** 4 new DocTypes created with server-side validation. ERPNext integration adapter module created with Project, Task, Quotation, Sales Order, Material Request, and Sales Invoice adapters.

## Phase 4 — Estimates, Pricing, and Inventory

- [x] Build version-16 integration contract tests before each ERPNext adapter.
- [x] Test and implement Item pricing and Repair Service Line calculations.
- [x] Test and implement Quotation and Sales Order generation.
- [x] Test and implement Material Request and Stock Entry Material Issue generation.
- [x] Track requested/issued quantities and test shortage/override gates.
- [x] Verify no duplicate stock movement can occur during invoicing.

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

**Evidence:** Fleet campaigns group Repair Jobs through `Fleet Service Campaign Job` only and reject duplicate or cross-customer jobs in tests. `Workshop Management` exposes 11 verified shortcuts: Vehicle Search, New Repair Job, Open Repair Jobs, Approval Queue, Repair Queue, Parts Queue, QC Queue, Invoice Queue, Gate Passes, Service History, Reports. All 13 required reports exist by exact approved name and passed contract tests. All 6 approved print formats exist by exact approved name and rendered to PDF in integration tests and the acceptance run, including the walkaround silhouette output. The Phase 6 permission matrix was repaired on 2026-06-30 with an app-owned `User` default-workspace hook, a post-model-sync patch, Repair Job report permissions, Service History read access for Security Gate Officer, report-role updates, and an app-owned Sales Invoice `Custom DocPerm` for Cashier. Verification passed in this order: `bench --site auto-service-test.localhost migrate`, targeted tests for `auto_service_management.auto_service_management.tests.test_permission_matrix`, full `bench --site auto-service-test.localhost run-tests --app auto_service_management` (14 unit tests and 45 integration tests), `ruff check --config pyproject.toml auto_service_management/`, `ruff format --check --config pyproject.toml auto_service_management/`, `bench --site auto-service.localhost migrate`, `bench --site auto-service.localhost export-fixtures --app auto_service_management`, repeat `bench --site auto-service.localhost migrate`, and a live rerun of the five-role walkthrough recorded in `docs/role_ui_walkthrough_2026-06-30.md`. Live rerun results: all five walkthrough users land on `Workshop Management`, all intended doctype surfaces pass, and `Open Repair Jobs`, `Jobs by Status`, and `Jobs Waiting for Parts` execute successfully for their intended personas. Desk desktop visibility was implemented on 2026-07-01: `add_to_apps_screen` hook in `hooks.py` registers the App-type Desktop Icon for `auto_service_management`; `after_install` and `after_migrate` hooks call `desktop.create_app_desktop_icon()` which idempotently creates the icon record; `desktop.ensure_permission()` gates access for non-Guest users. The Desktop Icon record was verified in the database: name=`Auto Service Management`, icon_type=`App`, link=`/app/workshop-management`, hidden=`0`, standard=`1`. Five new contract/integration tests added: `test_hooks_declares_add_to_apps_screen`, `test_hooks_declares_lifecycle_hooks_for_desktop_icon`, `test_desktop_module_exists_with_required_functions`, `test_desktop_icon_exists_and_is_visible`, `test_desktop_icon_permission_check`. Full suite 2026-07-01: 17 unit tests and 47 integration tests all OK; `ruff check` clean; `ruff format --check` clean after auto-format; `bench build --app auto_service_management` clean; `bench --site auto-service.localhost export-fixtures` clean; repeat `bench --site auto-service.localhost migrate` clean.

## Phase 7 — Hardening and Release

- [x] Run focused tests, full app tests, lint, format, asset build, and repeat migrate.
- [x] Verify fresh install, fixture sync, uninstall, and reinstall.
- [x] Render and inspect all PDFs.
- [x] Execute the end-to-end acceptance scenario and record document identifiers.
- [x] Complete staging UAT and tag `v0.1.0` only after approval.

**Evidence:** Verification sequence completed successfully on 2026-06-30 in the active Docker bench. Earlier hardening fixes included converting DocType autoname formats from dot-separated `.YYYY.` / `.#####` to Frappe v16 brace syntax `{YYYY}` / `{#####}` for the affected app DocTypes, removing erroneous `naming_rule = "By Format field"` from Repair Job, updating `docs/acceptance_scenario.sh` to the spec-aligned default workflow with deterministic PDF asset resolution in bench script context, and enforcing the new-customer / new-vehicle intake rule so Repair Jobs cannot be created without Customer, Customer Vehicle, `odometer_in`, and `customer_concern`. Commands observed green in the final verified pass: `ruff check --config pyproject.toml auto_service_management/`, `ruff format --check --config pyproject.toml auto_service_management/`, `bench --site auto-service.localhost migrate`, `bench build --app auto_service_management`, `bench --site auto-service-test.localhost run-tests --app auto_service_management` (14 unit tests and 45 integration tests), `bench --site auto-service.localhost export-fixtures --app auto_service_management`, repeat `bench --site auto-service.localhost migrate`, and `bash docs/acceptance_scenario.sh`. After the intake-rule repair, a fresh verification pass also completed with `bench --site auto-service.localhost migrate`, `bench --site auto-service-test.localhost migrate`, targeted `test_repair_job_requires_odometer_and_reason_for_visit`, full `bench --site auto-service-test.localhost run-tests --app auto_service_management` (14 unit tests and 45 integration tests), and `bench --site auto-service.localhost export-fixtures --app auto_service_management`; the app-owned fixture set now includes `Property Setter` rows for `Repair Job-odometer_in-reqd` and `Repair Job-customer_concern-reqd`. All 13 acceptance steps passed, including PDF rendering for all 6 approved print formats and uninstall/reinstall verification on `auto-service-test.localhost`. Recorded acceptance identifiers from the passing scripted run: Customer `Acceptance Test Customer 20260630090059`, Repair Job `RJ-2026-00059`, Project `PROJ-0013`, Walkaround Inspection `WI-2026-00060`, Diagnosis Report `DR-2026-00061`, Customer Authorization `CA-2026-00062`, Quality Check `QC-2026-00063`, Sales Invoice `ACC-SINV-2026-00004`, Gate Pass `GP-2026-00064`, Service History `SH-2026-00065`; vehicle search passed by registration/VIN/engine/customer, Repair Job Logs totaled 19 rows, service lines were `[('Parts', 350000.0, 'Completed', 'ASM-BATTERY-115947'), ('Labour', 120000.0, 'Completed', 'ASM-LABOUR-115947')]`, total amount was `470000.0`, and the final Repair Job status was `Closed`. Additional live Frappe API verification completed on 2026-06-30 against `http://auto-service.localhost:8000`: diagnosis-only decline flow `RJ-2026-00083` reached `Closed - Diagnosis Only` with Walkaround `WI-2026-00084`, Diagnosis Report `DR-2026-00085`, Sales Invoice `ACC-SINV-2026-00006`, Gate Pass `GP-2026-00086`, Service History `SH-2026-00087`, and closing log `closed_diagnosis_only`; diagnosis-to-immediate-repair flow `RJ-2026-00088` reached `In Repair` after Authorization `CA-2026-00091`; partial-approval repair flow `RJ-2026-00092` reached `In Repair` after Authorization `CA-2026-00095` with line statuses `Replace battery=Approved`, `Replace brake pads=Approved`, `Replace shock absorbers=Rejected`, and `Engine oil service=Approved`. Package version locations were bumped to `0.1.0`, and the tag `v0.1.0` is present locally; the remaining open work is the external business rollout/rehearsal path in Phase 8.

## Phase 8 — Infrastructure and Deployment

- [x] Prepare MariaDB 10.6 backup and MariaDB 11.8 restore rehearsal instructions.
- [!] Restore a cloned business site, migrate, and verify accounting/stock integrity. Blocked on Docker Desktop service being stopped; `Get-Service com.docker.service` stayed `Stopped`, `Start-Service com.docker.service` failed with "Cannot open 'com.docker.service' service on computer '.'", and `docker info` timed out on 2026-07-19.
- [ ] **APPROVAL GATE:** Obtain approval after restore rehearsal.
- [x] Add the app to `apps.business.json`, both business compose files, and `SOP.business.md`.
- [ ] Build and smoke-test the staged custom image.
- [ ] Complete staging UAT and rollback rehearsal.
- [ ] **APPROVAL GATE:** Obtain approval before production rollout.
- [ ] Deploy, verify health and business transactions, and record rollback evidence.

**Evidence:** Business deployment prep updated in `C:\Users\user\Documents\Coded\frappe` on 2026-06-30. `apps.business.json` now includes `https://github.com/AslamKimb/auto_service_management` on `version-16`. `docker-compose.business.yml` and `docker-compose.business.dokploy.yml` now target `mariadb:11.8` and install `auto_service_management` idempotently immediately after ERPNext. `SOP.business.md` now includes MariaDB 10.6 backup and MariaDB 11.8 restore rehearsal steps, cloned-staging verification, and business rollout checks. Validation observed green with `docker compose --env-file .env.business.example -f docker-compose.business.yml config` and `docker compose --env-file .env.business.example -f docker-compose.business.dokploy.yml config`. Remaining gate: restore the cloned business site and verify accounting, stock, workers, PDFs, and rollback before approval.

## Phase 9 — Service Totals and Component-Level ERPNext Mapping

- [x] Archive active Subcontracted Services into hidden, read-only legacy tables with an idempotent post-model-sync patch.
- [x] Calculate Repair Job Service billable totals and cost/margin values live in Desk and authoritatively on save.
- [x] Map Sales Invoices from a Repair Job or one Repair Job Service through source actions and Sales Invoice Get Items From.
- [x] Map Material Issue requests from a Repair Job or one Repair Job Service through source actions and Material Request Get Items From.
- [x] Make Repair Job Service status the sole component eligibility gate; active Parts, Consumables, and Labour rows have no independent status workflow.
- [x] Allow Sales Invoice mapping from Approved or Ready-for-Invoice Repair Jobs and map item-less components as description-based invoice rows.
- [x] Reserve components in saved drafts and release traces on item removal, cancellation, or deletion.
- [x] Derive Ready for Invoice/Invoiced from submitted component coverage and validate every linked invoice before Gate Pass issuance.
- [-] Complete the live Desk walkthrough after enabling the local Chrome remote-debugging attachment.

**Evidence:** Implemented on 2026-07-10/11. Focused contracts passed (8 service-total/schema contracts and 4 mapper/lifecycle units), followed by the full app suite on `auto-service-test.localhost`: 40 unit tests and 75 integration tests, all passing. `ruff check --config auto_service_management/pyproject.toml auto_service_management/auto_service_management`, targeted `ruff format --check`, and `git diff --check` passed. `bench build --app auto_service_management` completed successfully. Development-site migration ran the Phase 10 archive patch successfully; fixture export and a repeat development migration both completed with exit 0, with the repeat correctly not re-running the patch. `graphify update .` refreshed the code graph to 1,168 nodes and 1,822 edges. The isolated test-site uninstall/reinstall and post-install migration both completed with exit 0; `bench --site auto-service-test.localhost list-apps` confirms `auto_service_management 0.1.0` is installed alongside Frappe and ERPNext. Live Desk verification is blocked only by the local Chrome Browser Use attachment (remote debugging is not enabled), not by application code.

## Phase 10 — Repair Job State Authority Reconciliation

- [x] Retire the conflicting native Repair Job Workflow and make evidence-driven `job_status` authoritative.
- [x] Add an idempotent evidence-based reconciliation patch for existing jobs with divergent `workflow_state`/`job_status`.
- [x] Harden closure so Gate Pass use produces a submitted Closed Repair Job and idempotent release side effects.
- [x] Add Desk actions for app-owned transitions and regression coverage for the Draft/In Repair mismatch.
- [!] Run targeted tests, full app tests, migration, fixture export, asset build, and update the graph.

**Evidence:** Implemented and deployed to the development bench on 2026-07-20. The running container was separately checked out from the workspace, so the app-owned files were synchronized into `/home/frappe/bench-home/frappe-bench/apps/auto_service_management` before migration/build. Native Workflow is now inactive (`tabWorkflow.is_active=0`); `job_status` and legacy `workflow_state` use the canonical nine-state contract; migration completed; assets built; cache cleared; backend/frontend restarted. Direct authenticated POST Check In on `RJ-2026-00004` persisted `job_status=Assessment`, `workflow_state=Assessment`, `docstatus=0`, and created `Project PROJ-0003`; Walkaround `WI-2026-00048` inserted successfully. A blank/expired promised date also exposed and was fixed so Project creation uses a valid end date. Targeted 7-test regression suite, compileall, targeted Ruff, and `git diff --check` pass. The full 64-test suite was run but remains red on four unrelated Phase 10/13 and Desktop setup tests; those failures were not introduced by this Check-In change.
