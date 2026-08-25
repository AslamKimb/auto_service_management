# Gauntlet Loop — Repair Job Sales Order Proforma and Optional Workflow

## Previous run record

The prior Sales Order / Proforma Invoice run established the protected-state controls, backend/UI critics, and the remaining browser/PDF inspection boundary. Its evidence is retained below so this run does not erase history.

| ID | Output | Status | Evidence / remaining gate |
|---|---|---|---|
| M1 | Backend mapper, schema, lifecycle, sync | PASSED | Backend contract 4/4, Phase10 mapping 37/37, reversed native invoice trace pass. |
| M2 | Native Desk selector, actions, Proforma print behavior | PASSED | Focused contracts 3/3, Node/compile/JSON checks pass. |
| M3 | Integration and whole-system verification | CRITIC / UNVERIFIED | Browser CDP/PDF inspection remained unavailable; full suite had one pre-existing Job Card SVG metadata assertion. |

## Current run — Optional Repair Workflow and Stable v16 Upgrade

Goal: Make Repair Job evidence optional and non-regressive, update the editable stack to the compatible stable Frappe v16 set, and prove the result end to end.

Quality bar: G1 workflow behavior; G2 UI/native links; G3 upgrade compatibility; G4 regression suite; G5 live Desk inspection; G6 commit/push synchronization.

Overall state: BLOCKED / UNVERIFIED
Current wave: W1 — integration and closeout
Required modules: 3/3
Active: integration
Blocked: live browser/render inspection remains capability-gated; wkhtmltopdf cannot resolve the local asset host
Blocked: whole-system visual gate only
Whole-system gate: BLOCKED / UNVERIFIED
Parallel now: M1, M2, M3
Sequential chains: M1/M2/M3 → fresh critics → integration → site migration → system critic → commit/push
Free worker slots: 3
Dispatch batch: M1 -> backend_optional_workflow; M2 -> desk_docs_optional_flow; M3 -> stable_v16_pins
Last update: 2026-08-24 integration and upgrade evidence

| ID | Output | Depends on | Quality gate | Owner | Round | Status | Last verdict | Largest gap | Evidence | Next action |
|---|---|---|---|---|---:|---|---|---|---|---|
| M1 | Optional Repair Job backend workflow and tests | None | G1 | backend_optional_workflow | 1 | PASSED | PASS | Browser/PDF presentation remains outside backend gate | optional evidence integration 3/3, workflow compatibility 14/14, late authorization 1/1, compileall/Ruff, POST-only Return to Repair, and preserved guards pass | Keep visual gate separate |
| M2 | Desk actions, native links, docs, and acceptance contracts | None | G2 | desk_docs_optional_flow | 2 | PASSED | PASS | Live browser/render inspection remains unverified | Bash, Node, JSON, static button/link/no-quotation/no-stale-Road-Test checks pass; bounded fix removed stale assertion | Integrate and run live checks |
| M3 | Stable v16 dependency pins and upgrade checks | None | G3 | stable_v16_pins | 1 | PASSED | PASS | Browser/PDF presentation remains capability-gated | test/dev backups, migrations exit 0, exact Frappe/ERPNext/HRMS/Uganda SHAs, bench version, build, proxy asset HTTP 200, and direct backend ping HTTP 200 | Keep image gate closed |

## Event Log

| When | Module | Transition | Evidence or decision | Unlocked / next |
|---|---|---|---|---|
| 2026-08-24 | RUN | SETUP -> BUILDING | Graph report read; graph query mapped Repair Job, Sales Order mapping, and workflow communities. Three disjoint builders dispatched. | Fresh critics after each builder |
| 2026-08-24 | M3 | BUILDING -> CRITIC -> PASSED | Fresh critic PASS: exact stable v16 commits, Compose/YAML/shell, Containerfile, upstream resolution, and dirty-repo safety simulation passed. | Await M1/M2 builders and critics |
| 2026-08-24 | M1 | BUILDING -> CRITIC | Builder returned backend artifact; workflow compatibility 14/14 and compileall pass; optional integration suite remains unverified. | Fresh backend critic |
| 2026-08-24 | M2 | BUILDING -> CRITIC | Builder returned Desk/docs artifact; static contracts and parsing pass; browser render explicitly blocked. | Fresh UI/docs critic |
| 2026-08-24 | M1 | CRITIC -> PASSED | Fresh backend critic PASS: compileall, 9 focused workflow tests, optional-status matrix, explicit POST rework action, and preserved controls verified. | Integrate after M2 passes |
| 2026-08-24 | M2 | CRITIC -> FIX | Fresh critic found stale standalone `Road Test Report` assertion in acceptance script; builder removed it and reran static checks. | Fresh M2 critic retest |
| 2026-08-24 | M2 | FIX -> CRITIC -> PASSED | Fresh static critic PASS: bash, Node, JSON, required buttons, native form links, no quotation actions, and no stale standalone Road Test Report assertion. | Integration wave |
| 2026-08-24 | Integration | RUNNING -> PASSED | Test-site migration reached 100% DocType sync and exited 0; optional evidence 3/3; workflow compatibility 14/14; Sales Order/Proforma/Phase10 contracts 44/44; dev migration later exited 0; exact stable v16 versions verified. | Live runtime and whole-system gate |
| 2026-08-24 | Integration | FAIL -> FIX -> PASSED | Full-suite timestamp errors were reproduced as stale Repair Job action snapshots. Controller actions now reload persisted docs; late-authorization regression passed 1/1, and the PDF test progressed past the timestamp failure. | Record renderer blocker honestly |
| 2026-08-24 | Renderer/browser | VERIFY -> BLOCKED / UNVERIFIED | wkhtmltopdf fails with `HostNotFoundError` for local asset host; browser-control runtime cannot establish Chrome CDP. Native HTML/static contracts and generated bundle HTTP 200 remain green, but no live selector/PDF visual claim is made. | Await capability recovery before marking whole-system complete |
| 2026-08-24 | Commit/push | READY -> PASSED | Commit `aba2444f5fd71e2aabd08b2ee49fc47b44455e3d` pushed to `origin/version-16`; local `HEAD` and remote ref match and the worktree is clean. | Delivery synchronized; visual gate remains blocked |

## Current run — Repair Job Service Templates and Native History Drill-Down

Goal: add current-model Repair Job Service Templates, editable template/service mapping, a Find Vehicle workspace route, and native Customer/Customer Vehicle repair-history navigation.

Quality bar: G1 template schema and compatible selection; G2 snapshot mapping and current-price semantics; G3 native vehicle/customer history; G4 permissions, migrations, and regressions; G5 direct Desk inspection; G6 commit/push synchronization.

Overall state: BLOCKED / UNVERIFIED
Current wave: W2 — integrated verification
Required modules: 2/2
Active: Whole-system critic / closeout
Blocked: authenticated Desk/browser visual inspection; no reusable session/CDP
Whole-system gate: BLOCKED / UNVERIFIED
Parallel now: closeout
Sequential chains: M1/M2 -> fresh critics -> integration -> whole-system critic -> commit/push
Free worker slots: 2
Dispatch batch: M1 -> service_template_mapping; M2 -> history_navigation_workspace
Last update: 2026-08-24 M1/M2 fresh critics passed; integration unlocked

| ID | Output | Depends on | Quality gate | Owner | Round | Status | Last verdict | Largest gap | Evidence | Next action |
|---|---|---|---|---|---:|---|---|---|---|---|
| M1 | Repair Job Service Template DocTypes, mappers, service flow, and tests | None | G1/G2 | m1_templates | 2 | PASSED | PASS | Authenticated Desk template apply remains unverified | Fresh critic source review; synced v16 bench module 6/6; JSON, compile, Node, Ruff, and diff checks | Keep visual gate separate |
| M2 | Vehicle/customer history dashboards, workspace routes, and tests | None | G3 | history_navigation_workspace | 2 | PASSED | PASS | Authenticated Desk dashboard drill-down remains unverified | Fresh critic source/runtime review; focused history 4/4, workspace 11/11, and both-site sidebar/shortcut rows | Keep visual gate separate |

## Current run event log

| When | Module | Transition | Evidence or decision | Unlocked / next |
|---|---|---|---|---|
| 2026-08-24 | RUN | SETUP -> BUILDING | Locked additive scope, native drill-down, refreshed ERPNext pricing, unsaved review flow, and retired-template non-goal. | M1/M2 builders |
| 2026-08-24 | Design | BUILDING -> READY | Persisted `docs/design/repair-job-service-templates-and-history.md` with native Frappe forms, dialogs, dashboards, states, accessibility, and pricing rules. | Builders use the approved direction |
| 2026-08-24 | M1/M2 | READY -> BUILDING | Disjoint builders dispatched; M1 owns template/service files, M2 owns customer/vehicle/workspace files; plan and tracker remain lead-owned. | Await both artifacts |
| 2026-08-24 | M1 | BUILDING -> CRITIC | Builder returned template DocTypes, mappers, Repair Job/Service actions, and focused tests; static evidence passes, but the Frappe runner has no final result yet. | Fresh M1 critic; M2 remains in build |
| 2026-08-24 | M1 | CRITIC -> FIX | Fresh critic FAIL: discount fields violate price-free templates; unsaved mapped docs have no guaranteed route name; test base is not available in Frappe v16. | Return largest gap to M1 builder; keep integration blocked |
| 2026-08-24 | M2 | BUILDING -> CRITIC | Builder returned Customer/Customer Vehicle dashboard hooks, native Find Vehicle/Customers navigation, search/list fields, docs, and runtime dashboard smoke. | Fresh M2 critic; M1 fix remains blocking |
| 2026-08-24 | M1 | CRITIC -> FIX | Fresh critic failed price-free/unsaved/v16-base guarantees; root corrected schemas, sync routing, server context/compatibility guards, and focused fixtures. | Fresh M1 critic |
| 2026-08-24 | M1 | FIX -> PASSED | Fresh critic source contracts pass; synced Frappe v16 bench module passed 6/6. | Unlock integration |
| 2026-08-24 | M2 | CRITIC -> PASSED | Fresh critic PASS: dashboard merge, native navigation, search/list fields, hooks, and synced DB rows verified. | Unlock integration |
| 2026-08-24 | Integration | BUILDING | Added missing DocType package markers/controllers after migration orphan check; test-site schema now exposes all four current-model template DocTypes and dashboard hook. | Run integrated contract suite, dev migration, asset build, Graphify, whole-system critic |
| 2026-08-24 | Integration | BUILDING -> PASSED | Phase 6 27/27, Phase 7 2/2, template 6/6, history 4/4, workspace 11/11; both sites reached 100% DocType sync; dev backup, asset build, Graphify refresh, HTTP 200 ping/asset, and idempotent desktop setup verified. | Whole-system visual gate |
| 2026-08-24 | Full suite | VERIFY -> PARTIAL | Aggregate run: 133/133 unit tests green, 66/66 unspecified tests green, and 70 integration tests with one known wkhtmltopdf `HostNotFoundError` on Job Card local asset resolution. Navigation/materialization/permission stale contracts were updated to current requirements and their focused retests passed. | Preserve renderer/browser blocker honestly |
| 2026-08-24 | Whole-system critic | CRITIC -> BLOCKED / UNVERIFIED | Fresh runtime recheck confirmed exact Find Vehicle → Customer Vehicle and Customers → Customer rows on both sites, current-model template schema, dashboards, and focused tests. Browser can render login page, but no authenticated Desk session/CDP is available; direct selector/dashboard/empty-state interaction is not observed. | Preserve blocker; commit/push with honest gate status |

## Previous run events

| When | Module | Transition | Evidence or decision | Unlocked / next |
|---|---|---|---|---|
| Setup | All | SETUP -> READY | Approved implementation plan and protected-state controls recorded | Dispatch M1 and M2 |
| W1 | M1/M2 | READY -> BUILDING | Disjoint backend and UI/print workstreams dispatched to separate builders | Await both builders |
| W1 | M2 | BUILDING -> CRITIC | UI/print artifact returned with focused evidence | Dispatch fresh critic |
| W1 | M2 | CRITIC -> FIXING | Fresh critic found missing `sales_orders_html` render targets in both DocTypes | Add fields, rerun focused checks, dispatch fresh critic |
| W1 | M1 | BUILDING -> CRITIC | Backend artifact returned with static evidence; live migration/test queue not complete | Dispatch fresh backend critic |
| W1 | M2 | FIXING -> PASSED | Added `sales_orders_html` to both DocTypes; fresh critic static retest passed | Unlock M3 when M1 critic passes |
| W1 | M1 | CRITIC -> FIXING | Fresh critic found stale container source and positional native invoice trace risk | Sync current source, fix identity matching, rerun backend contracts and fresh critic |
| W1 | M1 | FIXING -> PASSED | Current-source hash check, backend contract 4/4, Phase10 mapping 37/37, and reversed native invoice trace regression all pass | Unlock integration gate |
| W1 | Runtime | BUILDING -> PARTIAL | Test-site source synced; migration reached DocType/customization sync; after-migrate sleep loop interrupted safely; custom fields and print heading then applied directly; asset build passed; live GET endpoint returned 3 selectable components | Fresh critic, live selection retry, HTML/PDF, whole-system gate |
| W1 | Integration | PARTIAL -> CRITIC | Re-ran backend/UI Frappe contracts after schema repair; test site exposes `sales_orders_html`, Sales Order Item trace field, and `Print Heading = Proforma Invoice`; browser harness still fails CDP handshake | Fresh whole-system critic |
| W1 | Whole-system critic | CRITIC -> UNVERIFIED | Fresh critic confirms the contract/runtime branches are evidenced but live selector and HTML/PDF presentation branch is absent | Restore CDP and capture selector + rendered Proforma HTML/PDF evidence |
| W1 | Full suite | VERIFY -> PARTIAL | Full app run completed: 130 unit tests with one existing Job Card SVG metadata assertion; 66 integration tests completed successfully; feature-focused suites remain green | Keep Phase 25 blocked until presentation gate closes |

## Current run — Fleet Campaign Repair Jobs and Consolidated Billing

Goal: Fleet Service Campaign creates linked Repair Jobs, consolidates selectable service components into traceable Sales Orders and Sales Invoices, tracks those documents, prints Sales Orders as Proforma Invoices, and removes the two reported permission failures.

Quality bar: G1 bidirectional campaign/job linkage; G2 component-safe multi-job Sales Order and Sales Invoice flows; G3 native Desk tracking plus Proforma output; G4 parent-scoped report access and least-privilege service-template access; G5 targeted, full-suite, migration, build, live non-image, and fresh-critic evidence.

Overall state: BLOCKED / UNVERIFIED
Current wave: W3 serialized focused regression, migration, and editable-stack proof
Required modules: 4 / 5
Active: M5 integration closeout
Blocked: Authenticated Desk/PDF visual branch; Browser Use CDP handshake timed out and wkhtmltopdf cannot resolve the local asset host
Whole-system gate: BLOCKED / UNVERIFIED
Parallel now: none; integration is serialized
Sequential chains: M3+M4 -> M5
Free worker slots: 3 after critics
Dispatch batch: lead integration
Last update: M3 PASS; M4 focused UI/print PASS after Ruff formatting fix; M5 runtime evidence is partial with visual/PDF capability blockers

| ID | Output | Depends on | Quality gate | Owner | Round | Status | Last verdict | Largest gap | Evidence | Next action |
|---|---|---|---|---|---:|---|---|---|---|---|---|
| M1 | Campaign and Repair Job lifecycle plus create mapper | None | G1 | campaign_link_builder | 1 | PASSED | PASS | None; database reassignment/denial coverage is optional integration strengthening | Controller 10/10 plus real DB lifecycle 1/1; compile/Ruff/diff clean | Integrate after M2 passes |
| M2 | Campaign Sales Order and Sales Invoice backend | None | G2 | campaign_billing_builder | 3 | PASSED | PASS | None; DB-fixture depth is optional strengthening | Campaign 17/17; adjacent 4/4; live POST/GET metadata; AST/Ruff/diff clean | Integrated prerequisite for M4 |
| M3 | Report child-permission and template-access repair | None | G4 | permission_repair_builder | 4 | PASSED | PASS | None; Frappe v17 deprecation warning is non-blocking on v16 | Serial 42/42 (8 permission, 27 Phase6, 3 reconciliation, 4 real report); direct PermissionError; exact child routing; v16 child-select patch read back on both sites; Ruff/format/AST/JSON/Node/diff clean | Integrated prerequisite |
| M4 | Campaign Desk UI, tracking, dashboard, and print integration | M1, M2 | G3 | campaign_ui_print_builder | 1 | BLOCKED | UNVERIFIED | Authenticated Desk/CDP and campaign PDF not available; Browser Use handshake timed out at Chrome Allow prompt; wkhtmltopdf HostNotFoundError | UI 9/9; printing 8/8; focused changed-file Ruff format/check, Node/Python/JSON/Jinja/diff clean; full app retains pre-existing formatter drift | Integrate code; visual gate remains blocked |
| M5 | Integrated runtime proof and system critic | M1, M2, M3, M4 | G1-G5 | Lead | 1 | BLOCKED | PARTIAL / UNVERIFIED | Isolated integration 21/22 with only wkhtmltopdf HostNotFoundError; aggregate run 169/169 unit and 72/72 unspecified but shared-run child-permission traceback and workspace deadlock are runner artifacts; authenticated Desk/PDF branch unavailable | Campaign 17/17 + lifecycle 1/1 + UI 9/9 + printing 8/8 + permission/report 42/42; both-site custom fields and DocPerm select readback; editable build/ping/asset HTTP 200; Graphify refreshed | Restore browser/PDF capability, rerun full suite uncontended, then close M5 |

### Fleet campaign event log

| When | Module | Transition | Evidence or decision | Unlocked / next |
|---|---|---|---|---|
| Setup | Run | SETUP -> BUILDING | Clean `version-16` worktree at `c4c919c`; graph report inspected; non-image-only approval boundary retained | Dispatch W1 |
| Setup | Tracker | RECONCILED | Initial Phase 28 tracker write replaced prior history; committed tracker was restored byte-for-byte and Phase 28 appended; project guardrail added | Continue W1 with append-only tracking |
| W1 | M1 | BUILDING | Red test failed on missing `make_repair_job`; controller and lifecycle implementation started | Focused green run, then critic |
| W1 | M2 | BUILDING | Six red tests produced 2 failures and 4 errors for missing campaign scope, mapping helpers, parent fields, and native invoice propagation | Focused green run, then critic |
| W1 | M3 | BUILDING | Live Error Log reproduced child permission failure; focused permission regression module now passes 5/5 after scoped repairs | Static closeout, then critic |
| W1 | M3 | BUILDING -> CRITIC | Builder returned parent-scoped report, API/UI gates, Number Card context, and bounded reconciliation; focused modules pass 5/5 and 3/3 | Fresh M3 critic |
| W1 | M2 | BUILDING -> CRITIC | Campaign mapping, multi-job scope validation, trace fields, and native invoice propagation returned; six-test green run plus static checks pass; seventh aggregation test awaits clean rerun | Fresh M2 critic |
| W1 | M1 | BUILDING -> CRITIC | POST mapper and bidirectional lifecycle synchronization returned; controller tests 10/10 plus static checks pass; database lifecycle module awaits clean run | Fresh M1 critic |
| W1 | M2 | CRITIC -> FIX | Critic FAIL G2: campaign mutation functions are not whitelisted POST-only and validation ignores extra untraced items despite 7/7 focused tests | Builder adds RPC and complete-trace regression contracts; fresh round-2 critic |
| W1 | M1 | CRITIC -> PASSED | Fresh critic verified POST-only mapper, permission/status/customer controls, duplicate/recursion-safe bidirectional sync, 10/10 controller tests and 1/1 DB lifecycle test | M1 passed; M4 still blocked on M2 |
| W1 | M3 | CRITIC -> FIX | Fresh critic FAIL G4: report runner uses get_all/business-link simulation instead of Frappe parent_doctype permissions; template cleanup is overbroad | Builder fixes framework scoping and constrained-row preservation; fresh round-2 critic |
| W1 | M2 | FIX -> CRITIC | POST-only whitelist and complete six-field trace enforcement added; campaign 11/11 and adjacent 4/4 pass | Fresh M2 round-2 critic |
| W1 | M3 | FIX -> CRITIC | Runner changed to parent_doctype get_list; reconciliation narrowed by locked role and permlevel; static checks pass, focused runtime deliberately deferred | Fresh M3 round-2 critic |
| W1 | M2 | CRITIC -> FIX | Round-2 critic FAIL G2: valid component refs can be paired with forged vehicle/service/project traces; parent project/source and manual direct-SI overlap are not fully rejected | Builder adds authoritative trace and overlap validation; fresh round-3 critic |
| W1 | M3 | CRITIC -> FIX | Round-2 critic FAIL G4: parent-scoped query is correct, but runner's read-or-report precheck conflicts with native parent read enforcement and tests are mocked | Require both permissions and prove restricted rows with real users/documents; fresh round-3 critic |
| W1 | M2 | FIX -> CRITIC | Authoritative component-chain comparison, blank campaign parent sources, and DB-backed overlap guards added; 17/17 and 4/4 pass | Fresh M2 round-3 critic |
| W1 | M3 | FIX -> CRITIC | Runner now requires report and read/select; real owner-restricted row integration and denial cases added; runtime green deferred to uncontended critic | Fresh M3 round-3 critic |
| W1 | M3 | CRITIC -> FIX | Round-3 critic FAIL G4: parent_doctype was applied to non-child Version report; denial assertion rejected legitimate Translation lookup; 5/6 focused tests passed | Explicit child-query routing and discriminating regressions; fresh round-4 critic |
| W1 | M2 | CRITIC -> PASSED | Round-3 critic verified 17/17 campaign tests, 4/4 adjacent contracts, live methods, authoritative trace/overlap guards, and legacy isolation | M4 unlocked |
| W2 | M4 | BLOCKED -> BUILDING | M1 and M2 passed; approved native Desk design and campaign backend interfaces available | Build campaign actions, selector, tracking, dashboard, and Proforma integration |
| W2 | M3 | FIX -> CRITIC | Explicit permission_parent_doctype limits child semantics to two invoice reports; Version/Translation regressions fixed; three focused modules green; final real-role fixture awaits rerun | Fresh M3 round-4 critic |
| W2 | M4 | BUILDING -> CRITIC | Native campaign form actions, selector, tracking, dashboard, mapped wrappers, campaign Proforma template, and dual render returned; final bench/API and live Desk/PDF remain pending | Fresh M4 critic; hold tests behind M3 |
| W2 | M3 | CRITIC -> PASSED | Fresh round-4 critic verified 7/7 permission, 27/27 Phase6, 3/3 reconciliation, and 4/4 real restricted-report tests serially; template matrix/cards/API and exact routing pass | M3 integrated |
| W2 | M4 | CRITIC -> BLOCKED / UNVERIFIED | Fresh critic verified UI 9/9, printing 8/8, static checks, dual campaign/single-job Jinja; browser CDP handshake timed out at Chrome Allow prompt | Integrate code; visual gate remains blocked |
| W3 | Integration | BUILDING | Formatted four files; reran UI 9/9 and printing 8/8; test/dev migration, campaign/lifecycle/backend regression, full suite, build, and live HTML remain | Create backups, migrate, run integrated tests/build |
| W3 | M3 | PASSED -> HARDENED | Added v16-compatible `select` permissions to active Repair Job Service component children plus idempotent `phase28_v16_child_select_permissions` patch; both sites read back all 12 role/doctype rows with `select=1`; direct child `get_list` and `has_permission` probes no longer raise PermissionError | Preserve least-privilege child access and rerun isolated integration |
| W3 | Integration | BUILDING -> PARTIAL / UNVERIFIED | Focused campaign billing 17/17, lifecycle 1/1, UI 9/9, permission regressions 8/8, report permissions 4/4; isolated controllers integration 21/22 with one wkhtmltopdf `HostNotFoundError`; aggregate app run 169/169 unit and 72/72 unspecified, with shared-run workspace/child-permission artifacts | Record renderer/browser blocker; no completion claim |
| W3 | Runtime | PARTIAL -> VERIFIED (non-visual) | Test/dev sites reached 100% DocType sync; campaign trace custom fields exist on both sites; child DocPerm patch applied on both; editable build exit 0; `/api/method/ping` and versioned billing bundle returned HTTP 200; Graphify refreshed to 241 files / 2707 nodes / 4120 edges / 442 communities | Await authenticated Desk and PDF visual evidence |
| W3 | Whole-system critic | VERIFY -> BLOCKED / UNVERIFIED | Browser Use doctor found Chrome/daemon but CDP handshake timed out at the Chrome Allow prompt; no authenticated campaign selector/dashboard/PDF interaction can be observed; wkhtmltopdf cannot resolve local asset host | Keep M4/M5 and Phase 28 explicitly blocked; do not build/deploy image |
| W3 | Static hygiene | CHECK -> QUALIFIED PASS | Focused campaign/permission files pass Ruff check, targeted Ruff format, compileall, Node, JSON, and `git diff --check`; full app Ruff still reports 14 pre-existing import/unused-variable findings outside the new campaign/permission modules | Do not broaden mechanical formatting into unrelated files |
| W3 | Runtime bug follow-up | REPRODUCED -> FIXED / VERIFIED | Supplied screenshot/logs reproduced HTTP 417 `Failed to get method` for the campaign summary RPC while a fresh `bench execute` resolved the function; stale `bench serve --noreload` module state was confirmed. Restarted backend, cleared cache, rebuilt assets, replayed exact URL (403 Guest permission instead of 417), authenticated server-side summary returned empty tracked-document lists, and campaign UI/RPC tests passed 10/10 | Keep backend restart invariant documented; ask user to hard-refresh and retry the Fleet Campaign save |

## Current run — Repair Job Native Tabs and Connections Redesign

Goal: reorganize the existing Repair Job form into native Frappe Details, Services, Workshop, Billing, and Connections tabs while preserving every field semantic and exposing native linked-record navigation.

Quality bar: RJ-UI exact tab order and Connections dashboard; RJ-PRESERVE all existing fields and required/read-only/hidden semantics; RJ-DASH native grouped connections and direct/child link contracts; RJ-RUNTIME migrations, focused regressions, build, and live metadata; RJ-VISUAL authenticated Desk inspection at desktop and narrow viewport or an explicit capability blocker.

Overall state: BLOCKED / UNVERIFIED
Current wave: W2 — integrated runtime proof and visual gate
Required modules: 2 / 3
Active: M3 lead closeout
Blocked: authenticated Desk/CDP visual inspection; browser-use daemon has no active connection
Whole-system gate: BLOCKED / UNVERIFIED
Parallel now: none; integration is serialized
Sequential chains: M1+M2 -> fresh critics -> integration -> whole-system critic
Free worker slots: tracked in collaboration roster
Dispatch batch: M1 -> Bro; M2 -> repair_job_dashboard_builder
Last update: 2026-08-24 setup

| ID | Output | Depends on | Quality gate | Owner | Round | Status | Last verdict | Largest gap | Evidence | Next action |
|---|---|---|---|---|---:|---|---|---|---|---|
| M1 | Native Repair Job JSON layout and design note | None | RJ-UI/RJ-PRESERVE | Bro | 1 | PASSED | PASS | None | JSON parsed; exact five tabs; field-preservation critic PASS; design note persisted | Integrated into M3 |
| M2 | Native dashboard definition and contract tests | None | RJ-DASH | repair_job_dashboard_builder | 1 | PASSED | PASS | None | Fresh critic PASS; Frappe v16 module 5/5; dashboard metadata and link counts live-verified | Integrated into M3 |
| M3 | Integrated migration/build/runtime/visual proof | M1, M2 | RJ-RUNTIME/RJ-VISUAL | Bro | 1 | PASSED | PASS | None for the native Repair Job tabs scope | 43/43 focused regressions; both-site metadata/count probes; build/cache/restart/ping; Graphify refresh; authenticated desktop+narrow Desk inspection with tab switching, grouped Connections, populated counts, and empty link rows | Preserve evidence; broader whole-system blockers remain tracked separately |

### Native tabs run event log

| When | Module | Transition | Evidence or decision | Unlocked / next |
|---|---|---|---|---|
| 2026-08-24 | Run | SETUP -> BUILDING | Approved screenshot direction translated into native Frappe tab/dashboard contract; no core edits, no image deployment | M1/M2 builders |
| 2026-08-24 | M1 | BUILDING | Added Details/Services/Workshop/Billing/Connections Tab Breaks, moved only field order, and persisted `docs/design/repair-job-form-layout.md` | Await M2 and contract tests |
| 2026-08-24 | M2 | BUILDING -> CRITIC -> PASSED | Native dashboard and contract tests returned; fresh critic verified exact groups, links, no duplicates, and Frappe v16 5/5 | Unlock M3 |
| 2026-08-24 | M1 | BUILDING -> CRITIC -> PASSED | Fresh critic compared against `HEAD`: all 50 existing fields retained with key semantics, five tabs exact, static checks clean | Unlock M3 |
| 2026-08-24 | M3 | BUILDING -> PARTIAL / UNVERIFIED | Both-site metadata and native count probes passed; serial focused regressions passed 43/43; build/cache/restart/ping passed; Browser Use doctor/CDP probe failed | Preserve explicit visual blocker; no completion claim |
| 2026-08-24 | M3 | PARTIAL / UNVERIFIED -> PASSED | Authenticated Desk/CDP became available: exact five tabs rendered and switched on `RJ-2026-00096` and `RJ-2026-00005`; desktop screenshots covered Services, Workshop, Billing, and Connections; Connections showed grouped links with populated and empty rows; narrow `390x844` retained all tab buttons and Billing content; viewport restored to `1310x683` | Native Repair Job tabs scope closed; broader whole-system blockers remain separate |

## Current run — Car Workshop Native Workspace Hubs

Goal: reorganize the Car Workshop app icon into a native Frappe parent app modal with eight role-filtered workflow workspaces while preserving the `Workshop Management` route as the Overview/default workspace and removing technical coverage counters from staff-facing pages.

Quality bar: CW-STRUCTURE exact eight hubs and parent/child hierarchy; CW-NATIVE v16 Workspace, Workspace Sidebar, Desktop Icon, and app-hook contracts; CW-PRESERVE existing route, permissions, workflows, and business data; CW-TEST focused contracts, migration, build, and role-filtered boot data; CW-VISUAL authenticated Desk inspection of the parent modal and hubs at desktop and narrow viewport, or an explicit capability blocker.

Overall state: PASSED (native navigation scope; no image deployment)
Current wave: W2 — integrated runtime and visual closeout
Required modules: 4 / 4
Active: none; closeout evidence recorded
Blocked: no remaining blocker for the approved native navigation scope
Whole-system gate: PASSED for Car Workshop navigation; unrelated renderer/image gates remain tracked in prior runs
Parallel now: none
Sequential chains: M1+M2 -> fresh critics -> contract integration -> editable runtime -> whole-system critic
Free worker slots: available
Dispatch batch: M1 -> workspace_hubs_builder; M2 -> desktop_app_icon_builder
Last update: 2026-08-25 runtime and Desk visual closeout

| ID | Output | Depends on | Quality gate | Owner | Round | Status | Last verdict | Largest gap | Evidence | Next action |
|---|---|---|---|---|---:|---|---|---|---|---|---|
| M1 | Native eight-hub workspace definitions, fixtures, and design note | None | CW-STRUCTURE/CW-PRESERVE | workspace_hubs_builder | 1 | PASSED | PASS | None | Eight fixtures, exact order, operational-only Overview, design note, JSON/static checks | Integrated into runtime |
| M2 | Parent App icon, child Desktop Icons, sidebar lifecycle, and app hook | None | CW-NATIVE/CW-PRESERVE | Bro (builder stalled; root completed) | 1 | PASSED | PASS after round-3 critic | Native App parent, eight role-bearing Workspace Sidebar children, v16 `link_to=<sidebar>`, legacy cleanup, idempotent lifecycle | Integrated into runtime |
| M3 | Contract/regression tests and acceptance updates | M1, M2 | CW-TEST | Bro | 1 | PASSED | PASS | None | Workspace contracts 12/12; desktop integration contracts 3/3; JSON/compile/Ruff/diff checks | Keep regression coverage |
| M4 | Integrated migration/build/runtime/visual proof | M1, M2, M3 | CW-TEST/CW-VISUAL | Bro | 1 | PASSED (qualified) | PASS | Frappe migrate reaches 100% then hits known Docker `Command: Sleep` loop; no schema blocker | Direct setup committed on both sites; build completed; ping/assets HTTP 200; live role filter Cashier => Car Workshop/Parts & Billing/Reports; authenticated Desk parent modal and Overview desktop + narrow sidebar collapse inspected | No image build/deploy |

### Car Workshop workspace event log

| When | Module | Transition | Evidence or decision | Unlocked / next |
|---|---|---|---|---|
| 2026-08-24 | Run | SETUP -> BUILDING | Approved HRMS-style eight-hub native Frappe plan; role-filtered visibility and operational-only dashboards selected; no core edits or image deployment | Dispatch M1/M2 |
| 2026-08-24 | M1 | BUILDING -> CRITIC | Builder returned eight native Workspace fixtures and persisted `docs/design/car-workshop-navigation.md`; static JSON/fixture checks passed | Fresh critics |
| 2026-08-24 | Critics | CRITIC -> FIX -> CRITIC | Round-1 and round-2 critics found missing child roles, stale legacy cleanup, app-less icon cleanup, and old shortcut assertions; root fixed each gap | Fresh round-3 critic |
| 2026-08-24 | Round-3 critic | CRITIC -> FIX | Found Parts Queue/Gate Passes fixture labels drifting from runtime hub definitions; fixtures aligned and parity test added | Re-run contracts |
| 2026-08-25 | Contracts | FIX -> PASSED | Workspace/dashboard unit contracts passed 12/12; desktop hierarchy/idempotency/grouping integration contracts passed 3/3; targeted Ruff, compileall, JSON, and diff checks passed | Runtime proof |
| 2026-08-25 | Runtime | BUILDING -> PASSED (qualified) | Test/dev post-sync setup committed native records; exact parent/children/sidebar/legacy queries pass; Cashier boot simulation returns only Car Workshop, Parts & Billing, Reports; migration reached 100% sync before known cleanup sleep loop | Build and Desk inspection |
| 2026-08-25 | Visual | VERIFY -> PASSED | Browser Use authenticated Desk inspection: Car Workshop parent modal shows eight branded SVG cards at 1310x683; Overview sidebar and operational charts render; 390x844 native sidebar collapses and charts stack without custom shell; viewport restored | Scope closed; no image build/deploy |

## Current run — Structured Spare-Parts Fitment Catalog

Goal: keep one ERPNext Item per physical spare part while recording reusable make/model/engine fitment, importing mixed-quality catalog data safely, and warning (not blocking) when a Repair Job part lacks an exact fitment.

Quality bar: G1 fitment/engine schema and validation; G2 duplicate-safe Item/fitment import path; G3 permission-checked compatibility query and Repair Job warning/override; G4 focused regressions, migration, build, and editable-stack runtime; G5 fresh critics plus whole-system evidence. No Item Variants for fitment, no ERPNext/Frappe core edits, no image/production deployment.

Overall state: BLOCKED / UNVERIFIED
Current wave: W2 — integration and editable runtime proof
Required modules: 3 / 4
Active: M4 closeout
Blocked: one pre-existing parent-scoped report permission artifact and browser/PDF visual capability
Whole-system gate: PENDING
Parallel now: M1, M2, M3
Sequential chains: M1 -> M4; M3 -> M4; M2 -> M4
Free worker slots: tracked in collaboration roster
Dispatch batch: M1 -> fitment_schema_builder; M2 -> fitment_import_builder; M3 -> compatibility_query_builder
Last update: 2026-08-25 setup

| ID | Output | Depends on | Quality gate | Owner | Round | Status | Last verdict | Largest gap | Evidence | Next action |
|---|---|---|---|---|---:|---|---|---|---|---|---|
| M1 | Vehicle Engine, Item Vehicle Fitment, Customer Vehicle engine-model link, permissions, and schema tests | None | G1 | fitment_schema_builder | 2 | PASSED | PASS | Live serial Frappe test pending setup completion | Canonical-field reconciliation, schema/static contracts, import 8/8, and fresh schema critic PASS | Integrate and run serial bench tests |
| M2 | Duplicate-safe Item/fitment CSV templates, validator/import documentation, and source audit tooling | None | G2 | fitment_import_builder | 3 | PASSED | PASS | Manufacturer child-template validation is optional hardening | 8 focused tests, native Item headers, alias checks, CLI/hash immutability, compileall/Ruff, fresh critic PASS | Integrate package and runtime proof |
| M3 | Compatibility read query, Repair Job part match snapshot/warning, Desk contracts, and focused tests | None | G3 | compatibility_query_builder | 2 | PASSED | PASS | Live serial Frappe test pending setup completion | GET-only decorators, permissions, canonical fields, ranking/snapshot tests, compile/Ruff, fresh critic PASS; custom JS intentionally deferred | Integrate and run serial bench tests |
| M4 | Integrated migration, tests, build, live editable-stack proof, Graphify refresh, and whole-system critic | M1, M2, M3 | G4/G5 | Bro | 1 | BLOCKED / UNVERIFIED | PARTIAL | Full app integration has one known v16 parent-scoped child-report permission artifact plus wkhtmltopdf/browser visual blockers | Focused Frappe 8/8 + 9/9, full unit 215/215, integration 73/75 with one known PDF HostNotFoundError and one existing Jobs Waiting for Parts permission artifact; build, ping, metadata, GET/POST denial, Graphify 3142/4772/500 | Keep image gate closed; resolve report artifact and obtain approved authenticated visual inspection |

### Structured fitment catalog event log

| When | Module | Transition | Evidence or decision | Unlocked / next |
|---|---|---|---|---|
| 2026-08-25 | Run | SETUP -> BUILDING | Scope locked to one physical Item plus many fitments; engine model distinct from engine serial; manual+CSV first; warn-and-allow with override reason; existing dirty LPO work protected | Dispatch M1/M2/M3 disjoint builders |
| 2026-08-25 | M2 | BUILDING -> CRITIC | Import builder returned validator, templates, docs, and 4/4 focused tests; fresh critic must verify DocType header compatibility and non-mutating review behavior | Await fresh M2 critic; M1/M3 continue building |
| 2026-08-25 | M2 | CRITIC -> FIX | Fresh critic failed G2.4/G2.5: internal ASM-/PROV- fallback is rejected after normalization and CSV fields do not match Item Vehicle Fitment; dual OEM/manufacturer identifiers also need independent checks | M2 builder fixes canonical fields and identity normalization; fresh critic retest |
| 2026-08-25 | M2 | FIX -> CRITIC | M2 builder aligned canonical headers, added explicit legacy aliases, fixed SKU normalization and independent OEM/manufacturer keys; focused tests now pass 7/7 with compileall/Ruff/CLI evidence | Await fresh M2 round-2 critic |
| 2026-08-25 | M1 | BUILDING -> CRITIC | Schema builder returned Vehicle Engine, Item Vehicle Fitment, Customer Vehicle engine-model link, validation, and static evidence; focused Frappe run remains unverified under concurrent Docker tests | Await fresh M1 critic; M3 continues building |
| 2026-08-25 | M1 | CRITIC -> FIX | Fresh schema critic passed schema/validation/permissions but failed G1.6 because compatibility/import consumers use item_code, vehicle_engine, from_year/to_year/status instead of canonical item, engine_model/vehicle_engine, year_from/year_to/verification_status | M3 and M2 builders reconcile interfaces; fresh critics retest |
| 2026-08-25 | M2 | FIX -> CRITIC -> PASSED | Corrected native ERPNext Item headers to `default_item_manufacturer`/`default_manufacturer_part_no`, added native Item Manufacturer child template, retained legacy source aliases, and passed 8 focused tests; fresh critic PASS | M4 integration |
| 2026-08-25 | M3 | BUILDING -> CRITIC -> FIX | Fresh critic found public compatibility decorators did not explicitly constrain methods to GET | Change both whitelists to `methods=["GET"]`; retain runtime and permission checks |
| 2026-08-25 | M3 | FIX -> CRITIC -> PASSED | Both compatibility methods now declare GET-only whitelists; fresh critic verified permissions, bounded search, canonical fields, ranking, snapshots, and no custom Desk JS | M4 integration |
| 2026-08-25 | M1 | CRITIC -> FIX -> CRITIC -> PASSED | Consumers and regression assertions reconciled to canonical fitment `item`, `vehicle_engine`, `year_from`/`year_to`/`verification_status`, and Customer Vehicle `engine_model`; fresh critic PASS | M4 integration; live Bench verification remains required |
| 2026-08-25 | M4 | BUILDING -> VERIFY | Editable source ownership repaired; both site schemas synced; focused Frappe schema 8/8 and compatibility 9/9; assets built and backend restarted; live metadata, ping, and permission-boundary probes passed; Graphify refreshed | Run full app suite and system critic |
| 2026-08-25 | M4 | VERIFY -> BLOCKED / UNVERIFIED | Full app suite: 215/215 unit tests pass; 75 integration tests have one wkhtmltopdf local-asset HostNotFoundError and one pre-existing v16 parent-scoped child-report permission failure in Parts Interpreter → Jobs Waiting for Parts; 81 unspecified tests pass | Preserve residuals honestly; no image or production gate |

## Current run — Customer LPO Fleet Intake and Consolidated Billing

Goal: implement the approved customer-LPO workflow for vehicle-list-plus-ceiling LPOs, linking one LPO to one Fleet Service Campaign, one Repair Job per vehicle, and one traceable consolidated invoice while preserving ERPNext accounting and existing workshop controls.

Quality bar: LPO-DOMAIN normalized submittable LPO/vehicle/amendment model; LPO-API permission-checked CSV, vehicle-resolution, campaign/job, amendment, summary, and billing actions; LPO-CEILING per-LPO tax-basis enforcement with hard amendment gate; LPO-DESK native approved Frappe form/actions/states; LPO-REPORT permission-aware utilization/progress reports; LPO-PRINT rendered fulfilment/proforma/invoice identity; LPO-RUNTIME test-site and editable-stack migration/build/probe evidence; LPO-E2E three-vehicle corporate acceptance case; LPO-VISUAL authenticated Desk/PDF inspection or explicit capability blocker.

Overall state: SETUP -> BUILDING -> RUNTIME VERIFIED / VISUAL BLOCKED
Current wave: W1 — editable runtime verified; authenticated Desk/PDF visual gate blocked by CDP capability
Required modules: 5 / 5
Active: M5 visual evidence and Aslam editable-stack UAT
Blocked: Authenticated browser CDP handshake/interaction inspection
Whole-system gate: PENDING UAT and visual capability recovery
Parallel now: none; awaiting Aslam UAT and browser capability recovery
Sequential chains: M1 -> fresh critic -> M3 API/billing -> fresh critic -> M4 Desk/reports/prints -> integration -> system critic
Free worker slots: tracked in collaboration roster
Dispatch batch: M1 -> lpo_schema_builder; M2 -> lpo_contract_builder
Last update: 2026-08-25 setup

| ID | Output | Depends on | Quality gate | Owner | Round | Status | Last verdict | Largest gap | Evidence | Next action |
|---|---|---|---|---|---:|---|---|---|---|---|
| M1 | Customer LPO, Customer LPO Vehicle, Customer LPO Amendment schemas/controllers/permissions and isolated tests | None | LPO-DOMAIN | lpo_schema_builder | 1 | PASSED | PASS | End-to-end user submission remains UAT scope | JSON/compile/Ruff plus fresh critic PASS; focused DocType tests and editable metadata/migration pass | Aslam UAT |
| M2 | Customer LPO specification and native Frappe design note | None | LPO-DESIGN | lpo_contract_builder | 1 | PASSED (static) | PASS | Native Desk/PDF visual gate remains unobserved | Markdown/contract coverage plus fresh critic PASS | Use design contract for implementation |
| M3 | CSV/vehicle resolution, campaign/job creation, ceiling enforcement, and billing trace integration | M1 | LPO-API/LPO-CEILING | Bro | 2 | PASSED | PASS | Three-vehicle corporate UAT remains | Fresh critic PASS; focused workflow suite 12/12, existing billing/regression suites pass, test-site runtime and live permission/metadata checks pass | Aslam UAT |
| M4 | Native Desk actions, reports, workspace links, and print formats | M2, M3 | LPO-DESK/LPO-REPORT/LPO-PRINT | Bro | 2 | PASSED (static/runtime) | PASS | Authenticated screenshot/PDF inspection blocked by CDP timeout | Fresh M4 critic PASS; UI contracts 5/5; dashboard override accepts Frappe's `data` keyword; authenticated live metadata HTTP 200 with no TypeError; asset build and HTTP asset 200 pass | Aslam hard-refresh confirmation; retry visual gate when browser capability is available |
| M5 | Integrated migrations, tests, build, editable-stack runtime, UAT and visual evidence | M1, M2, M3, M4 | LPO-RUNTIME/LPO-E2E/LPO-VISUAL | Bro | 1 | BLOCKED / UNVERIFIED | PARTIAL | Page.captureScreenshot timed out; Desk/PDF visual inspection not evidenced | Test-site regressions, dev migration, backend restart/cache clear, asset build, ping/asset 200, metadata probes, and authenticated Customer LPO `getdoctype` HTTP 200 without TypeError pass; image gate preserved | Aslam UAT editable stack; retry visual gate when browser capability is available |

### Customer LPO run event log

| When | Module | Transition | Evidence or decision | Unlocked / next |
|---|---|---|---|---|
| 2026-08-25 | Run | SETUP -> BUILDING | User explicitly requested implementation; scope locked to LPO vehicle list plus ceiling, per-LPO tax basis, hard amendment gate, table plus CSV intake, one consolidated invoice; no image/production deployment | Dispatch independent docs and schema builders |
| 2026-08-25 | M1/M2 | BUILDING -> PASSED (static) | Schema/design builders returned; fresh critic PASS; JSON, compile, Ruff, and contract checks pass; runtime remains unobserved | Integrate API/billing and native Desk/report/print slices |
| 2026-08-25 | M3/M4 | BLOCKED -> BUILDING | Lead integrated CSV/file intake, explicit confirmed vehicle creation, one-to-one Campaign/Repair Job creation, LPO trace fields, ceiling hooks/row lock, native Desk actions, reports, and A4/proforma/invoice formats; static checks pass | Fresh M3/M4 critics, then test-site runtime |
| 2026-08-25 | M3 | BUILDING -> FIX | Fresh critic found named-target active-document bypass, unscoped amendment aggregation, and missing regression coverage for reassignment/summary permissions/Cashier billing; native mapping and rounding fixes otherwise passed | Apply guard/query/test fixes; fresh critic retest |
| 2026-08-25 | M3 | FIX -> PASSED (static/critic) | Fresh retest critic verified always-on active-document query with current-target exclusion, permission-scoped amendments, native SO->SI mapping, zero-rounded-total handling, Cashier read/create path, and regression coverage; runtime still pending | Run focused runtime tests after migration |
| 2026-08-25 | M4 | BUILDING -> FIX | Fresh Desk/report/print critic found missing Add Amendment action, missing native Attach CSV picker, missing Auto Service Admin declarations, and Cashier excluded from Fleet & History discovery; four tabs, HTTP routing, reports, prints, and no-core-edit checks passed | Add native action/file picker, role declarations, Cashier workspace access; fresh M4 retest |
| 2026-08-25 | M4 | FIX -> PASSED (static/critic) | Fresh M4 retest PASS after amendment action gating, native file picker support, Admin/report permissions, and Cashier workspace visibility; live Desk/PDF inspection remains pending | Run editable runtime and visual gate |
| 2026-08-25 | M5 | BLOCKED -> BUILDING | Test-site migration and focused runtime regressions passed; editable dev-site migration completed without error; backend restart, asset build, live probes, and visual inspection remain | Complete runtime/build/visual evidence, then pause for Aslam UAT |
| 2026-08-25 | M5 | BUILDING -> RUNTIME VERIFIED / VISUAL BLOCKED | Dev migration exited cleanly; backend restarted and cache cleared; app assets built; `/api/method/ping` returned 200; Customer LPO JS returned 200; live metadata confirmed LPO DocTypes, trace links, Cashier select access, Admin read access, and Fleet & History workspace. Browser session opened `/desk/customer-lpo` on localhost, but Page.captureScreenshot timed out; no direct Desk/PDF visual claim made | Aslam UAT editable stack; retry browser/PDF inspection when screenshot capability is available; no image build |
| 2026-08-25 | M4 | USER REPRO -> FIX -> VERIFIED | Reproduced `get_data() got an unexpected keyword argument 'data'` by invoking the registered Customer LPO dashboard override with Frappe's `data` keyword. Changed the signature to `get_data(data=None)`, added a regression, synced source, restarted backend, cleared cache, and called the authenticated live `frappe.desk.form.load.getdoctype` endpoint: HTTP 200, Customer LPO metadata present, TypeError absent. Focused UI contracts pass 5/5 | Aslam hard-refresh and confirm the LPO Desk route; no image build |
