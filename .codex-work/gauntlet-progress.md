# Job Card Print Gauntlet

Goal: verified A4 Job Card print format matching the supplied structural references.

Quality bar: complete customer/vehicle data, original bottom-left top-down diagram, Walkaround markers, configurable terms/signatures, stable long-job pagination, real Print View/PDF inspection, and focused/full regression checks.

Overall state: WHOLE-SYSTEM GATE BLOCKED / UNVERIFIED
Current wave: M5 runtime/render evidence
Required modules: 5 / 5 implemented; runtime visual gate pending
Active: M5 local render recovery
Blocked: M5 PDF render by backend container process wait
Whole-system gate: PENDING
Parallel now: M2, M3
Sequential chains: M1 -> M2/M3 -> M4 -> M5
Free worker slots: to be checked before dispatch
Dispatch batch: lead owns M1
Last update: 2026-08-23 setup

| ID | Output | Depends on | Quality gate | Owner | Round | Status | Last verdict | Largest gap | Evidence | Next action |
|---|---|---|---|---|---:|---|---|---|---|---|
| M1 | Design contract and tracker | None | Direction persisted before visual edits | Lead | 1 | PASSED | PASS | none | Fresh critic matched persisted lines 5-77 and 3-31 | Unblock M2/M3 |
| M2 | Snapshot, settings, Jinja context | M1 | Data tests and safe fallback | Builder/Lead | 1 | PASSED | PASS | ERPNext Customer uses `customer_primary_contact` in this checkout | `test_printing` 8/8; live HTML render reached complete customer/vehicle/service output after field fix | Integrated PDF render |
| M3 | A4 template and diagram asset | M1 | Template contract and print layout | Lead | 1 | PASSED | PASS | none after Jinja namespace fix | `test_phase6_contracts` 27/27; SVG and template source checks pass | Integrated PDF render |
| M4 | Regression/render tests | M2, M3 | Focused tests and representative PDFs | Lead | 1 | PASSED | PASS | PDF process state became unhealthy after HTML success | `test_printing` 8/8; `test_phase6_contracts` 27/27; local py_compile passed | M5 runtime evidence |
| M5 | Integrated visual/runtime proof | M4 | Fresh whole-system critic PASS | Lead | 1 | BLOCKED | UNVERIFIED | Backend container blocks new Frappe/PDF worker processes before render; stack restart ended with existing DB zombie warning | HTML print output was captured and inspected semantically; PDF/image inspection not completed | Recreate healthy backend/db process, render PDF, inspect pages |

## Events

| When | Module | Transition | Evidence or decision | Unlocked / next |
|---|---|---|---|---|
| 2026-08-23 | M1 | SETUP -> BUILDING | Existing graph and dirty worktree inspected; user-owned unrelated changes protected | M1 critic |
| 2026-08-23 | M1 | CRITIC -> PASSED | Fresh critic verified the design contract and tracker against the M1 quality bar | M2 and M3 READY |
| 2026-08-23 | M2/M3 | BUILDING -> CRITIC | Builder delegation stalled after source landed; lead recovered the deleted template and completed the disjoint visual slice | M2 and M3 fresh critics |
| 2026-08-23 | M2 | CRITIC -> PASSED | Focused context tests passed 8/8; real Print View HTML exposed and fixed the live `Customer.customer_primary_contact` field name | M4 |
| 2026-08-23 | M3 | CRITIC -> PASSED | Contract suite passed 27/27 after fixing Jinja loop scope and retaining the diagram asset contract | M4 |
| 2026-08-23 | M4 | CRITIC -> PASSED | Focused regression suites passed; local Python compile passed; representative HTML render contained full customer/vehicle/service sections and diagram URL | M5 runtime evidence |
| 2026-08-23 | M5 | BLOCKED / UNVERIFIED | PDF harness could not proceed: backend spawned Python processes entered uninterruptible wait before stage output; non-destructive stack restart ended with Docker reporting the existing DB container as a zombie | User UAT after healthy stack render |
| 2026-08-23 | M3 | ASSET REVISION | Replaced the generated vehicle diagram with Aslam's supplied vector asset; host and backend SHA-256 match | Re-run PDF/image inspection when renderer is healthy |
| 2026-08-23 | DEPLOYMENT | SYNC + MIGRATE | Exact SVG synced to `dms-backend-1`; `auto-service.localhost` migration completed through `after_migrate`; nginx served the SVG with HTTP 200; migrated snapshot/terms fields confirmed | PDF/image inspection remains |
| 2026-08-23 | DEPLOYMENT | CACHE-BUST + REBUILD | Print context now uses versioned `vectorised-bb109a99.svg`; app build, clear-cache, backend restart, and live Nginx hash verification passed | PDF/image inspection remains |
