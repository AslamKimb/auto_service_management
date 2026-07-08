# Graph Report - DMS  (2026-07-08)

## Corpus Check
- 120 files · ~43,297 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 791 nodes · 1052 edges · 140 communities (96 shown, 44 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 40 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `410bd7ad`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 121|Community 121]]
- [[_COMMUNITY_Community 122|Community 122]]
- [[_COMMUNITY_Community 123|Community 123]]
- [[_COMMUNITY_Community 124|Community 124]]
- [[_COMMUNITY_Community 125|Community 125]]
- [[_COMMUNITY_Community 126|Community 126]]
- [[_COMMUNITY_Community 127|Community 127]]
- [[_COMMUNITY_Community 128|Community 128]]
- [[_COMMUNITY_Community 129|Community 129]]
- [[_COMMUNITY_Community 130|Community 130]]
- [[_COMMUNITY_Community 131|Community 131]]
- [[_COMMUNITY_Community 132|Community 132]]
- [[_COMMUNITY_Community 133|Community 133]]
- [[_COMMUNITY_Community 134|Community 134]]
- [[_COMMUNITY_Community 135|Community 135]]
- [[_COMMUNITY_Community 136|Community 136]]
- [[_COMMUNITY_Community 137|Community 137]]
- [[_COMMUNITY_Community 138|Community 138]]
- [[_COMMUNITY_Community 139|Community 139]]

## God Nodes (most connected - your core abstractions)
1. `_create_repair_job()` - 38 edges
2. `RepairJob` - 31 edges
3. `Real-World Workflows — Auto Service Management` - 23 edges
4. `_get_or_create_customer()` - 20 edges
5. `_create_test_vehicle()` - 20 edges
6. `TestRepairJobWorkflowIntegration` - 20 edges
7. `run_report()` - 18 edges
8. `_insert_walkaround()` - 17 edges
9. `TestPhase6Contracts` - 17 edges
10. `_insert_diagnosis()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `execute()` --calls--> `run_report()`  [INFERRED]
  auto_service_management/auto_service_management/auto_service_management/report/corporate_credit_releases/corporate_credit_releases.py → auto_service_management/auto_service_management/auto_service_management/reporting/runner.py
- `execute()` --calls--> `run_report()`  [INFERRED]
  auto_service_management/auto_service_management/auto_service_management/report/daily_workshop_load/daily_workshop_load.py → auto_service_management/auto_service_management/auto_service_management/reporting/runner.py
- `execute()` --calls--> `run_report()`  [INFERRED]
  auto_service_management/auto_service_management/auto_service_management/report/gate_pass_register/gate_pass_register.py → auto_service_management/auto_service_management/auto_service_management/reporting/runner.py
- `execute()` --calls--> `run_report()`  [INFERRED]
  auto_service_management/auto_service_management/auto_service_management/report/jobs_by_status/jobs_by_status.py → auto_service_management/auto_service_management/auto_service_management/reporting/runner.py
- `execute()` --calls--> `run_report()`  [INFERRED]
  auto_service_management/auto_service_management/auto_service_management/report/jobs_waiting_for_parts/jobs_waiting_for_parts.py → auto_service_management/auto_service_management/auto_service_management/reporting/runner.py

## Communities (140 total, 44 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (33): IntegrationTestCase, _append_pending_labour_line(), _create_repair_job(), _insert_authorization(), _insert_diagnosis(), _insert_quality_check(), _insert_road_test(), _insert_walkaround() (+25 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (42): approve_service_lines(), authorize(), cancel(), check_in(), close(), close_as_diagnosis_only(), complete_diagnosis(), complete_service_lines() (+34 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (18): create_stock_entry_for_material_issue(), Create a Stock Entry (Material Issue) for requested Parts lines.  	Only covers, _create_test_vehicle(), _ensure_erpnext_basics(), _get_or_create_customer(), Create minimal ERPNext setup data if missing., Create or reuse a test Customer Vehicle., _add_labour_line() (+10 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (17): AutoServiceSettings, CustomerVehicle, Ensure no duplicate registration across the system., Document, FleetServiceCampaignJob, Immutable audit log. No writes or deletes allowed after insert., RepairJobLog, RepairJobOverride (+9 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (39): 10. Workspace Fixture Must Include `type` Field, 11. Workspace Fixture Must Include `app` Field, 12. Workspace Sidebar Entry Required for Desk Navigation, 1. Stale Redis Cache â€” Module Map Empty, 2. Desktop Icon Must Use Workspace Sidebar, 3. Editable Install on Python 3.14, 4. Browser Cache After Server Fixes, 5. PowerShell Gotchas (+31 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (6): get_auto_service_settings_configured_card_data(), FleetServiceCampaign, TestFleetServiceCampaign, TestPhase7HardeningContracts, TestWorkspaceDashboardContracts, UnitTestCase

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (22): _build_sidebar_link(), create_app_desktop_icon(), ensure_permission(), _ensure_workspace_app_field(), _ensure_workspace_sidebar(), _ensure_workspace_type_field(), _get_workspace_sidebar_items(), Desk desktop visibility for Auto Service Management.  Ensures an App-type Deskto (+14 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (21): create_material_request(), create_project_for_repair_job(), create_quotation(), create_sales_invoice(), create_sales_order(), create_tasks_from_template(), get_item_price(), get_settings() (+13 more)

### Community 8 - "Community 8"
Cohesion: 0.15
Nodes (12): assign_default_workspace(), backfill_default_workspace_for_existing_users(), Assign the workshop workspace when a qualifying user has no explicit default., Backfill the workshop workspace for qualifying users with a blank default., _roles_from_user_doc(), _should_assign_default_workspace(), _ensure_app_roles(), ensure_cashier_sales_invoice_custom_docperm() (+4 more)

### Community 9 - "Community 9"
Cohesion: 0.1
Nodes (19): I. Core ERP & Financial Modules (Main Navigation Sidebar), II. DMS (Dealer Management System) Module Features, III. Job Card Execution & Action Sidebar Features, Phase 1: Demand Generation (Determining What to Buy), Phase 1: Quoting (Estimation & Authorization), Phase 2: Deposits & Prepayments (Down Payments), Phase 2: Purchase Order (PO) Creation, Phase 3: Goods Receiving (Purchase Receipt / GRN) (+11 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (9): approve(), CustomerAuthorization, Authorization is needed before work can begin., Approved amount must be positive., Authorization is needed before work can begin., Warn if authorization is expired., Approved amount must be positive., Warn if authorization is expired. (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.12
Nodes (5): Test the Repair Job status state machine., All expected states must have defined transitions., Verify the complete lifecycle from Draft to Closed., Cancellation should be allowed from most active states., TestRepairJobWorkflow

### Community 12 - "Community 12"
Cohesion: 0.12
Nodes (15): Auto Service Management, code:bash (git clone https://github.com/your-org/auto_service_managemen), code:bash (# Windows (run PowerShell as Administrator)), code:bash (docker compose -f docker-compose.dev.yml up -d), code:bash (curl http://auto-service.localhost:8080/api/method/ping), code:bash (docker exec dms-backend-1 bench --site auto-service-test.loc), code:bash (docker exec -it dms-backend-1 bash), code:bash (docker exec dms-backend-1 bench build --app auto_service_man) (+7 more)

### Community 13 - "Community 13"
Cohesion: 0.13
Nodes (15): code:mermaid (graph TD), Final Practical Insight, Real-World Workflows — Auto Service Management, The Cast, The Main Records and How They Connect, The Numbers Behind the Stories, The Status Flow, The Workspace View Staff Actually Use (+7 more)

### Community 14 - "Community 14"
Cohesion: 0.15
Nodes (8): execute(), execute(), execute(), execute(), execute(), _build_filters(), _get_scoped_child_rows(), run_report()

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (14): Acceptance Scenario, Approved Architecture Corrections, Automobile Repair Management Specification, Configuration and Masters, Domain Model, ERPNext Integrations, Non-Functional Requirements, Objective and Boundaries (+6 more)

### Community 16 - "Community 16"
Cohesion: 0.23
Nodes (5): GatePass, issue(), Gate pass requires a submitted invoice., Gate pass requires a submitted invoice., use_gate_pass()

### Community 18 - "Community 18"
Cohesion: 0.26
Nodes (3): Ensure linked Repair Job is in an appropriate state., Ensure linked Repair Job is in an appropriate state., WalkaroundInspection

### Community 19 - "Community 19"
Cohesion: 0.17
Nodes (11): Auto Service Management Implementation Plan, Evidence Rules, Phase 0 — Repository Governance, Phase 1 — Reproducible v16 Development, Phase 2 — Domain and Control Foundation, Phase 3 — Intake and Workshop Operations, Phase 4 — Estimates, Pricing, and Inventory, Phase 5 — QC, Billing, Release, and Closure (+3 more)

### Community 20 - "Community 20"
Cohesion: 0.16
Nodes (9): App-type Desktop Icon for Auto Service Management must exist and not be hidden., App-type Desktop Icon for Auto Service Management must exist and not be hidden., ensure_permission must deny Guest and allow authenticated users., ensure_permission must deny Guest and allow authenticated users., ensure_permission must deny Guest and allow authenticated users., App-type Desktop Icon for Auto Service Management must exist and not be hidden., ensure_permission must deny Guest and allow authenticated users., App-type Desktop Icon for Auto Service Management must exist and not be hidden. (+1 more)

### Community 21 - "Community 21"
Cohesion: 0.18
Nodes (11): 10. Cancellation Before Completion, 2. First-Time Customer With a New Vehicle, 4. Partial Approval, 5. Fleet Service Campaign, 6. Walkaround Upsell, 7. Corporate Credit Release, 8. QC Failure and Rework, 9. Road-Test-Required Job (+3 more)

### Community 22 - "Community 22"
Cohesion: 0.29
Nodes (3): DiagnosisReport, Diagnosis can only happen after check-in., Diagnosis can only happen after check-in.

### Community 24 - "Community 24"
Cohesion: 0.32
Nodes (6): _ensure_erpnext_basics(), _get_or_create_test_customer(), Create or reuse a test Customer for vehicle tests., Two vehicles with the same VIN should not coexist., Create minimal ERPNext setup data if missing., TestCustomerVehicle

### Community 25 - "Community 25"
Cohesion: 0.25
Nodes (7): Conclusion, Global Finding, Goal, Method, Phase 6 Role UI Walkthrough — 2026-06-30, Role Results, Verification Source

### Community 26 - "Community 26"
Cohesion: 0.29
Nodes (6): Auto Service Management, code:bash (cd $PATH_TO_YOUR_BENCH), code:bash (cd apps/auto_service_management), Contributing, Installation, License

### Community 28 - "Community 28"
Cohesion: 0.33
Nodes (6): 3. Diagnosis Only, code:text (Draft -> Checked In -> Walkaround Inspection -> Diagnosis ->), Status journey, Use Case 8: The Quality Reject — Rework Required, What happens, What the system enforces

### Community 29 - "Community 29"
Cohesion: 0.33
Nodes (6): 1. Normal Walk-In Repair, code:text (Draft -> Checked In -> Walkaround Inspection -> Diagnosis ->), Status journey, Use Case 3: Diagnosis Only — "Just Tell Me What's Wrong", What happens, What the system enforces

### Community 30 - "Community 30"
Cohesion: 0.33
Nodes (6): code:text (Draft), Status journey, The Core Status Journey, Use Case 1: The Normal Walk-In Repair, What happens, What the system enforces

### Community 31 - "Community 31"
Cohesion: 0.4
Nodes (4): hooks.py must declare after_install and after_migrate to ensure Desktop Icon exi, hooks.py must declare lifecycle hooks that run the full desktop setup., hooks.py must declare lifecycle hooks that run the full desktop setup., hooks.py must declare lifecycle hooks that run the full desktop setup.

### Community 32 - "Community 32"
Cohesion: 0.4
Nodes (4): hooks.py must declare add_to_apps_screen so Frappe creates an App-type Desktop I, hooks.py must declare add_to_apps_screen so Frappe creates an App-type Desktop I, hooks.py must declare add_to_apps_screen so Frappe creates an App-type Desktop I, hooks.py must declare add_to_apps_screen so Frappe creates an App-type Desktop I

### Community 33 - "Community 33"
Cohesion: 0.4
Nodes (4): desktop.py must exist and export create_app_desktop_icon and ensure_permission., desktop.py must exist and export create_app_desktop_icon and ensure_permission., desktop.py must exist and export create_app_desktop_icon and ensure_permission., desktop.py must exist and export create_app_desktop_icon and ensure_permission.

### Community 37 - "Community 37"
Cohesion: 0.67
Nodes (3): Use Case 4: Partial Approval — "Fix This, Not That", What happens, What the system enforces

### Community 38 - "Community 38"
Cohesion: 0.67
Nodes (3): Use Case 2: First-Time Customer, New Vehicle, What happens, What's different

### Community 39 - "Community 39"
Cohesion: 0.67
Nodes (3): Use Case 5: The Corporate Fleet — Batch Service, What happens, What the system enforces

### Community 40 - "Community 40"
Cohesion: 0.67
Nodes (3): Use Case 9: The Diagnostic Dilemma — Road Test Required, What happens, What the system enforces

### Community 41 - "Community 41"
Cohesion: 0.67
Nodes (3): Use Case 10: The Angry Customer — Cancellation Mid-Work, What happens, What the system enforces

## Knowledge Gaps
- **261 isolated node(s):** `Permission check for the ``add_to_apps_screen`` hook.  	Any non-Guest user may`, `Set the ``app`` field on the Workspace if it is NULL.  	Required for Frappe v16`, `Set the ``type`` field on the Workspace if it is NULL.  	Required for Frappe v16`, `Rebuild the app-owned Workspace Sidebar for the workshop workspace.  	Frappe v16`, `Create the App-type Desktop Icon if it does not already exist.  	Called from ``a` (+256 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **44 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TestRepairServiceLine` connect `Community 3` to `Community 0`?**
  _High betweenness centrality (0.173) - this node is a cross-community bridge._
- **Why does `FleetServiceCampaign` connect `Community 5` to `Community 3`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `_get_or_create_customer()` (e.g. with `.setUp()` and `_create_repair_job()`) actually correct?**
  _`_get_or_create_customer()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `_create_test_vehicle()` (e.g. with `.setUp()` and `_create_repair_job()`) actually correct?**
  _`_create_test_vehicle()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Permission check for the ``add_to_apps_screen`` hook.  	Any non-Guest user may`, `Set the ``app`` field on the Workspace if it is NULL.  	Required for Frappe v16`, `Set the ``type`` field on the Workspace if it is NULL.  	Required for Frappe v16` to the rest of the system?**
  _261 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.07 - nodes in this community are weakly interconnected._