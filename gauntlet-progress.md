# Gauntlet Loop — Repair Job Sales Order Proforma

Goal: replace app-facing Repair Job quotation creation with selectable Sales Orders, preserve both invoice paths, show all linked Sales Orders on Repair Job, and print all Sales Orders as Proforma Invoice.

Quality bar: no app quotation creation actions; selected billable service components map into a reviewable Sales Order; duplicate drafts are allowed but only one overlapping order may be submitted/billed; direct and native Sales Invoice paths preserve Repair Job/Sales Order traceability; related Sales Orders remain visible; HTML/PDF print output says Proforma Invoice; focused and full tests, migration, asset build, and live Desk inspection pass.

Overall state: CRITIC
Current wave: W1 — backend and native UI/print builders
Required modules: 2 / 3
Active: M3 (integration and whole-system verification)
Blocked: browser/PDF inspection gate
Whole-system gate: PENDING
Parallel now: M1, M2
Sequential chains: M1 + M2 -> fresh critics -> integration -> whole-system critic
Free worker slots: 3
Dispatch batch: M1 -> backend_sales_order; M2 -> ui_print_proforma
Last update: M1 and M2 fresh critics passed; integration checks green; browser CDP/PDF inspection remains blocked

| ID | Output | Depends on | Quality gate | Owner | Round | Status | Last verdict | Largest gap | Evidence | Next action |
|---|---|---|---|---|---:|---|---|---|---|---|
| M1 | Backend mapper, schema, lifecycle, sync | None | Component/order/invoice contract tests | backend_sales_order | 1 | PASSED | PASS | Live end-to-end document creation still belongs to M3 | Current-source hashes match; backend contract 4/4, Phase10 mapping 37/37, reversed native invoice-row trace regression pass; no quotation creation controller/UI action | Integration and whole-system gate |
| M2 | Native Desk selector, actions, Proforma print behavior | M1 interface names only | JS, print, HTML/PDF contracts | ui_print_proforma | 1 | PASSED | PASS | Live Desk/PDF still pending integration gate | focused contracts 3/3, node/compile/JSON pass, fresh critic confirms render targets and no stale quotation UI | Unlock M3 after M1 critic |
| M3 | Integration and whole-system verification | M1 + M2 | Full app, migration, browser, PDF | lead + fresh critics | 1 | CRITIC | UNVERIFIED | Browser CDP handshake blocks live selector/PDF inspection; full app suite has one unrelated legacy Job Card SVG metadata assertion still failing | Test-site schema/heading verified directly; dev GET returned 3 selectable components; live Repair Job Create menu was observed with Proforma Invoice (Sales Order) and no Quotation; asset build passed; 129/130 unit tests and all 66 integration tests reached completion, with only the pre-existing Job Card asset-contract failure | Restore CDP, inspect selector/draft/PDF, then decide whether to repair or separately track the Job Card contract |

## Events

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
