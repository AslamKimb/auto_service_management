# Repair Job Sales Order / Proforma Invoice UI Direction

Status: delegated native Frappe direction, 2026-08-23

## Intent and audience

Service Advisors create a reviewable Sales Order from one Repair Job or one Repair Job Service. The document is customer-facing as a Proforma Invoice and remains traceable to the source components.

## Visual and interaction principles

- Use native Frappe Desk forms, grouped action menus, dialogs, indicator pills, list routes, and standard link behavior.
- Make selection explicit: every eligible Part, Consumable, and Labour component appears as a checkbox row with service, type, description, quantity, amount, and current state.
- Preserve ERPNext's document review step: mapping opens an unsaved draft; the user reviews and saves/submits it.
- Use plain “Proforma Invoice (Sales Order)” language in actions and “Proforma Invoice” in print output. Historical Quotation records remain read-only compatibility data.

## Color, typography, layout, and density

Use the active Frappe theme, typography, spacing scale, table styling, and indicator-pill colors. Keep tables compact but readable; do not add a parallel design system or custom global CSS.

## States and accessibility

The component status HTML field must render loading, empty, error, available, draft, submitted, cancelled, invoiced, and not-billable states. Controls must be keyboard reachable, labels must describe each checkbox, disabled rows must remain legible, and status must not rely on color alone.

## Responsive behavior

Use Frappe's responsive table wrapper and allow long descriptions/order IDs to wrap. Dialog rows must remain usable at narrow Desk widths without clipping the primary action.

## Print behavior

Sales Order print output uses the app-owned Proforma Invoice format and heading. The heading, document identity, customer, source Repair Job, line items, totals, and standard ERPNext terms remain legible in HTML and PDF.
