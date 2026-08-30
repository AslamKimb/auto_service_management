# Auto Service Management - Product Contract

Status: READY FOR IMPLEMENTATION PLANNING
Last updated: 2026-08-30
UI Surface: PRESENT

This contract documents the approved product scope, including the three additive workshop capabilities requested for delivery. It is a canonical product reference, not authorization to change application code, ERPNext core, production data, or deployment state.

## Product Purpose

Auto Service Management turns ERPNext into a controlled automobile workshop operating system. It gives workshop staff one traceable story for a vehicle visit—from customer and vehicle intake through diagnosis, work, parts, labour, billing, payment/credit clearance, gate release, and service history—while ERPNext remains authoritative for customers, items, prices, taxes, stock, sales documents, payments, credit limits, and accounting.

The product optimizes for safe operational progress, auditability, and low-friction native Frappe Desk work. Optional inspection, diagnosis, authorization, quality, and road-test records add evidence but must not silently block or regress the core Repair Job flow.

## Target Users

- Independent and multi-bay automobile workshops using ERPNext/ Frappe Desk.
- Workshop staff working at reception, service bays, parts stores, accounts, and the security gate.
- Corporate-fleet customers whose approved LPO covers multiple independent vehicle visits.
- Customers who need read-only visibility of their submitted repair and payment status through `My Repairs`.

Primary use is authenticated Desk work on desktop or tablet-sized screens. The customer portal is a constrained read-only website surface.

## Roles

### Human roles

| Role | Core responsibility |
|---|---|
| Service Advisor | Find/create customers and vehicles, check in jobs, capture concerns, coordinate estimates and approvals. |
| Workshop Technician | Execute assigned work, update tasks/timesheets, and contribute inspection/diagnosis evidence. |
| Parts Interpreter | Resolve fitment, prepare material requests, and manage parts/consumables issue flow. |
| Workshop Manager | Review queues, approve controlled overrides, manage campaigns, and control rework/quality decisions. |
| Cashier | Create and reconcile Sales Invoices, payments, and release readiness. |
| Security Gate Officer | Issue/use Gate Passes only after release gates are satisfied. |
| Auto Service Admin | Configure settings, catalog, bays, permissions, templates, and operational controls. |
| Customer portal user | View only that user's linked submitted repair, service, invoice, and payment information. |

### Application and integration roles

- Frappe/ERPNext owns identity, sessions, permissions, documents, workflow persistence, accounting, stock, tax, pricing, and native document mapping.
- Auto Service Management owns workshop-specific DocTypes, business transitions, fitment decisions, audit logs, portal filtering, and integration adapters.
- Background workers and scheduler perform only explicitly queued or scheduled app work; they do not replace synchronous permission or financial gates.

## Modules

1. **Workshop setup** — settings, roles, bays, vehicle makes/models/engines, item fitment, service templates, defaults, and audit logs.
2. **Customer and vehicle intake** — ERPNext Customer plus app-owned Customer Vehicle search and maintenance.
3. **Repair operations** — Repair Job, services, tasks, timesheets, inspection, diagnosis, authorization, quality, and road-test evidence.
4. **Parts, pricing, and billing** — fitment-aware component selection, ERPNext prices/taxes, Sales Order/Proforma, Sales Invoice, payments, and material requests/stock issue.
5. **Fleet and commercial control** — Customer LPO, Fleet Service Campaign, per-vehicle jobs, amendments, ceiling reconciliation, and consolidated billing.
6. **Quality and release** — Quality Check, Gate Pass, release policy, closure, and Service History.
7. **Navigation, reporting, printing, and portal** — native workspaces, operational reports, Jinja print formats, and read-only `My Repairs`.

## Features and Actions

### Vehicle and customer intake

The Service Advisor searches by registration, VIN/chassis, engine identifier, or customer. If no suitable vehicle exists, the advisor creates a Customer Vehicle with optional controlled make/model/engine references. Registration and VIN are unique when supplied; model must belong to its make. A Customer Vehicle may be created without a Customer, then associated with multiple customers over time through explicit, dated, auditable visit associations; invalid or unauthorized matches fail without mutating the wrong customer record.

### Repair Job lifecycle

The Service Advisor creates one Repair Job for one Customer Vehicle and one ERPNext Project. Check-in creates the Project idempotently, captures intake details, and makes the job visible to operational queues. For a Company Customer, the advisor records the Contact or responsible person for that specific job; the Contact is required at Check In, validated against the company, and snapshotted for historical job context. Individual jobs do not require a Contact. The app owns the non-submittable Repair Job workflow: Draft → Assessment → Awaiting Approval → In Repair → Quality Check → Billing → Ready for Release → Closed, with validated cancellation before terminal completion and explicit Quality Check → In Repair rework.

### Optional evidence

Staff may attach Walkaround Inspection, Diagnosis Report, Customer Authorization, Quality Check, and road-test evidence where useful. These records validate links and permissions, but absence, failure, cancellation, or late creation never automatically blocks or regresses a later compatible job state. A passed optional record may advance an earlier compatible state.

### Service, pricing, fitment, and work execution

The technician/advisor adds Parts, Labour, and Consumables through Repair Job Services. ERPNext price lists and taxes remain authoritative. Item fitment produces an auditable match snapshot; exact verified matches pass silently, while broad, universal, provisional, missing-data, or mismatch outcomes warn and require a controlled override reason. Project Tasks and Timesheets trace execution and actual labour without double-billing submitted service rows.

### Orders, invoices, stock, and release

Typed POST-only actions open reviewable ERPNext drafts from explicitly selected components. A permitted user can use the native Sales Order `Get Items From` flow to preview and fetch eligible billable items from one Repair Job or one exact Repair Job Service while preserving Quotation behavior. The same feature may update a submitted Sales Order only when native ERPNext update eligibility, source/target permissions, customer match, ownership, fitment, stock, release, LPO, and duplicate-billing gates pass; it must preserve the same document identity and never bypass native restrictions. Submitted Sales Orders/Sales Invoices own component traces and reject duplicate submitted ownership. Invoices may be split across a job; invoice/payment hooks synchronize summaries without changing Repair Job status. Material Requests use a service-bay warehouse when configured and create automatic Stock Entry only for Material Issue. Ready for Release requires complete billable invoice coverage plus payment within tolerance, approved credit release, or a controlled credit override. Gate Pass issue/use and Service History creation complete the release path.

### Fleet/LPO flow

A Service Advisor or manager records a Customer LPO, validates CSV/manual vehicle rows, resolves vehicles, and submits the LPO before creating one Fleet Service Campaign and one Repair Job per resolved vehicle. Financials show the selected tax basis, original/effective authorization, committed/invoiced/paid/remaining values, amendments, and ceiling failures. Consolidated order/invoice actions remain permission- and ceiling-aware. No LPO action merges vehicles into one Repair Job or silently changes accounting authority.

### Customer portal

An explicitly linked ERPNext Customer website user can open `My Repairs` and see only permitted submitted repair jobs, service lines, submitted invoices, and submitted payment allocations. Draft finance documents, internal notes, technician identities, costing, margins, and payment-account details remain hidden. The portal does not create users or mutate records.

## User Stories

- As a Service Advisor, I can find a returning vehicle quickly and check in a new repair visit without duplicating the vehicle master or Project.
- As a Service Advisor, I can leave a new Customer Vehicle unassigned, explicitly associate it with a visit customer, and review the dated customer history when the vehicle returns under another customer.
- As a Service Advisor, I can record the Company Contact or responsible person for each company Repair Job while keeping company billing and customer identity intact.
- As a Technician, I can see assigned work, record actual hours, and progress the job without needing optional evidence to exist first.
- As a Parts Interpreter, I can see fitment warnings and create traceable requests for the correct component quantities and warehouse.
- As a Workshop Manager, I can approve exceptional fitment/credit decisions with reason, approver, timestamp, and evidence.
- As a Cashier, I can invoice selected components, reconcile payment or permitted credit, and understand exactly why release is or is not allowed.
- As a permitted Sales Order user, I can review and fetch eligible Repair Job or Repair Job Service items into a draft or native-eligible submitted Sales Order without duplicating owned components.
- As a Security Gate Officer, I can issue and use a Gate Pass only for a financially cleared Ready for Release job.
- As a Customer, I can follow submitted repair and payment status without seeing internal workshop or accounting details.
- As an administrator, I can configure site defaults and inspect audit/report data without hardcoding company-specific financial values.

## Permissions

DocType and row-level permissions are authoritative; workspace visibility is only navigation assistance.

| Role | Allowed actions | Data scope |
|---|---|---|
| Service Advisor | Read/write intake and Repair Jobs; associate vehicles to visit customers; record company Contacts; create optional evidence; prepare reviewable commercial drafts; read customer/vehicle context. | Assigned/authorized workshop records and permitted linked ERPNext records. |
| Workshop Technician | Read assigned jobs/tasks; update permitted execution fields and Timesheets; add evidence. | Assigned work and linked operational records; no finance/cost/credit control. |
| Parts Interpreter | Read permitted jobs/services; prepare Material Requests/Stock flows; maintain fitment/catalog data only when granted. | Relevant job components, items, warehouses, and catalog scope. |
| Workshop Manager | Manager-level read/write; approve overrides; control campaign/LPO and quality/rework decisions. | Workshop-wide records within company/site permission scope. |
| Cashier | Create/read/update permitted Sales Invoices and payment-related records; reconcile release readiness. | Financial records linked to permitted workshop/customer scope. |
| Permitted Sales Order user | Preview/fetch eligible Repair Job or Repair Job Service items into permitted draft or native-eligible submitted Sales Orders. | Permitted source jobs/services/components and target Sales Orders; no hidden Contact details. |
| Security Gate Officer | Read eligible Gate Passes; issue/use permitted passes. | Issuable/issued release records only. |
| Auto Service Admin | Configure app masters, roles, fixtures, settings, and controls; audit all app-owned records. | Site-wide app scope. |
| Customer portal user | Read linked submitted repairs, submitted services, invoices, and payment allocations. | Customer records linked to the website user; no mutation. |

All user-triggered mutations are permission-checked server actions. No guest mutation endpoint exists.

## Workflows

### Single-vehicle workshop visit

Find/create Customer Vehicle → create Repair Job → check in and create Project → optionally capture inspection/diagnosis/authorization → add services and resolve fitment → generate tasks/timesheets and parts requests → perform work → optionally quality check/road test → invoice one or more times → clear payment or approved credit → Ready for Release → issue/use Gate Pass → Closed and idempotent Service History.

### Returning vehicle and company contact

Find or create the Customer Vehicle without requiring the Customer → select the canonical visit Customer → explicitly confirm a different customer when needed → validate any Company Contact against that Customer → Check In atomically → record the dated vehicle association, per-job customer/contact snapshot, and one Project path → continue the normal Repair Job workflow.

### Sales Order item retrieval

Open native Sales Order `Get Items From` → preview one Repair Job or one exact Repair Job Service → select eligible billable rows → review counts and traces → fetch into a draft or, only when native update eligibility passes, the same submitted Sales Order → recalculate through ERPNext → preserve ownership and downstream invoice/portal controls.

### Branches

- Diagnosis-only: Assessment → Billing, with or without a Diagnosis Report.
- Rework: Quality Check → In Repair through an explicit action.
- Cancellation: validated pre-closure cancellation with reason; no post-invoice silent cancellation path.
- Fleet: submitted Customer LPO → one campaign → one independent Repair Job per resolved vehicle → per-job/consolidated commercial documents within the ceiling.

## Screens and Navigation

The native Frappe `Car Workshop` app launcher exposes permission-filtered hubs: Overview, Intake, Workshop, Parts & Billing, Quality & Release, Fleet & History, Reports, and Setup. `Workshop Management` remains the overview route.

Primary surfaces are Customer/Customer Vehicle search and dated association history, Repair Job form (Details, Services, Workshop, Billing, Connections) with conditional Company Contact, task/service/parts queues, LPO form (Details, Vehicles, Financials, Connections), native Sales Order mapping dialogs, reports, print formats, and the read-only `/my-repairs` customer page.

## Business Rules

- One Repair Job = one Customer Vehicle + one ERPNext Project.
- Customer Vehicle.customer may be blank at creation; each confirmed visit has exactly one canonical Repair Job.customer and a dated association interval, with no overlapping open intervals.
- A different visit customer requires explicit confirmation; prior customer/job snapshots remain immutable.
- A Company Repair Job may save as Draft without Contact, but Check In requires a readable Contact linked to the canonical Company Customer and snapshots the job-specific identity once; Individual jobs remain valid without Contact.
- Sales Order retrieval reads one Repair Job or one exact Repair Job Service at a time, requires source/target customer match and eligible source state, preserves existing rows and immutable traces, and never bypasses native submitted-document restrictions.
- Contact name, phone, and email are internal job context and do not broaden Sales Order, invoice, print, or portal visibility without an existing authorized boundary.
- Fleet campaigns group separate jobs; they do not merge vehicle work.
- Repair Job is non-submittable; `job_status` is the sole business status.
- Optional evidence cannot block or regress later compatible workflow state.
- ERPNext is authoritative for prices, taxes, stock, invoices, payments, credit limits, and accounting.
- Submitted component ownership prevents duplicate submitted Sales Order/Sales Invoice billing.
- Labour invoices use the required Hour service Item; Timesheets do not create a second billable labour source.
- Fitment warnings and financial exceptions require auditable overrides, never client-only authorization.
- Release requires billable coverage and payment/credit policy; closure requires a used Gate Pass.
- App-owned fixtures are filtered; no credentials, production records, signatures, or vehicle photos enter tests.

## Important Data Requirements

Core entities are Auto Service Settings, Customer Vehicle, Customer Vehicle Customer Association history, Vehicle Make/Model/Engine, Item Vehicle Fitment, Workshop Bay, Fleet Service Campaign, Customer LPO, Repair Job, Repair Job Service and component rows, per-visit customer/contact snapshots, Project/Task/Timesheet traces, inspection/diagnosis/authorization/quality records, Repair Job Override, Repair Job Log, Gate Pass, Service History, ERPNext commercial/stock/payment documents, and portal linkage.

Important invariants include unique supplied vehicle identifiers, linked-record ownership, server-calculated amounts/margins, immutable audit evidence, idempotent Project/Service History creation, complete component traces, permission-scoped queries, and submitted-only portal finance visibility.

## Integrations

- Frappe Desk, website routing, sessions, permissions, fixtures, hooks, DocType lifecycle, and scheduler/workers.
- ERPNext Customer, Vehicle boundary, Project, Task, Timesheet, Item, Price List, Quotation compatibility, Sales Order, Sales Invoice, Payment Entry, Material Request, Stock Entry, warehouses, taxes, terms, credit limits, and accounting.
- HRMS and Uganda Compliance are installed suite companions; EFRIS remains dormant until separately configured.
- Docker Compose, Nginx, MariaDB, Redis cache/queue/socket, and Socket.IO provide the local runtime.

## Acceptance Criteria

- **AC-001 Intake identity:** Given a permitted Service Advisor and a known registration, when the advisor searches, then the matching Customer Vehicle and customer context are shown without creating a duplicate.
- **AC-002 New visit:** Given a valid Customer Vehicle, when the advisor checks in a Repair Job, then exactly one linked ERPNext Project exists and the job enters the operational workflow.
- **AC-003 Optional evidence:** Given a job with no inspection, diagnosis, authorization, QC, or road-test record, when the advisor progresses it through a valid path, then absence of those optional records does not block or regress the job.
- **AC-004 Workflow safety:** Given an invalid or unauthorized transition, when a user attempts it, then the server rejects it and records no false state change.
- **AC-005 Fitment control:** Given an exact, broad, provisional, missing-data, or mismatched part fitment, when a component is evaluated, then the app shows the appropriate result and requires an auditable override where required.
- **AC-006 Commercial trace:** Given selected billable components, when a permitted user creates an ERPNext Sales Order or Sales Invoice draft, then the draft is reviewable and each selected component is traceable to the Repair Job/service row.
- **AC-007 Duplicate billing:** Given a component already owned by a submitted order/invoice, when another submitted document attempts to claim it, then submission fails with an actionable conflict.
- **AC-008 Stock safety:** Given a Material Request purpose, when a request is created, then the selected quantities and bay/default warehouse are respected and automatic Stock Entry occurs only for Material Issue.
- **AC-009 Release gate:** Given incomplete invoice coverage or payment/credit failure, when Gate Pass issue is attempted, then the server rejects it with the exact unmet condition; given a cleared job, issue/use succeeds.
- **AC-010 Closure:** Given a used Gate Pass, when the job closes, then one Service History snapshot is created and vehicle service/odometer fields update according to the approved rules.
- **AC-011 Fleet/LPO:** Given a submitted LPO with resolved vehicles, when campaign creation runs, then one campaign and one Repair Job per vehicle are created idempotently and ceiling controls remain visible.
- **AC-012 Portal privacy:** Given a linked customer website user, when `/my-repairs` is opened, then only that customer's submitted repair and finance data appears; internal notes, drafts, cost, margin, and account details do not.
- **AC-013 Permissions:** Given a user without a role or row scope, when a protected read or mutation is attempted, then access is denied without leaking hidden linked totals or records.
- **AC-014 Installability:** Given an isolated test site, fresh install, repeated migrate, uninstall, and reinstall complete without core edits or unfiltered app-owned fixtures.
- **AC-015 Vehicle customer history:** Given a permitted advisor and a Customer Vehicle with blank or different current Customer, when an explicit visit association is confirmed, then the same vehicle identity is reused, one dated association interval is recorded, the visit keeps its canonical customer, and prior intervals remain unchanged.
- **AC-016 Company job contact:** Given a Company Customer Repair Job, when it is saved as Draft and then checked in with a validated Contact, then the Draft remains saveable without Contact, Check In captures one immutable job snapshot, and separate jobs may retain different Contacts without changing the company master; Individual jobs remain valid without Contact.
- **AC-017 Repair Job item retrieval:** Given a permitted user and a new or Draft Sales Order, when native `Get Items From` is opened, then Repair Job and exact Repair Job Service sources appear alongside Quotation, selected eligible rows are reviewable and traceable, and existing rows and Quotation behavior remain intact.
- **AC-018 Submitted Sales Order item retrieval:** Given a permitted user, an Assessment-or-later Repair Job source, and a submitted Sales Order that passes native update eligibility and all app gates, when selected items are fetched, then the same submitted Sales Order is updated atomically; otherwise the action is rejected or unavailable without mutation.

## MVP Priorities

1. Safe intake, Customer Vehicle identity, Repair Job lifecycle, permissions, and auditability.
2. Service lines, ERPNext pricing, fitment warnings/overrides, Projects/Tasks/Timesheets, parts requests, invoicing, payments, release, and history.
3. Native workspaces, print formats, reports, optional evidence, and read-only customer portal.
4. Fleet Service Campaign and Customer LPO controlled batching/consolidation.

## Constraints

- Target Frappe/ERPNext `version-16`; keep behavior inside this app.
- Never edit Frappe/ERPNext core, hardcode accounts/taxes/warehouses/prices/credit limits, or commit in controllers.
- Use typed POST-only mutation methods with server-side permissions; use GET for reads/previews.
- Prefer native Frappe/ERPNext records, Desk, Query Builder, workflows, reports, and print mechanisms.
- Production database/image/deployment changes require the documented approval gates.
- Visual implementation requires approved `DESIGN.md` direction and direct runtime inspection.
- The three requested capabilities are additive extensions to the existing workshop baseline: they preserve prior Repair Job-to-draft and invoice mappings while adding vehicle association history, company job contacts, and native Sales Order `Get Items From` retrieval for draft and native-eligible submitted targets.

## Assumptions

- The current approved specification and implemented repository behavior are the baseline being documented.
- Native Frappe/ERPNext styling remains the approved visual language; no new brand palette is assumed.
- The read-only `My Repairs` route is a supported secondary surface, while a custom LPO portal is not in scope.
- Site-specific company, price list, tax, warehouse, terms, payment tolerance, and credit values are configured through ERPNext/app settings rather than encoded in the app.

## Explicitly Out of Scope

- Editing Frappe/ERPNext core or replacing ERPNext accounting, stock, tax, payment, or credit authority.
- A custom Vue shell, separate public form, or customer mutation portal.
- OCR, automatic LPO interpretation, multi-currency conversion, speculative microservices, offline-first operation, and unapproved third-party integrations.
- Creating Item Variants for vehicle fitment, merging fleet vehicles into one Repair Job, or treating optional evidence as mandatory workflow gates.
- Production rollout, image build/redeploy, or Dokploy changes without explicit approval.

## Open Decisions

None - no material unresolved decisions. The remaining work is implementation planning or execution against this documented existing baseline.
