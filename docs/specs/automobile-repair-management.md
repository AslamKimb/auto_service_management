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
6. Use a non-submittable Repair Job with a server-validated workflow; submitted ERPNext transactions remain immutable.
7. Treat ERPNext-generated quotation, invoice, tax, stock, payment, and credit figures as authoritative.

## Domain Model

### Configuration and Masters

- **Auto Service Settings**: company, default price list, project template, source warehouse, default terms, payment tolerance, and other site-specific defaults. No accounting or tax value is hardcoded.
- **Customer Vehicle**: registration number, customer, make, model, year, VIN/chassis, engine number, color, fuel type, transmission, current odometer, last service date, warranty, insurer, and notes. Registration and VIN are unique when supplied; search includes registration, VIN/chassis, engine, and customer.
- **Workshop Bay**: bay code, bay name, enabled state, and notes.
- **Fleet Service Campaign**: corporate customer, dates, description, status, and a child table linking independent Repair Jobs.

### Repair Job

The garage-facing document uses naming series `JC-.YYYY.-.#####` and links Customer, Customer Vehicle, and Project. It records repair type, complaint, visit reason, odometer, fuel level, advisor, mechanic, bay, planned/promised dates, contact details, workflow state, approval, invoice, gate-pass state, terms, and service lines.

`Repair Service Line` records Item, line type, description, quantity, UOM, cost and selling rates, discount, tax template, amounts, margin, warehouse, technician, linked Task, requested/issued quantities, and line state. Line types are Part, Labour, Consumable, Subcontracted Service, and Other.

### Workshop Transactions

- **Vehicle Walkaround Inspection** with Vehicle Damage Mark children, photos, signatures, odometer, fuel, condition notes, and customer presence.
- **Diagnosis Report** with findings, recommendations, estimated hours, required parts, and status.
- **Customer Authorization** with method, approved amount, evidence/signature, notes, and status.
- **Quality Check** with completion, fitment, fluid, warning-light, cleaning, road-test, notes, and Passed/Failed/Rework status.
- **Road Test Report** with route, odometers, braking, steering, performance, transmission, warning lights, notes, and status.
- **Gate Pass** with repair job, vehicle, invoice, recipient, identity reference, release/security users, issue/use timestamps, and status.
- **Repair Job Override** with exception type, reason, requestor, approver, decision timestamp, and linked evidence. Only Workshop Manager or Auto Service Admin can approve.
- **Repair Job Log** is server-created and read-only to users. It stores user, time, action, old/new values, remarks, and source document.
- **Service History** is an idempotent closure snapshot linked uniquely to its Repair Job.

## Workflow

Draft → Checked In → Walkaround Inspection → Diagnosis → Estimate Prepared → Waiting for Customer Approval → Approved → Parts Requested/In Repair/Waiting for Parts → Quality Check → Road Test → Ready for Invoice → Invoiced → Gate Pass Issued → Closed. Cancellation is allowed only through validated transitions.

Required gates:

- Checked In creates the Project once.
- Diagnosis requires check-in.
- In Repair requires approved Customer Authorization or an approved authorization override.
- Quality Check requires at least one Task or an approved exception.
- Ready for Invoice requires passed QC; a QC invoice override is separately audited.
- Road Test must pass when QC marks it required.
- Gate Pass requires a submitted invoice and either payment within tolerance, approved customer credit release, or a credit override.
- Credit release additionally requires configured payment terms and no credit-limit breach.
- Closing requires an issued/used Gate Pass and creates Service History once.

## ERPNext Integrations

- **Project**: created idempotently on check-in; receives customer, dates, Repair Job, Customer Vehicle, registration, workshop status, advisor, and mechanic.
- **Task**: generated from Project Template and linked to Project, Repair Job, Customer Vehicle, stage, technician, and bay.
- **Timesheet Detail**: linked to Repair Job and Customer Vehicle in addition to Project and Task. Timesheets supply actual hours and labour cost; invoice rows come only from approved service lines to prevent double billing.
- **Quotation / Sales Order / Sales Invoice**: created by typed POST-only Repair Job methods and linked bidirectionally. ERPNext pricing and tax controllers calculate authoritative totals.
- **Material Request / Stock Entry**: requests stock parts and records Material Issue consumption. Invoices do not update stock for quantities already issued.
- **Customer**: receives an explicit allow-credit-release control while existing payment terms and credit limits remain authoritative.

All ERPNext internal calls live behind focused integration adapters with contract tests.

## Roles

Service Advisor, Technician, Parts Interpreter, Workshop Manager, Cashier, Security Gate Officer, and Auto Service Admin. Permissions apply at DocType and row level. Technicians see assigned work; Security sees issuable/issued Gate Passes; manager overrides are never client-authorized.

## Workspace, Printing, and Reports

Create a Workshop Management workspace with shortcuts for vehicle search, new/open jobs, approval queues, repair/parts/QC/invoice queues, gate passes, history, and reports.

Provide Jinja print formats for Job Card, Walkaround Inspection, Customer Authorization, Estimate Summary, Gate Pass, and Repair Summary. The walkaround uses a static vehicle silhouette with numbered damage references, photos, terms, and signatures.

Provide reports for Open Repair Jobs, Daily Workshop Load, Jobs by Status, Jobs Waiting for Parts, Technician Productivity, Labour Hours by Technician, Repair Revenue by Period, Parts Used by Repair Job, Vehicle Service History, Delayed Jobs, Gate Pass Register, Corporate Credit Releases, and Discount and Price Change Audit.

## Acceptance Scenario

The release passes when a Service Advisor can find or create a Customer Vehicle, create a numbered Repair Job and Project, record intake/inspection/authorization/diagnosis, add priced service lines, create Tasks, capture Timesheets, audit important changes, pass QC and conditional road test, create a Sales Invoice, apply payment or controlled credit policy, issue and use a Gate Pass, close the job, and verify Service History and vehicle odometer/service dates.

## Non-Functional Requirements

- Fresh install, repeat migrate, uninstall, and reinstall succeed on an isolated test site.
- No core edits, guest mutation endpoints, raw SQL where Query Builder works, or controller commits.
- Fixtures are filtered to app-owned records.
- Tests contain no personal or production data.
- Production rollout follows backup/restore rehearsal, staging UAT, and explicit approval gates.
