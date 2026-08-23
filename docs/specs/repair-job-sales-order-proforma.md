# Repair Job Sales Order / Proforma Invoice Specification

## Functional contract

- Repair Job and Repair Job Service expose Sales Order creation, not Quotation creation.
- The selector combines eligible Parts, Consumables, and Labour from Repair Job Services and permits explicit inclusion/exclusion.
- Mapping creates an unsaved draft for review. Multiple drafts are allowed as revisions; only one overlapping submitted order may own a component.
- A submitted order cannot overlap a submitted Sales Invoice. Cancelled orders release their component links.
- Repair Job lists every linked Sales Order, with status, dates, total, and billing state.
- Native Sales Order-to-Sales Invoice mapping preserves Repair Job and component trace fields; direct invoice mapping uses a unique accepted Sales Order link when present.

## Print contract

All Sales Orders use the “Proforma Invoice” print heading. The app-owned editable format is “DMS Editable - Proforma Invoice”, and the standard app format renders the Proforma Invoice template.

## Permissions and compatibility

Mutation methods are POST-only and enforce source read/write and target create permissions. Component summaries are GET-only. Historical Quotation data and read-only compatibility endpoints remain supported without exposing new Quotation creation actions.

## Acceptance evidence

Focused contracts, Python/JavaScript syntax checks, migration, asset build, live Desk interaction, and HTML/PDF output inspection are required before release. Image build and deployment remain outside this change until explicit UAT approval.
