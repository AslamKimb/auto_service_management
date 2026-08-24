# Repair Job Service Templates and History Navigation Design Contract

## Intent and audience

This is a native Frappe Desk workflow for Service Advisors, Workshop Managers, Parts Interpreters, and Workshop Technicians. The goal is to reuse a proven repair-service definition quickly and to move from a customer or vehicle directly into the workshop history without losing ERPNext's normal document context.

## Reference direction and principles

- Follow the existing Car Workshop workspace and Frappe CRM/ERPNext Desk patterns: standard forms, Link controls, dialogs, list views, dashboards, breadcrumbs, and native related-document connections.
- Keep the interaction compact and operational: choose a compatible template, review the populated service, then save.
- Keep Customer and Customer Vehicle as the source-of-truth masters. Do not add a parallel customer, vehicle, or composite-history page.
- Treat templates as reusable snapshots. Existing services never change when a template changes.

## Color, typography, density, and surfaces

- Use Frappe Desk's existing typography, spacing, colors, badges, and surface hierarchy. No new brand palette, font, shadow system, or decorative illustration is introduced.
- Use standard sections and two-column form density for template definitions; keep child tables in the normal Frappe grid style.
- Use native status colors only: enabled/available uses the existing success treatment; disabled/incompatible states use the existing neutral or warning treatment.

## Layout and navigation

- Add `Find Vehicle` and `Customers` as native workspace/sidebar links.
- Vehicle search opens the native Customer Vehicle list with registration, customer, make/model, VIN, engine, odometer, and last-service context.
- Customer opens the standard ERPNext Customer form with an added Workshop History dashboard group.
- Customer Vehicle opens the standard vehicle form with Workshop History connections for Repair Jobs, Repair Job Services, and Service History.
- Preserve Frappe breadcrumbs and document routes; do not introduce a custom shell or nested page.

## Interaction and component states

- `Create Repair Job Service` opens a native Frappe Dialog with a compatible Link selector and a blank-service option.
- `Create Service Template` opens a native mapping flow that returns an unsaved editable Template form.
- Loading uses Frappe's native frozen-call/loading treatment; empty template lists explain that a blank service remains available; incompatible templates are not offered.
- Errors remain inline/native Frappe messages and never silently create records.
- Keyboard navigation must work through Link selection, dialog primary action, child-table editing, and standard Save/Cancel controls.

## Responsive and accessibility constraints

- Inherit Frappe Desk's responsive behavior; no fixed-width custom panel is allowed.
- Preserve visible labels, focus order, keyboard access, and standard Link-field semantics. Never rely on color alone for enabled, disabled, or compatibility state.
- Long service/template names and vehicle identifiers must truncate safely in lists while remaining available through the document title and search.

## Data and pricing behavior

- Templates store reusable scope only: service definition, parts, consumables, planned/billable labour hours, descriptions, billable flags, UOM, and consumption basis.
- Prices, discounts, costs, warehouses, assigned technicians, Tasks, Timesheets, actual hours, stock, Sales Orders, Sales Invoices, completion, and payment traces are excluded.
- Applying a template resolves current ERPNext prices and workshop defaults, then leaves the user with an unsaved editable service for review.

## Acceptance states

- Compatible model template: appears first and populates an editable service.
- Make-level template: appears after exact-model templates.
- Global template: appears after make-level templates.
- No compatible templates: clear empty state plus blank-service action.
- Existing customer with multiple vehicles: Customer dashboard shows vehicles and repair jobs; each vehicle form shows only its own repair history.
