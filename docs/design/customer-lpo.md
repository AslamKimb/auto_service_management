# Customer LPO Native Desk Design Contract

## Decision

Customer LPO uses native Frappe v16 Desk surfaces inside the existing Car Workshop information architecture. It is a commercial intake and reconciliation document above `Fleet Service Campaign`; it does not become a custom portal, Vue shell, or replacement for the Repair Job form.

Implementation routing starts with `frappe-router` and `frappe-project-triage`, then uses `frappe-doctype-development` for the native DocTypes, `frappe-api-development` for typed POST/GET actions, `frappe-ui-patterns` and `frappe-desk-customization` for Desk behavior, `frappe-printing-templates` for A4/Jinja outputs, `frappe-reports` for utilization/progress reports, and `frappe-testing` for contract and rendered-evidence checks. The router must be re-entered if the implementation changes from native Desk to a portal or custom frontend.

## Intent and audience

The form helps a Service Advisor turn a company LPO into a controlled batch of vehicle visits. Workshop Managers need authority and exception visibility. Cashiers need a safe path to one consolidated invoice. Technicians, Parts Interpreters, and Security Gate Officers continue using their existing Repair Job, stock, and Gate Pass surfaces without being exposed to LPO financial controls.

The visual objective is calm commercial control: make the original attachment, customer, vehicle count, ceiling basis, remaining authority, and next action obvious without hiding the per-vehicle operational trail.

## Reference direction and principles

- Use the approved native Frappe/ERPNext form language from `car-workshop-navigation.md` and `repair-job-form-layout.md`.
- Use the active Frappe/ERPNext theme, typography, status colors, native icons, link pickers, tables, dashboards, dialogs, alerts, and permission filtering. Do not hard-code a new palette or add global CSS.
- Keep the commercial parent compact; put vehicle detail in the table and operational detail in the linked Repair Jobs.
- Show authorization and invoice reconciliation as read-only calculated values. The UI may explain a gate, but the server remains the authority.
- Keep the original LPO attachment visible as evidence and keep amendment history append-only through submitted documents.

## Information architecture

The Customer LPO form uses four native `Tab Break` fields in this order:

1. **Details** — Company, Customer, external LPO number, issue/expiry dates, currency, ceiling basis, original amount, contact, instructions, original attachment, status, and linked Fleet Service Campaign.
2. **Vehicles** — child table with registration, Customer Vehicle, requested work, planned date, allocated ceiling, Repair Job, row status, and remarks. Place CSV actions immediately above the table.
3. **Financials** — original/effective authorization, committed amount, invoiced amount, paid amount, remaining amount, amendment list, consolidated Sales Order/Proforma, and consolidated Sales Invoice.
4. **Connections** — native dashboard links to the Campaign, Repair Jobs, Customer Vehicles, Amendments, Sales Order, and Sales Invoice.

The list view should expose external LPO number, Customer, issue date, effective expiry, status, ceiling basis, effective amount, invoiced amount, remaining amount, and vehicle progress. Status indicators must follow Frappe/ERPNext conventions. The existing `Fleet & History` workspace receives a Customer LPO shortcut and a number card for active LPOs; the Reports workspace receives the two LPO reports.

## Actions and interaction states

Native grouped actions are permission- and status-aware:

- `Import Vehicles` opens a native file dialog with the exact CSV header example.
- `Preview CSV` shows normalized rows, matched/unresolved vehicles, duplicates, and row/column errors without saving.
- `Resolve Vehicles` requires explicit confirmation before creating a minimal Customer Vehicle.
- `Create Campaign & Jobs` is available only after LPO submission and creates/reuses one Campaign and one Repair Job per resolved vehicle.
- `Create Proforma` and `Create Invoice` show selected billable component counts, total under the chosen Tax Inclusive/Tax Exclusive basis, and the remaining ceiling before the server call.
- `Add Amendment` opens the native submittable Amendment form; it cannot edit Customer, Company, currency, or ceiling basis.
- `Close LPO` explains unresolved jobs/components when the close gate fails.

The design must visibly handle:

- Draft with no attachment, no rows, or unresolved vehicles.
- Populated table with long registration/work text and mixed job statuses.
- CSV loading, valid preview, duplicate rows, malformed dates, invalid numeric allocation, cross-customer match, and atomic import failure.
- Empty Financials/Connections dashboards and permission-filtered links.
- Active, expired, exhausted, cancelled, and completed LPOs.
- Over-ceiling billing with the exact excess and required Amendment action.
- Successful Campaign/Job creation, successful consolidated invoice creation, and duplicate-action/idempotency feedback.
- Permission-denied actions without leaking hidden totals or linked documents.

## Layout, density, and responsive behavior

Use the native Frappe two-column field density inside Details and Financials. Keep the Vehicles table readable at desktop width and let native Frappe table scrolling/stacking handle narrow screens. Do not create a second mobile navigation pattern.

At narrow widths, the attachment, status, remaining authority, and primary action must remain discoverable without horizontal page clipping. Long text may wrap in table cells; identifiers and amounts must remain legible. Tabs, buttons, link pickers, table controls, alerts, and dashboards must retain keyboard order and native focus states.

## Accessibility and content rules

- Use concise labels: `External LPO No.`, `Ceiling Basis`, `Effective Authorization`, `Remaining Amount`, and `Vehicle Progress`.
- Use help text for the difference between Tax Inclusive and Tax Exclusive; do not rely on color alone.
- Every CSV error identifies row, column, and correction.
- Every ceiling failure names authorized, proposed, excess, and amendment requirement.
- Every empty state explains the next valid action.
- Preserve native required indicators, read-only affordances, role filtering, focus order, and screen-reader-readable tab labels.
- No invented customer claims, prices, approvals, vehicle data, or financial outcomes in sample content.

## Print and report presentation

The A4 `Customer LPO Fulfilment Summary` uses the existing workshop print language: clear title, company/customer/LPO identity, original attachment reference, ceiling basis, original and amended authority, per-vehicle rows, linked Repair Job status, billed total, remaining amount, and signature/notes area. Consolidated Proforma and Sales Invoice prints show the LPO number and retain the existing per-line Repair Job and Customer Vehicle traces.

Reports use native Frappe filters and tables:

- `Customer LPO Utilization`: customer, date, status, authority, billed/paid/remaining amounts, vehicle counts, and expiry.
- `Customer LPO Vehicle Progress`: LPO, registration, Customer Vehicle, Repair Job, requested work, planned date, job status, and billed amount.

The reports and print must remain permission-aware and readable when no rows match.

## Evidence gate

This is a design contract, not a visual implementation or runtime result. Before the feature can be called visually verified, `frappe-testing` must pair static/contract checks with direct authenticated Desk inspection at a desktop viewport and `390x844`, including all states above, keyboard/focus checks, long-table behavior, action/permission behavior, and successful invoice flow. The fulfilment, Proforma, and Invoice outputs must be rendered and inspected as HTML/PDF. Each pass records runtime, viewport, state, interaction, observed result, defect, fix, and retest. A screenshot without live interaction evidence is insufficient for interactive behavior.

## Acceptance

- Native Customer LPO form uses the four approved tabs and no custom shell.
- A user can see the original attachment, enter vehicles in a table or validated CSV flow, and understand unresolved-row errors.
- The form makes the one LPO → one Campaign → one Repair Job per vehicle relationship visible through row links and Connections.
- Financials make the per-LPO Tax Inclusive/Tax Exclusive basis, amendment effect, and remaining ceiling understandable.
- Actions are grouped, role-filtered, keyboard-reachable, and provide native empty/loading/error/success feedback.
- Rendered prints and reports preserve the LPO-to-vehicle-to-job-to-invoice audit trail.
- No visual PASS is claimed by this documentation-only slice; the evidence gate remains pending implementation.
