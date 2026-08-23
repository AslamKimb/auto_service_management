# Legacy Repair Job Sales Quotation and Print Output Specification

> Historical compatibility specification. New Repair Job document creation uses Sales Order documents printed as Proforma Invoice. Existing Quotation records, read-only summaries, and invoice compatibility mapping remain supported; no new Quotation action is exposed.

## Goal

Allow workshop users to create ERPNext Sales Quotations from a complete Repair Job or one Repair Job Service, preserve component traceability, create a Sales Invoice through ERPNext's native Quotation mapping, and produce consistent branded DMS print output.

## Functional contract

### Quotation creation

- A saved Repair Job exposes **Create Quotation** and can quote all billable Parts, Consumables, and Labour from its included Repair Job Services.
- A saved Repair Job Service exposes **Create Quotation** and quotes only that service's billable components.
- Quotation rows use the same invoice quantity/hours, invoice rate, description, item code, UOM, discount eligibility, and labour-item validation as Sales Invoice mapping.
- A quotation does not reserve, consume, or otherwise change a component's stock, invoice, or reservation state.
- Repeated quotation creation is allowed. Each quotation is historical and independent; the singular `Repair Job.quotation` field is updated to the latest quotation for existing compatibility flows.
- Each generated quotation has `valid_till` set to one calendar month after `transaction_date`.

### Traceability and counts

- `Quotation.repair_job` identifies the originating Repair Job.
- `Quotation.repair_job_service` is set for a service-scoped quotation.
- Every Quotation Item carries `repair_job`, `customer_vehicle`, `repair_job_service`, `repair_component_doctype`, `repair_component_row`, and `repair_service_line`.
- The source component keeps the latest quotation and quotation-row identity in its existing quotation fields.
- Repair Job shows a read-only quotation count and opens the full quotation list. Repair Job Service opens quotations filtered to that service.

### Quotation to invoice

Use ERPNext's native Sales Invoice **Get Items From → Quotation** flow. No ERPNext core files are changed. The app overrides the native whitelisted mapper only to copy app-owned trace fields after ERPNext builds the invoice; the UI action and ERPNext mapping remain native, after which existing invoice synchronization remains authoritative.

## Print output

- The six existing DMS print formats continue to include the shared `common.html` header.
- Resolve the configured Company logo first. Relative File URLs are normalized to absolute URLs for HTML/PDF rendering.
- Resolve logos in this order: `Company.company_logo`, Website Settings `app_logo`, then Website Settings `banner_image`. If none exists, render no logo; never use a workspace, car-wash, upholstery, or workshop icon as a print fallback.
- ERPNext core print formats are out of scope.
- The Repair Job Estimate Summary includes this exact note below the estimate table:

> This quotation is valid for one month only unless the vehicle is not mobile. Payment can be done by CASH, through a bank, DFCU Bank: 01670016727489, OR MTN Mobile Money: 0392554255. We value and respect your time and will provide the best service to you.

The estimate table displays each Repair Job Service as a parent row and indented Part, Consumable, and Labour rows with item code, description, billable quantity/hours, rate, amount, source component DocType, and source row identity.

## Interfaces and permissions

- `RepairJob.create_quotation`: POST-only document mutation; requires Repair Job write permission and Quotation create permission.
- `RepairJobService.create_quotation`: POST-only document mutation; requires service write permission and Quotation create permission.
- `repair_job.get_quotation_summary`: GET-only read operation; requires Repair Job read permission.
- All component mapping must validate that the selected service/component belongs to the requested Repair Job.

## Test and acceptance matrix

| Area | Required coverage |
| --- | --- |
| Unit | Full-job and service-scoped item mapping, quantities/rates/descriptions, labour billing, trace fields, validity date, duplicate quotes, permissions, POST/GET method declarations |
| Integration | Full-job and service quotations contain only eligible components; native Quotation-to-Sales-Invoice mapping carries traces and invoice synchronization continues |
| Regression | Quotation creation does not alter stock, invoice status, component reservation, or material/invoice state |
| Print | All six formats render with a Company logo and app-logo fallback in HTML/PDF; Estimate Summary has exact note and component hierarchy |
| End-to-end | `docs/acceptance_scenario.sh` creates quotations, verifies count and line completeness, creates a native invoice, checks validity date, and checks Estimate Summary output |

## Acceptance criteria

1. A full Repair Job quotation contains every eligible billable Part, Consumable, and Labour line exactly once for that quotation.
2. A service quotation contains only the selected service's eligible billable lines.
3. A second quotation can be created without overwriting the first or changing reservation/stock state; the count increases to two.
4. `valid_till` is exactly one calendar month after the quotation date.
5. ERPNext's native quotation-to-invoice action produces an invoice with Repair Job and component trace fields, and existing invoice synchronization sees those rows.
6. All six DMS formats show a usable logo source, including the app icon fallback, and the Estimate Summary note and trace hierarchy are present in HTML and PDF output.

## Assumptions and non-goals

- ERPNext remains authoritative for pricing, taxes, customer credit, and ledger postings.
- The non-mobile vehicle exception is printed text only until a mobility field is introduced.
- No new component reservation model or custom invoice-from-quotation endpoint is introduced.
