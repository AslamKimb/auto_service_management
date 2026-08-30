---
id: SPEC-003
title: Fetch Repair Job work into draft or eligible submitted Sales Orders
dependencies: []
core_user_value: 4
architectural_risk: 5
implementation_effort: 5
---

## Source Contract Trace

- PRODUCT.md: AC-004 -> SPEC-003-AC-03; stale/invalid retrieval cannot create a false state.
- PRODUCT.md: AC-005 -> SPEC-003-AC-04; fetched components preserve fitment decisions and override authority.
- PRODUCT.md: AC-006 -> SPEC-003-AC-02; selected billable components produce reviewable traced commercial drafts.
- PRODUCT.md: AC-007 -> SPEC-003-AC-03; submitted ownership and duplicate billing remain blocked atomically.
- PRODUCT.md: AC-008 -> SPEC-003-AC-05; downstream stock authority and material-request safety remain unchanged.
- PRODUCT.md: AC-009 -> SPEC-003-AC-06; release/payment/credit gates remain unchanged by order retrieval.
- PRODUCT.md: AC-012 -> SPEC-003-AC-07; fetched traces do not broaden customer portal visibility.
- PRODUCT.md: AC-013 -> SPEC-003-AC-08; source, target, item, campaign, and LPO permissions remain server-enforced.
- PRODUCT.md: AC-014 -> SPEC-003-AC-09; installability and native compatibility remain regression gates.
- PRODUCT.md: AC-017 -> SPEC-003-AC-02; draft Sales Orders can review and fetch eligible Repair Job or Repair Job Service items.
- PRODUCT.md: AC-018 -> SPEC-003-AC-06; submitted Sales Orders update only through native eligibility and all app gates.
- ARCHITECTURE.md: AD-001, AD-002, AD-003, AD-004; modular-monolith boundaries, Repair Job/component ownership, POST-only mutations, and native Desk.
- ARCHITECTURE.md: Sections 5, 7-11, 14, 16, and 18; integration adapters, native frontend, ERPNext authority, permissions, APIs, tests, and explicit-site tooling.
- DESIGN.md: Sections 2, 8, 10, 13-15, 18-22; native Sales Order grouping/dialogs, readable state text, responsive tables, keyboard accessibility, and direct visual/interaction inspection.

## Objective

- Actor: Service Advisor or other user with permitted Sales Order and Repair Job scope.
- Trigger: The user opens `Get Items From` on a new/draft Sales Order or invokes the Repair Job retrieval action on an eligible submitted order.
- Primary goal: Select billable work from one eligible Repair Job or one exact eligible Repair Job Service and add it without losing native Sales Order authority.
- Observable outcome: Selected rows are appended exactly once with complete traces and native totals, or the target remains unchanged with an actionable server/native gate message.

## User Value

Staff can create or update a Sales Order from the same repair work already reviewed for invoicing. Draft and eligible submitted paths use one traceable selection experience while ERPNext continues to control pricing, taxes, stock, delivery, billing, reservations, and post-submit safety.

## Scope

- Extend the native Sales Order `Get Items From` surface with Repair Job, Repair Job Service, and preserved Quotation choices.
- Allow explicit selection of eligible billable Parts, Consumables, and Labour components from one Assessment-or-later Repair Job or one exact service in that state into a new or existing Draft Sales Order; Draft/Pre-Assessment sources are preview-only and cannot mutate rows.
- Allow the same selection into a submitted Sales Order only when the source is Assessment-or-later, native ERPNext update eligibility, app permissions, source ownership, customer match, and all business gates pass; keep the same submitted document and use its controlled update boundary.
- Preserve existing manual rows, mapped rows, component ownership, canonical Repair Job customer, immutable source/job/service/component IDs, customer/company/campaign/LPO traces, native recalculation, Quotation conversion, and Sales Order-to-Sales Invoice behavior; do not copy Contact name, phone, or email into Sales Order, invoice, print, or portal output.
- Reject non-billable, invoiced, reserved, duplicate, stale, mismatched, over-ceiling, or native-blocked selections atomically and permission-safely.
- Treat product-wide AC-004, AC-005, AC-008, AC-009, AC-012, AC-013, and AC-014 entries above as regression boundaries; this spec does not reimplement fitment, stock, release, portal, permission, or installation foundations.

## Out of Scope

- Editing ERPNext core, replacing native Quotation or Sales Order logic, unguarded submitted saves, amendment/replacement workflows, or a promise to bypass a native submitted-order restriction.
- Silent row merging, mixed unrelated jobs, changing source component values, changing invoices/payments/stock/credit state, or exposing internal traces to the portal.
- A custom Sales Order page, client-only authorization, automatic selection, or a new accounting/stock ledger.

## Dependencies

None - the slice consumes the existing Repair Job component mapping, ERPNext Sales Order, and Sales Invoice contracts. Its shared Repair Job source state with SPEC-001 and SPEC-002 is a resource synchronization point, not a hard dependency.

## Ordering Rationale

- Core user value: 4 - removes duplicate entry and keeps sales documents traceable to approved repair work.
- Architectural risk: 5 - spans native draft mapping, controlled post-submit updates, ownership/rollback, and downstream ERPNext compatibility.
- Implementation effort: 5 - requires source/component dialogs, server methods, native hooks, multiple document states, permissions, concurrency, and broad regression evidence.

## Affected Existing Functionality

Repair Job and Repair Job Service source mapping, Sales Order Quotation retrieval, native Sales Order `Update Items`, Sales Order-to-Sales Invoice conversion, component ownership/reservation, LPO/campaign ceiling controls, fitment/stock/release rules, dashboards, reports, prints, and permissions can regress. ERPNext pricing, tax, stock, delivery, billing, reservation, payment, and accounting controllers remain authoritative.

## Implementation Requirements

### Data

- [SPEC-003-AC-01, SPEC-003-AC-02, SPEC-003-AC-03, SPEC-003-AC-07, SPEC-003-AC-09] Requirement: preserve existing Sales Order/item trace fields and component identity while appending only selected authoritative rows; Evidence: metadata, mapping, migration, and downstream-invoice tests show exact source/job/service/component traces with no duplicate or portal leakage.

### Authorization

- [SPEC-003-AC-02, SPEC-003-AC-03, SPEC-003-AC-08] Requirement: enforce source read, target create/write/submitted-write, Item/customer, campaign, LPO, and component ownership permissions server-side; Evidence: permitted and denied calls return only safe data and never partially mutate a target.

### Business Logic

- [SPEC-003-AC-01, SPEC-003-AC-02, SPEC-003-AC-03, SPEC-003-AC-04, SPEC-003-AC-05, SPEC-003-AC-06] Requirement: resolve one Assessment-or-later job/service source, filter billable/unowned rows, require the source and Sales Order customers to match, obey fitment/stock/release/native submitted gates, preserve manual rows, and roll back atomically; Evidence: draft/submitted integration tests prove exact rows, totals, ownership, source-state eligibility, and unchanged failures.

### API

- [SPEC-003-AC-01, SPEC-003-AC-02, SPEC-003-AC-03, SPEC-003-AC-08] Requirement: provide GET-only permission-scoped previews and typed POST-only draft/submitted retrieval methods that re-fetch source, canonical customer, target, ownership, and native state before mutation; return selected/available counts, immutable source IDs, and stable source-state/customer/permission/stale errors, with no Contact personal details; Evidence: RPC contract tests prove methods, version checks, response shape, customer binding, and no controller commit.

### State

- [SPEC-003-AC-01, SPEC-003-AC-02, SPEC-003-AC-03, SPEC-003-AC-06] Requirement: represent source loading, empty, available/present/invoiced/blocked rows, draft append, submitted preview-only/eligible update, stale conflict, rollback, and success without changing Sales Order identity/docstatus incorrectly; Evidence: state and rollback tests prove idempotency, customer/source-state gates, and native gate preservation.

### UI

- [SPEC-003-AC-01, SPEC-003-AC-02, SPEC-003-AC-03, SPEC-003-AC-07, SPEC-003-AC-08] Requirement: extend native `Get Items From` grouping/dialogs, explicit checkboxes with selected/available counts and review-before-save, semantic text states, focus order, WCAG 2.2 AA labels/contrast/status/errors, text reflow, touch targets, reduced motion, responsive scrolling, and post-success refresh without replacing ERPNext behavior; Evidence: authenticated Desk scenarios cover draft, submitted, preview-only, empty, denied, stale, long-content, keyboard, and no-overflow states.

### Automated Tests

- [SPEC-003-AC-01, SPEC-003-AC-02, SPEC-003-AC-03, SPEC-003-AC-04, SPEC-003-AC-09] Requirement: cover source menu, exact job/service scope, source-state/customer gates, draft/manual-row idempotency, submitted same-document updates, duplicate/ownership/stale rollback, native Quotation/Invoice mapping, and install/reinstall; Evidence: unit, integration, and regression suites assert exact document names, rows, traces, source eligibility, and unchanged failures.
- [SPEC-003-AC-05, SPEC-003-AC-06, SPEC-003-AC-08] Requirement: cover fitment, stock, invoice/payment/release, customer/company/LPO/campaign, native restriction, and permission boundaries; Evidence: negative and permission tests show no bypass, over-ceiling state, hidden data, or partial mutation.
- [SPEC-003-AC-07] Requirement: cover submitted-only portal privacy after fetched-order traces exist; Evidence: portal tests show authorized submitted repair/finance data only.

### User Verification

- [SPEC-003-AC-01, SPEC-003-AC-02, SPEC-003-AC-03] Runtime: authenticated Frappe/ERPNext v16 Desk; Setup: create a new/draft Sales Order, a pre-Assessment and an Assessment-or-later Repair Job with multiple services, plus an eligible submitted order; Action: preview each source, open `Get Items From`, choose one eligible job/service, select rows, review counts, repeat once, and use the submitted action; Expected: pre-Assessment is preview-only, eligible success preserves Quotation/manual rows, same submitted order identity, native totals, exact immutable traces, and no duplicate rows.
- [SPEC-003-AC-04, SPEC-003-AC-05, SPEC-003-AC-06, SPEC-003-AC-08] Runtime: authenticated Desk at 1310x683, tablet width, and 390x844; Setup: use fitment warning, non-billable/invoiced/reserved, customer/LPO mismatch, stale, denied, closed/fully billed submitted, empty, and long-content states; Action: inspect statuses, keyboard-select, cancel, retry, and refresh; Expected: alternate/error/denied states remain actionable, native gates are visible in text, no hidden data or partial rows occur, and no page-level overflow appears.
- [SPEC-003-AC-07, SPEC-003-AC-09] Runtime: authenticated Desk and customer portal; Setup: fetched order with job/service/vehicle/LPO traces and isolated install/reinstall; Action: render downstream Sales Invoice/print and open `/my-repairs`; Expected: traces/totals/terms remain correct, portal privacy is unchanged, and install/reinstall preserves the package without core edits.

## Security and Permission Requirements

- Permitted actor: a user with the existing source, target, Item/customer, and relevant submitted-write/campaign/LPO permissions; role assignment remains governed by Frappe/ERPNext policy.
- Forbidden actor: guest, unauthorized staff, unrelated customer, or caller without the source/target row scope attempting preview or mutation.
- Unauthenticated behavior: no guest source preview or Sales Order mutation is exposed.
- Data boundary: reveal only permitted source rows and target-safe status; do not disclose hidden customer, component, invoice, order, price, margin, LPO, or ownership details.
- Safe failure: reject before mutation on every source/target/native/app gate, roll back the entire operation, and state the next safe action such as refresh, change source, deselect, or use the native workflow.

## Edge Cases

- A new Sales Order with no Customer cannot fetch until the source Customer can be set/validated; a different target Customer is rejected.
- A draft with manual rows preserves them; repeated retrieval marks present component identities and appends only new eligible rows.
- A service source cannot include a sibling-service component; a job source cannot silently mix unrelated jobs.
- A submitted order that is closed, fully delivered/billed, cancelled, subcontracted, reserved, stale, or not write-permitted remains unchanged and exposes no bypass.
- Invoiced/owned/non-billable/fitment-blocked/LPO-over-ceiling rows fail atomically; two components resolving to one Item do not lose identity.
- Native Sales Order-to-Sales Invoice mapping, Quotation conversion, customer-vehicle/campaign/LPO traces, and portal scope remain valid after a successful fetch.
- Large rows and long descriptions use native dialog/table scrolling and do not clip identifiers or create page-level overflow.

## Automated Tests

### Unit Tests

- [SPEC-003-AC-01, SPEC-003-AC-02, SPEC-003-AC-03, SPEC-003-AC-04] Setup: use pre-Assessment/Assessment-or-later, job-wide, service-specific, customer-match/mismatch, manual-row, duplicate, and repeated-fetch fixtures; Action: preview and map selected rows; Assertion: source eligibility, exact scope, canonical customer binding, immutable trace identity, idempotency, and preserved existing rows are enforced.
- [SPEC-003-AC-05, SPEC-003-AC-06, SPEC-003-AC-08] Setup: use fitment, invoice, reservation, LPO, native-state, stale, and permission fixtures; Action: attempt allowed and blocked operations; Assertion: server rules reject safely with no partial target/source/financial change.

### Integration/API Tests

- [SPEC-003-AC-01, SPEC-003-AC-02, SPEC-003-AC-03, SPEC-003-AC-09] Setup: create new/draft/submitted Sales Orders and Repair Job/Service sources; Action: call GET previews and POST retrievals, then map a downstream invoice; Assertion: native Quotation behavior, same submitted name/docstatus, complete traces, totals, ownership, and invoice conversion remain correct.
- [SPEC-003-AC-04, SPEC-003-AC-05, SPEC-003-AC-06, SPEC-003-AC-07, SPEC-003-AC-08] Setup: use conflicts, denied users, portal users, LPO ceilings, and concurrent selections; Action: submit stale/duplicate/unauthorized/over-ceiling requests; Assertion: rollback is complete, retry guidance is safe, and portal/permission data is scoped.

### UI Tests

- [SPEC-003-AC-01, SPEC-003-AC-02, SPEC-003-AC-03, SPEC-003-AC-04] Setup: use native Sales Order source menu/dialogs and realistic item rows; Action: preview pre-Assessment, choose an eligible job/service, select/deselect, review counts, cancel, repeat, and refresh; Assertion: grouping, focus, state labels, customer/source-state gates, manual rows, traces, totals, and idempotency match.
- [SPEC-003-AC-05, SPEC-003-AC-06, SPEC-003-AC-07, SPEC-003-AC-08] Setup: use empty, loading, denied, error, long, narrow, submitted-blocked, LPO, print, and portal states; Action: keyboard-navigate and inspect downstream results; Assertion: native controls remain readable/operable, no privacy leak or clipping occurs, and next actions are visible.

## UI Verification Scenarios

- [SPEC-003-AC-01, SPEC-003-AC-03] Runtime: authenticated Frappe Desk; Viewport/device: desktop 1310x683; State/data: new/draft order, manual rows, pre-Assessment source, job-wide source, service-specific source, and eligible submitted order; Interaction: preview, open source menu, select rows, review counts, cancel, repeat, and refresh; Expected: pre-Assessment remains preview-only, eligible success preserves Quotation/manual rows, appends exact rows once, shows immutable traces/totals, and updates the same submitted order only through the native boundary.
- [SPEC-003-AC-05, SPEC-003-AC-06, SPEC-003-AC-08] Runtime: authenticated Frappe Desk; Viewport/device: narrow 390x844 and tablet width; State/data: loading, empty, no eligible, fitment warning, invoiced/owned, denied, stale, customer mismatch, LPO ceiling, and long descriptions; Interaction: keyboard-focus controls, scroll rows, cancel, retry, and inspect errors; Expected: alternate/error/denied states use readable text and next actions, focus remains visible, native tables stay contained, and no partial mutation or page overflow occurs.
- [SPEC-003-AC-07, SPEC-003-AC-09] Runtime: authenticated Desk and customer portal; Viewport/device: desktop and narrow; State/data: fetched traces, downstream Sales Invoice/Proforma, and two portal scopes; Interaction: render/refresh documents and open `/my-repairs`; Expected: invoice/print values and traces remain correct, only authorized submitted portal data appears, and installation compatibility is preserved.

## Acceptance Criteria

- [ ] SPEC-003-AC-01: Given a permitted user opens a new or Draft Sales Order, when `Get Items From` is opened, then Repair Job, Repair Job Service, and the existing Quotation choices appear in the native grouping and Quotation retains its current behavior.
- [ ] SPEC-003-AC-02: Given a permitted Draft Sales Order and one Repair Job or exact Repair Job Service, when the user selects eligible billable components, then exactly those rows append with complete traces, matching customer/company context, native totals, and all pre-existing rows unchanged.
- [ ] SPEC-003-AC-03: Given a draft or eligible submitted target contains existing component rows, when the user repeats a compatible fetch or submits a stale/duplicate/owned selection, then present identities are not duplicated and every rejected operation leaves the target/source and ownership unchanged.
- [ ] SPEC-003-AC-04: Given a component has exact, broad, provisional, missing-data, or mismatched fitment state, when it is offered for retrieval, then its existing warning/override requirement is shown and cannot be bypassed by Sales Order selection.
- [ ] SPEC-003-AC-05: Given a fetched order is later used in stock, when native ERPNext material/stock workflows run, then warehouse, quantity, purpose, and Material Issue-only Stock Entry behavior remain unchanged.
- [ ] SPEC-003-AC-06: Given a submitted Sales Order is not closed, fully delivered, fully billed, cancelled, subcontracted, or otherwise native-blocked and the user has write permission, when eligible components are selected, then the same submitted Sales Order is updated atomically through its controlled boundary; otherwise the action is unavailable or rejected with no mutation.
- [ ] SPEC-003-AC-07: Given fetched job/service/vehicle/campaign/LPO traces exist, when downstream invoice/print and customer portal views are opened, then traces, totals, terms, and submitted-only customer scope remain correct without exposing internal data.
- [ ] SPEC-003-AC-08: Given the user lacks source, target, Item/customer, submitted-write, campaign, or LPO scope, when preview or retrieval is attempted, then only permission-safe data is returned and the mutation is denied without hidden values.
- [ ] SPEC-003-AC-09: Given a fresh, repeated, or uninstall/reinstall cycle, when Sales Order feature metadata and mappings are synchronized, then no ERPNext core file is changed, native Quotation/Invoice behavior remains available, and no unfiltered fixture or duplicate trace is introduced.

## Definition of Done

- [ ] All acceptance criteria are implemented later inside the app through native Frappe/ERPNext extension points with no core edits.
- [ ] Automated unit, integration/API, permission, concurrency, rollback, migration, downstream invoice, portal, and regression tests provide evidence for every criterion.
- [ ] User/UI verification covers draft, submitted, loading, empty, no-eligible, denied, stale, conflict, long-content, keyboard, narrow, LPO, print, and portal states.
- [ ] Security and permission checks prove no source, ownership, financial, or customer privacy leak.
- [ ] Quotation retrieval, Repair Job/Service mapping, Sales Order-to-Sales Invoice, fitment, stock, release, LPO/campaign, dashboards, reports, and prints regressions are recorded.
- [ ] Documentation, PROGRESS.md, coherence evidence, and the downstream execution map reconcile before separate implementation authorization.
