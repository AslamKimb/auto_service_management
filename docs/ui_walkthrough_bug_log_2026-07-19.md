# DMS UI Walkthrough Bug Log - 2026-07-19

## Scope

- Browser: Chrome plugin, headed UI.
- Site: `http://auto-service.localhost:8080`
- Playbook: `docs/role_ui_walkthrough_2026-06-30.md`
- User used for UI execution: `Administrator`
- Records exercised: `RJ-2026-00028`, `RJ-2026-00023`, `RJS-2026-00043`

## Bugs Found

### Fix Verification Update - 2026-07-19

| Status | Area | Verification |
| --- | --- | --- |
| Fixed | Role/workspace link | `/desk/vehicle-service-history` now redirects to `/desk/query-report/Vehicle%20Service%20History`. |
| Fixed | Security reports | Security Gate Officer can open `Vehicle Service History` and `Gate Pass Register`. |
| Fixed | Repair Job intake | Headed UI saved `RJ-2026-00044` with `Odometer In (km) = 98,765`. |
| Fixed | Repair Job actions | Approved job `RJ-2026-00028` no longer shows invalid `Create Quality Check` or premature `Create Gate Pass`. |
| Fixed | Billing workflow | Ready for Invoice job `RJ-2026-00023` shows `Create > Sales Invoice`. |
| Fixed | Service creation | `Services > Create Service` opens Repair Job Service with `repair_job = RJ-2026-00023`. |
| Fixed | Primary action label | Saved Repair Job form shows visible `Actions` label at desktop width. |
| Fixed | Realtime | Fresh headed Chrome Desk load had no Socket.IO/origin/polling/auth console errors; nginx logged successful `/socket.io` polling after routing websocket auth through Docker-internal `backend:8000` headers. |

| Area | Bug | Evidence |
| --- | --- | --- |
| Realtime | Socket.IO repeatedly fails with `Invalid origin`. | Browser console on Desk load logs `Error connecting to socket.io: Invalid origin` from `desk.bundle.OBHPYFFY.js`. |
| Role/workspace link | Direct route `/desk/vehicle-service-history` shows `Page vehicle-service-history not found`. | Security Gate Officer surface probe hit `Not found`; exact workspace query-report route `/desk/query-report/Vehicle%20Service%20History` works. |
| Repair Job intake | New Repair Job cannot be saved after filling the visible `Odometer In (km)` field. | On `/desk/repair-job/new-repair-job-cxekwgdsla`, visible input `odometer_in = 12345`, but save returns `Missing Fields: Odometer In (km) is required`. Retried with `Tab` blur, same result. |
| Repair Job form | Header status badge shows Frappe document status `Draft` instead of business workflow status. | `RJ-2026-00028` shows header `Draft` while field `Status = Approved`; `RJ-2026-00023` shows header `Draft` while field `Status = Ready for Invoice`. |
| Repair Job actions | Primary Actions button is visually blank/narrow on saved Repair Jobs. | On `RJ-2026-00028`, visible primary button has `data-label="Actions"` in HTML but rendered text is empty and width is about 40px. |
| Service creation | `Services > Create Service` opens a Repair Job Service form with `Repair Job` blank. | From `RJ-2026-00028`, new service page copied Customer, Vehicle, and Bay but showed `Repair Job: Begin typing for results`. |
| Service creation | Repair Job Service can be saved while the visible `Repair Job` link is blank. | `RJS-2026-00043` saved from the Create Service action before the source job was visibly linked. Submit later backfilled `Repair Job = RJ-2026-00028` and `Diagnosis Report = DR-2026-00030`. |
| QC action gating | `Create Quality Check` is offered on an Approved job that the server rejects. | `RJ-2026-00028` menu offered `Related Documents > Create Quality Check`; saving QC returned `Quality Check can only be created when the Repair Job is in 'In Repair', 'Quality Check', or 'Billing' state. Current: Approved`. |
| QC creation | `Create Quality Check` opens a QC form with `Repair Job` blank. | From `RJ-2026-00028`, new QC page copied Vehicle `UBA 482M` but showed `Repair Job: Begin typing for results`. |
| Billing workflow | Ready for Invoice job has no visible `Create Sales Invoice` action. | `RJ-2026-00023` menu had `Related Documents > Sales Invoices` but no create invoice action. |
| Gate Pass action gating | `Create Gate Pass` is offered before invoice coverage is satisfied. | `RJ-2026-00023` menu offered `Related Documents > Create Gate Pass`; saving returned `Every billable component ... must be covered by a submitted Sales Invoice before issuing a Gate Pass.` |
| Gate Pass creation | `Create Gate Pass` opens a form with `Repair Job` and `Sales Invoice` blank. | From `RJ-2026-00023`, new Gate Pass copied Vehicle `TEST-PH7-001` but showed `Repair Job: Begin typing for results` and `Sales Invoice: Begin typing for results`. |
| Security Gate Officer reports | Security Gate Officer cannot access `Gate Pass Register` report. | As `walkthrough.security.gate@example.com`, `/desk/query-report/Gate%20Pass%20Register` shows `You don't have access to Report: Gate Pass Register`. |
| Security Gate Officer reports | Security Gate Officer cannot access `Vehicle Service History` report. | As `walkthrough.security.gate@example.com`, `/desk/query-report/Vehicle%20Service%20History` shows `You don't have access to Report: Vehicle Service History`. |

## Surfaces Checked

| Surface | Result |
| --- | --- |
| Workshop Management workspace | Loaded |
| Customer Vehicle list | Loaded |
| New Repair Job | Loaded, blocked by `Odometer In` validation bug |
| Customer Authorization list | Loaded |
| Open Repair Jobs report | Loaded |
| Repair Job list | Loaded |
| Quality Check list | Loaded |
| Jobs by Status report | Loaded |
| Jobs Waiting for Parts report | Loaded |
| Sales Invoice list | Loaded |
| Gate Pass list | Loaded |
| Vehicle Service History report | Loaded through query-report route |
| Gate Pass Register report | Loaded |
| Corporate Credit Releases report | Loaded |
| Discount and Price Change Audit report | Loaded |
| Daily Workshop Load report | Loaded |
| Technician Productivity report | Loaded |
| Labour Hours by Technician report | Loaded |
| Parts Used by Repair Job report | Loaded |
| Delayed Jobs report | Loaded |
| Repair Revenue by Period report | Loaded |

## Persona UI Checks

| Role | Login | Playbook surfaces checked | Result |
| --- | --- | --- | --- |
| Service Advisor | Passed | Workspace, Customer Vehicle, New Repair Job, Customer Authorization, Open Repair Jobs | All role surfaces loaded. New Repair Job save is still blocked by the `Odometer In` bug above. |
| Workshop Manager | Passed | Workspace, Repair Queue, QC Queue, Jobs by Status | All role surfaces loaded. |
| Parts Interpreter | Passed | Workspace, Jobs Waiting for Parts, Repair Queue | All role surfaces loaded; Parts Queue rendered rows. |
| Cashier | Passed | Workspace, Sales Invoice, Jobs by Status | All role surfaces loaded; Sales Invoice list rendered rows. |
| Security Gate Officer | Passed | Workspace, Gate Pass, Gate Pass Register, Service History, Vehicle Service History | Workspace, Gate Pass, and Service History loaded. Gate Pass Register and Vehicle Service History report links were blocked by report permission errors. |

## Persona Setup

- `walkthrough.service.advisor@example.com`
- `walkthrough.workshop.manager@example.com`
- `walkthrough.parts.interpreter@example.com`
- `walkthrough.cashier@example.com`
- `walkthrough.security.gate@example.com`

Each walkthrough user was verified as enabled, `System User`, with `default_workspace = "Workshop Management"`, password `admin`, and its target role plus `Desk User`.

## Workflow Coverage

- Intake/new Repair Job: attempted through UI; blocked by `Odometer In` not committing to save validation.
- Service creation/submission: exercised from existing Approved job; service creation route works but shows incomplete source-link state.
- QC creation: exercised from Approved job; UI offers invalid action, server blocks correctly.
- Billing/invoice: Ready for Invoice job inspected; no create invoice action found in menu.
- Gate Pass/release: exercised from Ready for Invoice job; UI offers action early, server blocks correctly until invoice coverage exists.
- Reports and role shortcuts: workspace/report routes checked with exact workspace links.

## Notes

- The first workflow pass was done as `Administrator` to exercise end-to-end records and action menus. The follow-up role pass was completed as the five dedicated walkthrough personas.
- Browser Harness was initially blocked by Chrome remote-debugging permission, then the test was retried successfully through the bundled Chrome plugin in headed Chrome.
