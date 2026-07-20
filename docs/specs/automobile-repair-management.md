# Automobile Repair Management Specification

## Status

Approved implementation baseline for `auto_service_management`, targeting Frappe and ERPNext `version-16`.

## Objective and Boundaries

Build an installable HRMS-style vertical app that makes ERPNext operate as an automobile workshop system without modifying Frappe or ERPNext core. Custom DocTypes provide the workshop interface; ERPNext remains the authority for operational projects, stock, selling, payments, and accounting.

The repository research file `Automotive DMS.md` explains legacy dealership workflows but does not add requirements beyond this specification.

## Approved Architecture Corrections

1. Use `required_apps = ["erpnext"]`.
2. Use a custom `Customer Vehicle` master because ERPNext already owns `Vehicle` for internal fleet assets.
3. Enforce one Customer Vehicle and one ERPNext Project per Repair Job.
4. Model fleet work through `Fleet Service Campaign`, which groups separate Repair Jobs.
5. Use a dedicated, submittable `Repair Job Override` for controlled exceptions.
6. Use a non-submittable `Repair Job` with an automatic workflow; the workflow state changes are derived from server-side validation and `job_status` is the sole business status.
7. Treat ERPNext-generated quotation, invoice, tax, stock, payment, and credit figures as authoritative.
8. Do not use `Repair Job Service` status as an eligibility gate; downstream actions must derive from submitted content and parent job state.

## Domain Model

### Configuration and Masters

- **Auto Service Settings**: company, default price list, project template, default Parts/Consumables warehouse, default terms, payment tolerance, and other site-specific defaults. No accounting or tax value is hardcoded.
- **Customer Vehicle**: registration number, customer, make, model, year, VIN/chassis, engine number, color, fuel type, transmission, current odometer, last service date, warranty, insurer, and notes. Registration and VIN are unique when supplied; search includes registration, VIN/chassis, engine, and customer.
- **Workshop Bay**: bay code, bay name, enabled state, and notes.
- **Fleet Service Campaign**: corporate customer, dates, description, status, and a child table linking independent Repair Jobs.

### Repair Job

The garage-facing document uses naming series `JC-.YYYY.-.#####` and links Customer, Customer Vehicle, and Project. It records repair type, complaint, visit reason, odometer, fuel level, advisor, mechanic, bay, planned/promised dates, contact details, workflow state, approval, invoice, gate-pass state, terms, and service lines.

Each `Repair Job Service` owns Parts, Labour, and Consumables child tables. Service eligibility is not controlled by a user-facing status field; billing, stock, and downstream automation derive from the submitted service content, workshop bay, and parent Repair Job state. Stock rows record optional Item, quantity, UOM, warehouse, selling and cost rates, discounts, amounts, and requested/issued quantities. Labour rows use hours and costing rate for cost, and billing hours, optional Billable Labour Item, and billing rate for selling. The service stores a live pre-tax total, cost total, gross margin, and margin percentage. Historical subcontract rows remain auditable only through hidden, read-only legacy tables.

### Workshop Transactions

- **Vehicle Walkaround Inspection** with Vehicle Damage Mark children, photos, signatures, odometer, fuel, condition notes, and customer presence. Optional unless intake damage capture is needed.
- **Diagnosis Report** with findings, recommendations, estimated hours, required parts, and status. Optional for straight-through repair cycles and required for diagnosis-led closures.
- **Customer Authorization** with method, approved amount, evidence/signature, notes, and approval state. Required before repair work begins unless the job is diagnosis-only.
- **Quality Check** with completion, fitment, fluid, warning-light, cleaning, road-test, notes, and Passed/Failed/Rework status. Required for repair jobs and optional only for diagnosis-only closures.
- **Road Test** evidence is captured as a child table on Quality Check, not as a separate status-bearing DocType.
- **Gate Pass** with repair job, vehicle, invoice, recipient, identity reference, release/security users, issue/use timestamps, and status.
- **Repair Job Override** with exception type, reason, requestor, approver, decision timestamp, and linked evidence. Only Workshop Manager or Auto Service Admin can approve.
- **Repair Job Log** is server-created and read-only to users. It stores user, time, action, old/new values, remarks, and source document.
- **Service History** is an idempotent closure snapshot linked uniquely to its Repair Job.

## Workflow

Draft → Assessment → Awaiting Approval → In Repair → Quality Check → Billing → Ready for Release → Closed. Cancellation is allowed only through validated transitions.

The workflow is automatic:

- `Draft` means the Repair Job has not been checked in.
- `Assessment` means the job is checked in and intake or diagnosis is still incomplete.
- `Awaiting Approval` means the service scope is complete but a current full-job authorization is missing.
- `In Repair` means the current scope is authorized and QC has not passed.
- `Quality Check` means QC has opened and is pending a result.
- `Billing` means QC passed, or the job is diagnosis-only, but invoice coverage or payment clearance is still incomplete.
- `Ready for Release` means every billable component is fully invoiced and financially cleared.
- `Closed` means the Gate Pass was used and the Repair Job is submitted.
- `Cancelled` means a validated pre-closure cancellation was recorded with a reason.

Diagnosis-only jobs can move from `Assessment` directly to `Billing` after diagnosis is submitted. A job can move back from `Quality Check` to `In Repair` when QC fails or rework is required. A job can move from `Billing` back to `Awaiting Approval` when the scope changes and current authorization is no longer valid.

Required gates:

- Checked In creates the Project once.
- Diagnosis requires check-in.
- In Repair requires approved Customer Authorization or an approved authorization override.
- Quality Check requires at least one Task or an approved exception.
- Billing requires passed QC, or diagnosis-only completion, and unresolved invoice or payment coverage.
- Ready for Release requires every billable component to be covered by submitted invoices and either payment within tolerance, approved customer credit release, or a credit override.
- Road test evidence is required only when QC marks it required.
- Gate Pass requires the job to be Ready for Release and the invoice/payment coverage rules to remain satisfied.
- Credit release additionally requires configured payment terms and no credit-limit breach.
- Closing requires an issued/used Gate Pass and creates Service History once.

## Submission and Document Policy

- `Repair Job` is non-submittable and closes through the app-owned workflow.
- `Repair Job Service` is the service-level document used for billing, stock, and labour lines; it does not depend on a user-facing status field for eligibility.
- `Customer Authorization`, `Diagnosis Report`, `Quality Check`, and `Gate Pass` are submittable workshop control documents.
- `Walkaround Inspection`, `Road Test` evidence, `Repair Job Override`, `Quotation`, `Sales Order`, `Material Request`, `Stock Entry`, and `Timesheet` are optional or conditional records.
- `Sales Invoice` may be created more than once per Repair Job; payment status is derived from submitted invoices and their Payment Entries, not from invoice creation alone.
- `Service History` is generated automatically at closure and is not manually submitted.

## ERPNext Integrations

- **Project**: created idempotently on check-in; receives customer, dates, Repair Job, Customer Vehicle, registration, workshop status, advisor, and mechanic.
- **Task**: generated from Project Template and linked to Project, Repair Job, Customer Vehicle, stage, technician, and bay.
- **Timesheet Detail**: linked to Repair Job and Customer Vehicle in addition to Project and Task. Timesheets supply actual hours and labour cost; invoice rows come only from submitted Repair Job Services to prevent double billing.
- **Quotation / Sales Order**: created by typed POST-only Repair Job methods and linked bidirectionally.
- **Sales Invoice**: mapped from a Repair Job or one submitted Repair Job Service, either from the source form or through the target form's native Get Items From menu. Every billable Part, Consumable, and Labour row in eligible services maps; Item links are optional for invoice rows, with description-based stock rows using `Nos` and Labour using `Hour`. Drafts reserve component rows; several service-level invoices may cover one job. The Repair Job reaches Ready for Release only after every eligible component is covered by submitted invoices and payment coverage is satisfied. ERPNext pricing and tax controllers remain authoritative, and mapped invoices never update stock.
- **Material Request / Stock Entry**: Material Issue requests can be mapped from a Repair Job or one submitted Repair Job Service, either from the source form or through Get Items From. Parts and Consumables map from submitted parent services, require Items, and use full component quantities and configured warehouses. Drafts reserve component rows and cancellation, deletion, or item removal releases them. Stock Entry records Material Issue consumption.
- **Customer**: receives an explicit allow-credit-release control while existing payment terms and credit limits remain authoritative.

All ERPNext internal calls live behind focused integration adapters with contract tests.

## Roles

Service Advisor, Technician, Parts Interpreter, Workshop Manager, Cashier, Security Gate Officer, and Auto Service Admin. Permissions apply at DocType and row level. Technicians see assigned work; Security sees issuable/issued Gate Passes; manager overrides are never client-authorized.

## Workspace, Printing, and Reports

Create a Workshop Management workspace with shortcuts for vehicle search, new/open jobs, approval queues, repair/parts/QC/invoice queues, gate passes, history, and reports.

Provide Jinja print formats for Job Card, Walkaround Inspection, Customer Authorization, Estimate Summary, Gate Pass, and Repair Summary. The walkaround uses a static vehicle silhouette with numbered damage references, photos, terms, and signatures.

Provide reports for Open Repair Jobs, Daily Workshop Load, Jobs by Status, Jobs Waiting for Parts, Technician Productivity, Labour Hours by Technician, Repair Revenue by Period, Parts Used by Repair Job, Vehicle Service History, Delayed Jobs, Gate Pass Register, Corporate Credit Releases, and Discount and Price Change Audit.

## Acceptance Scenario

The release passes when a Service Advisor can find or create a Customer Vehicle, create a numbered Repair Job and Project, record intake/inspection/authorization/diagnosis, add priced service lines, create Tasks, capture Timesheets, audit important changes, pass QC and conditional road-test evidence, create one or more Sales Invoices, apply payment or controlled credit policy, issue and use a Gate Pass, close the job, and verify Service History and vehicle odometer/service dates.

## Non-Functional Requirements

- Fresh install, repeat migrate, uninstall, and reinstall succeed on an isolated test site.
- No core edits, guest mutation endpoints, raw SQL where Query Builder works, or controller commits.
- Fixtures are filtered to app-owned records.
- Tests contain no personal or production data.
- Production rollout follows backup/restore rehearsal, staging UAT, and explicit approval gates.
