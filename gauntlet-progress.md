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
