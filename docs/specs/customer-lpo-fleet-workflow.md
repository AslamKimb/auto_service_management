# Customer LPO Fleet Workflow Specification

## Status

Approved documentation contract for a future Frappe and ERPNext `version-16` implementation in `auto_service_management`. This slice defines the product and implementation boundary only; it does not change source code, fixtures, progress ledgers, or the running site.

## Objective and boundaries

Support a company that sends an LPO listing vehicles for workshop work. The LPO is the commercial authorization and ceiling for one batch; each vehicle remains an independent workshop visit.

```text
Customer LPO
  → one Fleet Service Campaign
      → one Customer Vehicle row and one Repair Job per vehicle
          → normal inspection, diagnosis, repair, billing, payment, and Gate Pass flow
              → one consolidated Sales Order/Proforma and one consolidated Sales Invoice
```

The feature must not merge vehicles into one Repair Job, replace ERPNext accounting, make optional `Customer Authorization` a fleet-level ceiling, or introduce a custom portal, OCR, multi-currency conversion, or Frappe/ERPNext core edits.

The existing `Fleet Service Campaign` remains the operational parent for separate jobs. The new `Customer LPO` becomes the commercial parent and source document. The original customer LPO attachment is authoritative evidence; staff manually capture its structured fields and vehicle list.

## Frappe routing contract

Every implementation phase starts with `frappe-router`. The router first runs `frappe-project-triage` to confirm Frappe/ERPNext v16, installed apps, site names, developer mode, and available Docker/bench tooling. Before coding against a changing Frappe or ERPNext API, refresh official documentation through `context7-cli`.

| Workstream | Router-selected skills | Contract output |
|---|---|---|
| Domain and lifecycle | `frappe-enterprise-patterns` → `frappe-doctype-development` | LPO, vehicle-row, amendment, status, and invariants are locked before schema work. |
| DocTypes and permissions | `frappe-doctype-development` → `frappe-testing` | Native submittable DocTypes, child tables, links, permissions, validation, and migration-safe tests. |
| RPC and ERPNext mapping | `frappe-api-development` → `frappe-enterprise-patterns` → `frappe-testing` | Typed, permission-checked, POST-only mutations; GET-only previews/summaries; native Sales Order/Invoice mapping and trace preservation. |
| Desk forms and actions | `frappe-ui-patterns` → `frappe-desk-customization` → `frappe-testing` | Native Frappe forms, table intake, CSV dialog, grouped actions, indicators, dashboards, and permission-aware states. |
| Prints and reports | `frappe-printing-templates` and `frappe-reports` → `frappe-testing` | LPO fulfilment print, utilization/progress reports, filters, permissions, and rendered evidence. |
| Environment and verification | `frappe-manager` → `frappe-project-triage` → `frappe-testing` | Site-specific Docker/bench checks using explicit `--site`; no image or production work before approval. |

`frappe-frontend-development` and `frappe-web-forms` are not part of v1: the approved surface is native Desk, not a Vue portal or public form. `frappe-integrations` is not required because no third-party integration is included.

## Domain model

### Customer LPO

Create a submittable app-owned `Customer LPO` with naming series `LPO-{YYYY}-{#####}`. It contains:

- Company, Customer, external LPO number, issue date, original expiry date, currency, ceiling basis, original authorized amount, customer contact, instructions, source LPO attachment, and linked Fleet Service Campaign.
- Calculated effective authorization, committed amount, invoiced amount, paid amount, remaining amount, vehicle counts, and server-controlled operational status.
- Status values: `Draft`, `Active`, `Exhausted`, `Completed`, `Expired`, `Cancelled`.
- A unique external LPO number within the same Company and Customer. The same number for another customer is allowed.
- Required source attachment, at least one vehicle row, positive authorized amount, valid dates, and resolved Customer Vehicles before submission.
- One LPO currency only. Sales Order and Sales Invoice currency must match; currency conversion is out of scope.

`ceiling_basis` is required per LPO and has exactly two values: `Tax Inclusive` or `Tax Exclusive`. It cannot be changed after submission. Amount amendments use the same currency and basis.

### Customer LPO Vehicle

Add a child table with:

- Registration number, Customer Vehicle, requested work, planned date, optional allocated ceiling, linked Repair Job, row/job status, and remarks.
- Registration normalized for comparison and unique within the LPO.
- A Customer Vehicle that belongs to the LPO Customer. A cross-customer vehicle is rejected.
- An unresolved registration may be linked to an existing Customer Vehicle or become a minimal new Customer Vehicle only after explicit confirmation; submission requires every row resolved.
- At most one linked Repair Job per row. At most one LPO row per Customer Vehicle. The row and job remain traceable if work is cancelled.
- After a Repair Job exists, removing the row is not a silent delete; the existing Repair Job cancellation path and audit trail are required.

The primary invariant is strict:

```text
one Customer LPO
  = one Fleet Service Campaign
  = one LPO vehicle row per vehicle
  = one Repair Job per vehicle row
```

The Campaign still groups independent jobs. Each job keeps its own Project, service lines, optional evidence, stock/labour, invoice traces, payment/release controls, and Service History.

### Customer LPO Amendment

Create a separate submittable `Customer LPO Amendment` with the parent LPO, external amendment/reference number, issue date, amount increase, optional replacement expiry date, reason, and amendment attachment.

- An amendment must increase the authorized amount, extend expiry, or do both.
- Only a submitted amendment affects authorization or expiry.
- Customer, Company, currency, and ceiling basis cannot change.
- Effective authorization is the original amount plus submitted amendment increases.
- Effective expiry is the original expiry unless a submitted amendment replaces it with a later valid date.
- Cancelling an amendment is blocked when the resulting authorization would make an existing non-cancelled Sales Order or submitted Sales Invoice exceed the LPO ceiling.
- `Customer Authorization` may approve a Repair Job scope but never raises the LPO ceiling. Over-ceiling work requires a submitted LPO Amendment.

### Existing document links

Add app-owned links from `Fleet Service Campaign`, `Repair Job`, `Sales Order`, and `Sales Invoice` to `Customer LPO`. The existing campaign/item trace fields remain authoritative for vehicle, job, service, component, and Project lineage; do not create a second accounting ledger.

The LPO-owned billing action allows one active consolidated Sales Order/Proforma and one active consolidated Sales Invoice per LPO. Cancelled documents may be replaced. A draft may be reviewed and corrected, but a second active LPO-level document is rejected.

### Canonical field contract

Use these fieldnames unless an existing Frappe/ERPNext field collision requires an app-owned prefix:

| Document | Required fieldnames |
|---|---|
| Customer LPO | `company`, `customer`, `lpo_number`, `issue_date`, `expiry_date`, `currency`, `ceiling_basis`, `authorized_amount`, `source_lpo`, `work_instruction`, `vehicle_rows`, `fleet_service_campaign`, `status`. |
| Customer LPO calculated values | `effective_authorized_amount`, `committed_amount`, `invoiced_amount`, `paid_amount`, `remaining_amount`, `vehicle_count`, `resolved_vehicle_count`; read-only and server-derived. |
| Customer LPO Vehicle | `registration_number`, `customer_vehicle`, `requested_work`, `planned_date`, `allocated_ceiling`, `repair_job`, `status`, `remarks`. |
| Customer LPO Amendment | `customer_lpo`, `external_reference`, `issue_date`, `amount_increase`, `replacement_expiry`, `reason`, `source_attachment`. |
| Cross-document trace | `customer_lpo` on Fleet Service Campaign, Repair Job, Sales Order, and Sales Invoice; existing campaign/item trace fields remain unchanged. |

The attachment fields are the original customer evidence: `source_lpo` on Customer LPO and `source_attachment` on Amendment. They are not generated summaries or OCR output.

## Intake and data flow

### Table intake

The native Customer LPO form supports direct child-table entry. Rows are validated on save and again on submission. The form exposes link search for Customer Vehicle, requested-work text, planned date, optional allocation, and remarks.

### CSV intake

CSV is an intake accelerator, not a second source of truth. The native Desk dialog accepts UTF-8 CSV with this header contract:

```text
registration_number,customer_vehicle,requested_work,planned_date,allocated_ceiling,remarks
```

`registration_number` is required. The other fields are optional except that a row must resolve to a Customer Vehicle before LPO submission. Preview parses and normalizes without mutation; import reparses server-side and appends valid rows atomically. One invalid row rejects the whole import and returns row/column errors. PDF extraction and OCR are out of scope.

### API contract

All methods are app-owned, typed, permission-checked, and resolved through the native controller path. Mutations are POST-only and must not call `frappe.db.commit()`.

| Method | HTTP | Input | Output and rules |
|---|---|---|---|
| `preview_vehicle_csv(lpo_name, csv_text=None, rows=None)` | GET | Draft LPO plus UTF-8 CSV text or normalized row objects | Normalized rows, matched/new/unresolved vehicles, duplicate registrations, and row errors; no mutation. A native file dialog supplies content; the method does not create a server-side file. |
| `import_vehicle_csv(lpo_name, csv_text=None, rows=None)` | POST | Draft LPO plus UTF-8 CSV text or normalized row objects | Atomically appends validated rows; invalid rows leave the LPO unchanged. |
| `resolve_vehicle_rows(lpo_name, row_names=None, create_confirmed=False)` | POST | Draft LPO rows and explicit confirmation flag | Links same-customer vehicles or, only when explicitly confirmed, creates minimal Customer Vehicles; revalidates ownership and duplicates. |
| `create_campaign_and_repair_jobs(lpo_name)` | POST | Submitted LPO | Creates or reuses exactly one Campaign and fills only missing one-to-one Repair Job links. Repeated calls are idempotent. |
| `get_lpo_summary(lpo_name)` | GET | Readable LPO | Permission-scoped totals, status, expiry, amendments, row/job states, Campaign, Sales Order, and Sales Invoice links. |
| `make_sales_order(lpo_name, target_doc=None, component_refs=None)` | POST | LPO, optional draft target, and explicitly selected billable component references | Returns/creates the single reviewable consolidated Sales Order; preserves LPO, Campaign, Vehicle, Repair Job, service, component, and Project traces. |
| `make_sales_invoice(lpo_name, target_doc=None, component_refs=None)` | POST | LPO, optional draft target, and selected component references | Returns/creates the single consolidated Sales Invoice through the existing Campaign mapper or native Sales Order mapping; preserves all traces and applies the ceiling gate. |
| `close_lpo(lpo_name)` | POST | Submitted LPO | Closes only when every linked Repair Job is `Closed` or `Cancelled` and no billable component remains unresolved. |

The server rechecks the LPO, Customer Vehicle, Campaign, Repair Job, and ERPNext sales-document permissions on every call. Client-side visibility is not authorization.

## Workflow and financial controls

```text
Draft
  → submit after attachment, rows, dates, amount, and vehicle resolution pass
Active
  → create/reuse Campaign and one Repair Job per vehicle
  → normal vehicle-by-vehicle workshop flow
  → one consolidated Sales Order/Proforma and one consolidated Sales Invoice
  → Completed after terminal jobs and billing reconciliation
```

Server-controlled transitions also set `Expired` after effective expiry, `Exhausted` when the authorized ceiling is consumed, and `Cancelled` only through validated cancellation. A submitted amendment may restore `Active` when it extends expiry or increases capacity.

For LPO-level billing, `invoiced_amount` is the sum of non-cancelled submitted LPO consolidated invoices; `remaining_amount = effective_authorized_amount - invoiced_amount`. A linked Sales Order is not counted again after its invoice is submitted. Draft estimates remain reviewable and do not become accounting entries.

At Sales Order review/submission and Sales Invoice validation/submission:

- Customer, Company, currency, LPO, Campaign, Repair Job, Customer Vehicle, service, component, and Project traces must agree with authoritative source rows.
- Expired, cancelled, and completed LPOs cannot receive new billing.
- `Tax Exclusive` compares the proposed document's `net_total` to the remaining ceiling.
- `Tax Inclusive` compares the proposed document's ERPNext payable total (`rounded_total` when rounding applies, otherwise `grand_total`) to the remaining ceiling.
- Sales Invoice submission locks/reloads the LPO and re-evaluates the ceiling to prevent concurrent overbilling.
- An over-ceiling request fails with authorized amount, proposed amount, excess, and the required amendment reference; warning-only overage and manager bypass are out of scope.
- ERPNext remains authoritative for prices, taxes, rounding, stock, payment, credit limits, and ledger postings.

## Roles and permission intent

DocType permissions and server checks must preserve the existing roles:

| Role | Customer LPO intent |
|---|---|
| Service Advisor | Create/edit drafts, attach evidence, enter/import/resolve vehicle rows, read/print/report, and create Campaign/Repair Jobs after submission. No amount/expiry amendment approval. |
| Workshop Manager | Full LPO and Amendment lifecycle, including submit/cancel, exceptions, reports, prints, and billing oversight. |
| Cashier | Read/print/report and create the permitted consolidated Sales Order/Invoice using existing ERPNext selling permissions; cannot change LPO authority or submit Amendments. |
| Technician / Parts Interpreter | No LPO financial access; continue working through assigned Repair Jobs, services, stock, and Timesheets. |
| Security Gate Officer | No LPO editing; continue using Gate Pass as the release control. |
| Auto Service Admin / System Manager | Full access subject to standard Frappe audit and permission behavior. |

Every link and action must enforce same-Customer and same-Company scope. No guest mutation endpoint, client-only permission, or hidden manager override is allowed.

## Desk, reports, and print contract

Use native Frappe Desk only. The Customer LPO form follows the approved native form language:

1. **Details** — customer, external reference, dates, currency, ceiling basis, amount, attachment, contact, and status.
2. **Vehicles** — child table, CSV Import/Preview/Resolve actions, row errors, and job links.
3. **Financials** — original/effective authorization, committed/invoiced/paid/remaining amounts, amendments, and consolidated sales links.
4. **Connections** — native dashboard links to Campaign, Repair Jobs, Customer Vehicles, Sales Order, Sales Invoice, and Amendments.

Required native actions: `Import Vehicles`, `Preview CSV`, `Resolve Vehicles`, `Create Campaign & Jobs`, `Create Proforma`, `Create Invoice`, `Add Amendment`, and `Close LPO`, filtered by permissions and lifecycle. Do not add a custom Vue shell, custom navigation, or global CSS.

Provide a `Customer LPO Utilization` report, a `Customer LPO Vehicle Progress` report, an A4 `Customer LPO Fulfilment Summary` print, and LPO identity/external reference on consolidated Proforma and Sales Invoice prints. Use permission-aware Query Builder or existing report patterns with bounded filters.

## Test and evidence gates

The future implementation uses `frappe-testing` throughout: write failing tests before behavior code, run the smallest focused test after each slice, then the full app suite.

Required automated scenarios:

- Schema, naming, required attachment, submission, cancellation, expiry, status derivation, permissions, and repeat migration.
- Unique external number per Company/Customer, same number across customers, same-customer vehicle enforcement, normalized registration duplicates, and one-row/one-job invariants.
- Table and CSV preview/import, UTF-8 parsing, atomic rejection, row/column errors, existing-vehicle matching, confirmed new-vehicle creation, and idempotent repeated job creation.
- Amendment amount/expiry effects, cancellation safety, effective ceiling calculation, tax-inclusive/exclusive comparisons, rounding, expiry rejection, concurrent invoice lock, and over-ceiling error text.
- One active LPO Sales Order and Invoice, native Sales Order-to-Invoice trace propagation, no duplicate billing, and complete per-line audit trace.
- Role-specific actions, GET/POST method enforcement, permission-scoped summaries/reports, and no controller commits.
- Fresh install, repeat migrate, fixture sync, uninstall/reinstall, and regression of existing Fleet Service Campaign, Repair Job, invoice, payment, and Gate Pass behavior.

The project commands are site-specific and are prescribed for implementation verification only:

```text
docker exec dms-backend-1 bench --site auto-service-test.localhost migrate
docker exec dms-backend-1 bench --site auto-service-test.localhost run-tests --app auto_service_management
docker exec dms-backend-1 bench --site auto-service-test.localhost export-fixtures --app auto_service_management
docker exec dms-backend-1 bench build --app auto_service_management
```

After code changes, the editable non-image stack must be migrated, assets rebuilt, the `--noreload` backend restarted for Python changes, cache cleared, and exact RPC URLs replayed. The result then pauses for explicit Aslam UAT. No image build, registry push, Dokploy change, or production rollout belongs to this contract slice.

Visual evidence is a separate must-pass gate: authenticated native Desk inspection at desktop and `390x844` must exercise new/draft, populated, long-table, empty, loading, CSV-error, unresolved-vehicle, expired, exhausted, over-ceiling, permission-denied, amendment, and successful billing states; keyboard focus, clipping, overflow, readable totals, action visibility, dashboard links, and role boundaries must be recorded. Render and directly inspect the A4 fulfilment, Proforma, and consolidated Invoice outputs as HTML/PDF. Screenshots alone do not prove interaction; the evidence record must name runtime, viewport, state, action, observed result, defect, fix, and retest.

This documentation slice makes no visual or runtime claim. Those gates remain unobserved until the native Desk and rendered documents exist.

## Sources of truth

- `docs/specs/automobile-repair-management.md` — approved v16 architecture, workflow, ERPNext authority, roles, prints, reports, and acceptance baseline.
- `docs/use-cases/real-workflows.md` — fleet campaign behavior and vehicle-by-vehicle operational narrative.
- `docs/design/car-workshop-navigation.md` — native Frappe workspace, theme, responsive, and no-custom-shell decisions.
- `docs/design/repair-job-form-layout.md` — native tabs, Connections dashboard, density, accessibility, and state language.
- Existing `Fleet Service Campaign` DocType/controller/tests — current one-customer campaign grouping, job synchronization, POST-only mapping, permission-scoped summaries, and trace contracts.
