# Repair Job Native Form Layout

## Intent and audience

Repair Job is a workshop operator's working record: service advisors need the vehicle and intake context immediately, technicians need service and inspection evidence, and accounts users need billing without scrolling through unrelated fields. The redesign follows the native ERPNext Sales Invoice form pattern shown in the approved reference: a compact horizontal tab bar, native Frappe fields, and a final Connections dashboard.

## Layout and information architecture

The form uses five native Frappe `Tab Break` fields in this exact order:

1. **Details** — customer, vehicle, registration, intake, status, priority, promised date, project, fleet campaign, quotation, and Sales Order trace fields.
2. **Services** — service guidance, repair job services, and the calculated total.
3. **Workshop** — optional inspections, diagnosis, authorization, quality check, gate pass, odometer-out, and closure evidence.
4. **Billing** — currency, invoices, proforma Sales Orders, payment entries, payment status, billing/material summaries, and payment total.
5. **Connections** — the native Frappe dashboard (`show_dashboard: 1`) for linked workshop, billing/material, and context records.

Existing fieldnames, validation, required flags, read-only states, hidden fields, and workflows are unchanged. Only field order and native tabs change the visual hierarchy.

## Visual and interaction principles

- Use the standard Frappe Desk form shell and tab styling; no custom CSS, Vue shell, or duplicate dashboard is introduced.
- Keep the tab labels short and action-oriented so the full tab row remains scannable on desktop.
- Keep existing Section Breaks and Column Breaks inside their owning tab to preserve familiar two-column density and field grouping.
- Keep tables in their task tab: Repair Job Services under Services; invoices, proforma Sales Orders, and payments under Billing.
- Keep optional workshop evidence visibly optional; an empty state must remain a valid saved Repair Job.
- Connections is navigation and visibility, not a replacement for the existing document-creation actions in the form toolbar.

## Responsive and accessibility behavior

- Rely on Frappe's native tab overflow/stacking behavior at narrow widths; do not add a parallel responsive navigation pattern.
- Preserve keyboard tab order as the field order in the DocType JSON; `Tab Break` labels must be reachable and readable by assistive technology.
- Preserve native required indicators, read-only affordances, link pickers, table controls, and dashboard empty states.
- Verify desktop and narrow viewport rendering, long labels, empty linked records, and populated tables in the authenticated Desk runtime.

## Acceptance states

- New/draft job: Details and Services are usable with optional Workshop evidence blank.
- In-repair job: Workshop evidence and closure fields remain available without making optional records mandatory.
- Billing job: invoice/proforma/payment tables and component status widgets remain usable together.
- Connected job: Connections lists linked records with native counts and no duplicate entries.
- Empty connections: the native dashboard renders a clear empty state without a JavaScript or permission error.
