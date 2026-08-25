# Spare-Parts Item and Vehicle Fitment Design Contract

## Intent and audience

This is a native Frappe Desk workflow for Parts Interpreters, Service Advisors, Workshop Managers, and Technicians. It must let staff create one reusable ERPNext Item, attach verified or provisional vehicle/engine fitment, and select suitable parts from a Repair Job without splitting stock by vehicle.

## Reference direction and principles

- Follow the approved Car Workshop and Repair Job native Frappe patterns: standard forms, Link fields, child tables, list views, badges, dialogs, and breadcrumbs.
- ERPNext Item remains the authority for stock, UOM, warehouse, pricing, barcode, brand, and manufacturer part number.
- Customer Vehicle remains the authority for vehicle identity. Engine serial number and engine model/code are separate fields.
- Fitment is many-to-many. Never create Item Variants merely because one part fits several vehicles.
- Compatibility is evidence-led: unknown or provisional rows are visible and warn users; the system never invents a match.

## Color, typography, density, and surfaces

- Reuse Frappe Desk typography, spacing, colors, badges, and surfaces. No custom palette, font, shadow system, or decorative visual shell.
- Use standard two-column master-form density and the normal Frappe child-table grid for fitment rows.
- Use native status treatments: verified/strong match uses the existing success treatment; provisional or broad match uses warning/neutral treatment; mismatch uses the existing danger treatment.

## Layout and navigation

- Vehicle Engine is a normal master form with engine code/name and concise technical notes.
- Item Vehicle Fitment is maintained from its native list/form and exposed from the linked Item context; the Item form remains the stock master.
- Customer Vehicle shows Make, Model, Engine Model, and Engine Serial Number in the vehicle-details area.
- Repair Job Service Part keeps the normal Item Link field and child-table layout. Compatibility status, matched fitment, warning, and override reason are visible in the standard grid/form context; no custom SPA or fixed-width panel.

## Interaction and component states

- Exact model + engine + year matches rank first, followed by broader model/make/universal matches.
- `Verified`, `Provisional`, `Broad match`, `Mismatch`, loading, empty, and server-error states must be distinguishable through text/labels as well as color.
- Warn-and-allow is the approved policy: selecting a provisional, broad, or mismatched part requires a concise override reason; it does not block legitimate workshop work.
- Loading uses native Frappe link/search treatment. Empty results explain that no recorded fitment exists and allow normal Item search. Errors remain visible native messages and never silently select a part.

## Responsive and accessibility constraints

- Inherit Frappe Desk responsive behavior; no fixed-width custom panel.
- Preserve labels, keyboard focus order, standard Link semantics, and screen-reader-readable status text. Never rely on color alone.
- Long Item names, part numbers, vehicle names, and engine codes must remain searchable and truncate safely in lists.

## Acceptance states

- One Item with multiple verified fitments shows one stock identity and several compatibility rows.
- Exact match is clearly preferred over broader matches.
- Missing fitment data produces a visible warning, not a false “compatible” claim.
- A mismatch can be saved only with an override reason recorded on the Repair Job part row.
- Narrow viewport preserves the Item link, match status, and save/validation controls without clipping.
