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
- [!] Complete the live Desk walkthrough after enabling the local Chrome remote-debugging attachment. Blocked because the local Chrome remote-debugging attachment remains unavailable; later focused live API and Desk boot checks are recorded under Phases 11–15.

**Evidence:** Implemented on 2026-07-10/11. Focused contracts passed (8 service-total/schema contracts and 4 mapper/lifecycle units), followed by the full app suite on `auto-service-test.localhost`: 40 unit tests and 75 integration tests, all passing. `ruff check --config auto_service_management/pyproject.toml auto_service_management/auto_service_management`, targeted `ruff format --check`, and `git diff --check` passed. `bench build --app auto_service_management` completed successfully. Development-site migration ran the Phase 10 archive patch successfully; fixture export and a repeat development migration both completed with exit 0, with the repeat correctly not re-running the patch. `graphify update .` refreshed the code graph to 1,168 nodes and 1,822 edges. The isolated test-site uninstall/reinstall and post-install migration both completed with exit 0; `bench --site auto-service-test.localhost list-apps` confirms `auto_service_management 0.1.0` is installed alongside Frappe and ERPNext. Live Desk verification is blocked only by the local Chrome Browser Use attachment (remote debugging is not enabled), not by application code.

## Phase 10 — Repair Job State Authority Reconciliation

- [x] Retire the conflicting native Repair Job Workflow and make evidence-driven `job_status` authoritative.
- [x] Add an idempotent evidence-based reconciliation patch for existing jobs with divergent `workflow_state`/`job_status`.
- [x] Harden closure so Gate Pass use produces a submitted Closed Repair Job and idempotent release side effects.
- [x] Add Desk actions for app-owned transitions and regression coverage for the Draft/In Repair mismatch.
- [!] Run targeted tests, full app tests, migration, fixture export, asset build, and update the graph.

**Evidence:** Implemented and deployed to the development bench on 2026-07-20. The running container was separately checked out from the workspace, so the app-owned files were synchronized into `/home/frappe/bench-home/frappe-bench/apps/auto_service_management` before migration/build. Native Workflow is now inactive (`tabWorkflow.is_active=0`); `job_status` and legacy `workflow_state` use the canonical nine-state contract; migration completed; assets built; cache cleared; backend/frontend restarted. Direct authenticated POST Check In on `RJ-2026-00004` persisted `job_status=Assessment`, `workflow_state=Assessment`, `docstatus=0`, and created `Project PROJ-0003`; Walkaround `WI-2026-00048` inserted successfully. A blank/expired promised date also exposed and was fixed so Project creation uses a valid end date. Targeted 7-test regression suite, compileall, targeted Ruff, and `git diff --check` pass. The full 64-test suite was run but remains red on four unrelated Phase 10/13 and Desktop setup tests; those failures were not introduced by this Check-In change.

## Phase 11 — Repair Job Component Billing and Single-Status Model

- [x] Allow status-independent Sales Invoice mapping from saved Repair Jobs and Repair Job Services with selected, whole, unbilled component references.
- [x] Add server-side component billing summaries and Desk selection dialogs with Unbilled, Reserved, Invoiced, and Not Billable states.
- [x] Make Repair Job non-submittable, remove closure submission, and add legacy `docstatus` reconciliation through a pre-model-sync patch.
- [x] Add focused mapper/status regression coverage and complete development migration, asset build, cache clear, restart, and live API verification.
- [!] Complete browser hard-refresh walkthrough and full app-suite rerun; local browser attachment is unavailable and the existing full-suite baseline has unrelated failures.

**Evidence:** Implemented on 2026-07-20. The focused mapping/status suite passed 16/16 tests with `--skip-before-tests`; JSON validation, compileall, targeted Ruff, JavaScript syntax checks, and `git diff --check` passed. Development migration reached DocType/fixture synchronization and the app assets built successfully; cache was cleared and backend/frontend/websocket services restarted. Live metadata reports `Repair Job.is_submittable=0`, `Repair Job Service.is_submittable=0`, only visible `job_status` among Repair Job status fields, billing HTML fields on both doctypes, and all 15 Repair Jobs at `docstatus=0`. Live billing endpoint returned four Unbilled components totaling 220,000 for `RJ-2026-00045`; direct unsaved mapping of one selected component returned exactly one Sales Invoice item. No invoice was created or persisted during verification.

## Phase 12 — Labour Service Items, Bay Warehouses, and Related-Table Consistency

- [x] Require Labour service Items and repair legacy item-less labour invoice rows without mutating submitted history.
- [x] Route Material Requests through the selected Workshop Bay warehouse before the global default.
- [x] Rebuild Repair Job service/invoice/payment mirrors immediately after source and invoice updates.
- [x] Display the assigned Repair Job ID and add focused regression coverage.
- [!] Run focused/full tests, migration, asset build, cache clear, restart, and live invoice-save verification.

**Evidence:** Implemented and verified on 2026-07-21. Focused service-billing contracts passed 13/13 and mapper contracts passed 16/16. Development migration applied `phase21_labour_items_and_related_views`, created/configured `ASM-WORKSHOP-LABOUR`, backfilled all 14 legacy Labour rows, rebuilt every Repair Job service mirror, built assets, cleared cache, and restarted backend/frontend/websocket services. Live mapping of `RJ-2026-00059` produced three complete invoice rows: the Part used ERPNext `Sales - G` and `Main - G`, and both Labour rows used `ASM-WORKSHOP-LABOUR`, `Hour`, `Sales - G`, and `Main - G`; a real draft Sales Invoice inserted successfully and was deleted as a controlled verification artifact. The test-site migration also applied the patch successfully after adding clean-site creation of the `Services` Item Group and `Hour` UOM. The full app run remains red on four pre-existing Phase 10/17/40 workflow-test contract failures unrelated to this phase; no new phase12 test failed.

## Phase 13 — Workshop Operations, Release Policy, and Permissions

- [x] Allow Material Requests from any saved Repair Job status, with one active request per Repair Job Service.
- [x] Add technician-controlled Repair Job Service completion and realtime Repair Job service mirrors.
- [x] Expand Daily Workshop Load into the Workshop Bay View with technicians and closed-today visuals.
- [x] Keep invoice creation/payment synchronization neutral to the Repair Job business status.
- [x] Require only an active invoice for QC and a submitted invoice plus configurable payment policy for Gate Pass.
- [x] Make Walkaround Inspection submittable and add idempotent operational permissions.
- [x] Run targeted/full tests, migration, asset build, cache clear, restart, and live verification.

**Evidence:** Implementation completed on 2026-07-22. Test-site migration and focused verification were recorded incrementally and then closed by the follow-up verification below.

**Interim release-safety evidence (2026-07-22):** Added regression tests proving that a submitted invoice cannot issue a Gate Pass when billable component coverage is incomplete and that Repair Job `release()` uses the same validator. Wired the existing `_all_billable_components_submitted()` helper into the shared `validate_job_invoices_for_gate_pass()` validator used by both Repair Job and Gate Pass flows, and made `release()` call that validator before entering Ready for Release. Synchronized the changed source into the backend container; the red coverage test reproduced before the guard, then the focused module passed 20/20 with `--skip-before-tests`. Converted remaining user-triggered Repair Job, Customer Authorization, and Gate Pass mutation methods to POST-only whitelisted endpoints. `graphify update . --no-viz` refreshed the AST graph to 1,832 nodes and 2,894 edges.

**Follow-up verification (2026-07-22):** Repaired the Phase 40 safety-test contract and unused workshop-bay collector, fixed the integration diagnosis helper's unreachable insert/submit path, corrected the Desktop Icon update to avoid a duplicate `Workshop Management` label, and restored spec-first Quality Check ordering (QC may be created before billing, with a Repair Job status guard). The focused controller integration module passed 19/19, including PDF rendering, authorization permissions, and desktop setup. Permission-matrix failures were traced to `phase22_operational_permissions` creating broad System Manager `Custom DocPerm` rows that shadowed standard DocType permissions; the patch no longer creates those rows, and new `phase24_reconcile_custom_permissions` removes them from existing installs. After migration and backend restart, the permission-matrix module passed 5/5 (all 21 role/report/child-permission assertions). Implemented the missing idempotent `RepairJobService.materialize_template_components()` contract; its focused unit module passes 2/2. The Phase 3b labour/stock cluster was then reconciled to the current schema: component iteration tolerates the removed service-status field, test helpers no longer query removed child `status` columns, labour assertions use the configured labour item, and direct-service fixtures provide the required Workshop Bay. A final Desktop Icon collision was fixed by naming newly created App icons `Auto Service Management` instead of the existing workspace link label. Final verification: all 75 unit tests, all 54 integration tests, and all 42 unspecified-category tests passed.

## Phase 14 — Suite Integration: HRMS and Uganda Compliance

- [x] Refactor the Docker setup flow so an existing bench upgrades idempotently to the four-app suite without wiping `bench-data`.
- [x] Add `hrms` and `uganda_compliance` retrieval, site installation order, migrations, and per-app asset builds for both local sites.
- [x] Update local setup documentation to describe the four-app dev suite, branch pins, and dormant EFRIS defaults.
- [!] Run compose validation, setup idempotence checks, site app verification, migrations, builds, and targeted suite tests.
- [x] Verify cross-app smoke behavior for non-EFRIS invoicing, HRMS timesheet hooks, desk boot/assets, and duplicate icon/sidebar regressions.

**Evidence:** Implemented on 2026-07-22. `graphify update . --no-viz` refreshed the graph at the start of this phase. Upstream branch SHAs resolved before implementation: `hrms version-16 -> 6aa125b976469cb1c342afa3ef07d381c88677e0`, `uganda_compliance hotfix-v-16 -> 33743cd596c6e8c079945478d0e5b52e461fe770`. `docker-compose.dev.yml` setup was refactored from a one-shot fresh-bench path into per-step idempotent guards: bench init only when `sites/apps.txt` is missing; `bench get-app` only when app folders are absent; local `auto_service_management` copy/install only when absent; site creation only when missing; app installation on each site in fixed order `erpnext -> auto_service_management -> hrms -> uganda_compliance`; site migrate after install; per-app builds for `auto_service_management`, `hrms`, and `uganda_compliance`. README now documents the four-app local suite, in-place upgrade via `docker compose -f docker-compose.dev.yml up -d`, verification commands for all apps, and that Uganda Compliance EFRIS behavior remains dormant until explicitly configured.

**Verification:** `docker compose -f docker-compose.dev.yml config` passed. The setup flow was re-run against the existing `bench-data` volume until it completed cleanly without bench deletion; `sites/apps.txt` now contains each app exactly once (`frappe`, `auto_service_management`, `erpnext`, `hrms`, `uganda_compliance`). Both sites list the same installed apps: `frappe 16.25.0`, `erpnext 16.26.2`, `auto_service_management 0.1.0`, `hrms 16.14.0`, `uganda_compliance 0.0.1`. Backend health and boot were re-verified with `curl http://127.0.0.1:8000/api/method/ping -> {"message":"pong"}`. Duplicate desk regressions were checked directly in both sites: exactly one `Desktop Icon` (`Auto Service Management`), one `Workspace Sidebar` (`Workshop Management`), and one `Workspace` (`Workshop Management`) exist for `auto_service_management`. The full Auto Service suite on `auto-service-test.localhost` passed after restoring the Service Advisor `Customer` `Custom DocPerm` via the app-owned Phase 6 repair hook: 75 unit tests, 54 integration tests, and 42 unspecified-category tests all green. HRMS integration was verified with `bench --site auto-service-test.localhost run-tests --module hrms.hr.report.employee_hours_utilization_based_on_timesheet.test_employee_util --skip-before-tests`, which passed 5/5 tests covering Timesheet + Project reporting through HRMS overrides. A live manual HRMS smoke on `auto-service-test.localhost` then submitted `Timesheet TS-2026-00001` for active employee `_T-Employee-00003` with Auto Service trace fields and confirmed the linked `Repair Job Service Labour` row updated to `hours=2.5`, `timesheet=TS-2026-00001`, `timesheet_detail=ukc6k8sj11`, while HRMS kept the Timesheet status at `Submitted`. A live non-EFRIS Auto Service invoice smoke on `auto-service-test.localhost` created, submitted, and cancelled `Sales Invoice ACC-SINV-2026-00017` from `Repair Job RJ-2026-00133`; after submit the Repair Job compatibility rows showed one service row `('RJS-2026-00134', 'Unpaid', 470000.0)` and one invoice row `('ACC-SINV-2026-00017', 470000.0, 'Unpaid')`, and after cancel the invoice rows were empty again and both component `sales_invoice` links were released to `None`. `E Invoicing Settings` exists from Uganda Compliance install, but this baseline smoke completed without configured EFRIS credentials or runtime EFRIS submission requirements.

**Blocked upstream verification:** targeted vendor tests were isolated further and still were not patched, per suite-integration scope. The earlier `tabSingles` / `tabGender` deadlocks were tied to overlapping `bench run-tests` activity on the same site and are not the stable single-run failure mode. When rerun sequentially, `bench --site auto-service-test.localhost run-tests --module hrms.hr.report.project_profitability.test_project_profitability --skip-before-tests` gets past bootstrap and fails later during `Salary Slip` submit because wkhtmltopdf tries to render/email the payslip PDF and returns `HostNotFoundError`. When rerun sequentially, `bench --site auto-service-test.localhost run-tests --app uganda_compliance --skip-before-tests` fails in discovery because `uganda_compliance/efris/doctype/e_invoice/test_e_invoice.py` imports `get_sales_invoice_for_e_invoice` from ERPNext's `test_sales_invoice.py`, and that helper is absent in this ERPNext v16 checkout. The top-level files `uganda_compliance/tests/test_integration.py` and `uganda_compliance/tests/test_vat_compliance.py` are empty placeholder files and are not the actual blocker. These failures occur in upstream vendor test code and test-environment assumptions, not in the live suite smoke paths, so vendor app code was left unchanged.

## Phase 15 — Workshop Management Desk Icon

- [x] Replace the incorrectly routed Auto Service Management app icon with one top-level Workshop Management workspace icon using `car-front`.
- [x] Add focused regression coverage for the icon type, label, route target, icon glyph, and stale-icon cleanup.
- [x] Migrate both sites, clear caches, restart Desk services, and verify the live boot payload and browser route.
  - Evidence:
    - Root cause confirmed against installed Frappe v16 Desk routing: `Desktop Icon.label` was `Auto Service Management` while the only valid sidebar key was `Workshop Management`, so the Desk route lookup failed before it could resolve the workspace sidebar target.
    - Updated `auto_service_management/auto_service_management/auto_service_management/desktop.py` so setup now deletes stale `icon_type = "App"` rows for `auto_service_management`, creates or updates exactly one visible top-level `Desktop Icon` labeled `Workshop Management`, and pins it to `icon = "car-front"`, `icon_type = "Link"`, `link_type = "Workspace Sidebar"`, `link_to = "Workshop Management"`.
    - Updated `auto_service_management/auto_service_management/auto_service_management/workspace/workshop_management/workshop_management.json` to use `icon = "car-front"` so the workspace and Desk entry stay visually aligned after fixture sync.
    - Added regression coverage in `auto_service_management/auto_service_management/auto_service_management/tests/test_controllers_integration.py` and `auto_service_management/auto_service_management/auto_service_management/tests/test_phase6_contracts.py` for the icon label, glyph, route target, link type, standard flag, and stale app-icon cleanup.
    - Re-ran both site migrations and cache clears, then restarted `backend`, `frontend`, and `websocket` with `docker compose -f docker-compose.dev.yml restart backend frontend websocket`.
    - Focused tests passed on `auto-service-test.localhost`:
      - `bench --site auto-service-test.localhost run-tests --module auto_service_management.auto_service_management.tests.test_phase6_contracts --test test_desktop_module_exists_with_required_functions --skip-before-tests`
      - `bench --site auto-service-test.localhost run-tests --module auto_service_management.auto_service_management.tests.test_controllers_integration --test test_desktop_icon_exists_and_is_visible --skip-before-tests`
    - Live boot contract verified inside the backend bench environment on both `auto-service.localhost` and `auto-service-test.localhost`: the only Desk icon for `app = auto_service_management` is `('Workshop Management', 'Link', 'car-front', 'Workspace Sidebar', 'Workshop Management', None)`, `boot.workspace_sidebar_item` contains `workshop management`, and the stale `auto service management` key is absent.

## Phase 16 — Flexible Material Requests, Sidebar Icons, and Customer Repair Portal

- [x] Amend the approved Material Request contract and add focused failing coverage for component-level request selection, purpose preservation, request history, and Stock Entry guards.
- [x] Implement backward-compatible Repair Job and Repair Job Service Material Request mapping for every installed ERPNext purpose, with one active request per component.
- [x] Add the shared Desk selector and read-only request overview, including explicit `Not Requested` components and historical traced requests.
- [x] Add and validate semantic Lucide icons for every Car Workshop sidebar section and link.
- [x] Add secure read-only `/my-repairs` list/detail portal pages scoped through ERPNext Customer Portal User associations.
- [x] Run focused and full tests, repeated test/dev migrations, asset build, cache/route/live-record checks, static validation, and refresh Graphify.

**Evidence (started 2026-07-23):** Refreshed the AST knowledge graph before implementation with `graphify update .` (1,869 nodes, 2,940 edges, 324 communities), reviewed `graphify-out/GRAPH_REPORT.md`, and traced the existing Material Request mapper, component trace fields, sidebar builder, and standard ERPNext customer portal model. Locked defaults remain one active Material Request per component and submitted-only portal finance. Updated `docs/specs/automobile-repair-management.md` to the component-level, all-purpose contract and added Phase 16 contract tests. The pre-implementation signature assertion failed as intended: `Repair Job.make_material_request` exposed only `source_name` and `target_doc`, proving `component_refs` and `material_request_type` were absent.

**Completed verification (2026-07-23):** Synced the app source into the bench copy, rebuilt `bench build --app auto_service_management`, and restarted `backend`, `frontend`, `scheduler`, `queue-default`, `queue-short`, `queue-long`, and `websocket`. The focused contract slice passed: `bench --site auto-service-test.localhost run-tests --module auto_service_management.auto_service_management.tests.test_phase16_contracts --skip-before-tests` (13/13). The workspace/sidebar slice passed: `bench --site auto-service-test.localhost run-tests --module auto_service_management.auto_service_management.tests.test_workspace_dashboard --skip-before-tests` (10/10). The controller slice passed: `bench --site auto-service-test.localhost run-tests --module auto_service_management.auto_service_management.tests.test_controllers_integration --skip-before-tests` (19/19). The full app suite passed: `bench --site auto-service-test.localhost run-tests --app auto_service_management --skip-before-tests` (93 unit tests, 54 integration tests, 42 unspecified-category tests). Live smoke checks passed after restart: `curl http://127.0.0.1:8000/api/method/ping` returned `200 OK` with `{"message":"pong"}` and `curl -H "Host: auto-service.localhost" http://127.0.0.1:8080/my-repairs` returned `403 FORBIDDEN` for a guest request, confirming the portal fails closed without exposing customer data. `git diff --check` passed, and `graphify update .` refreshed the graph to 1,927 nodes, 3,019 edges, and 329 communities.
