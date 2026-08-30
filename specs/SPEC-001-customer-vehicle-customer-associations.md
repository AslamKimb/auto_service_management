---
id: SPEC-001
title: Reassociate an existing Customer Vehicle across dated customer visits
dependencies: []
core_user_value: 5
architectural_risk: 5
implementation_effort: 5
---

## Source Contract Trace

- PRODUCT.md: AC-001 -> SPEC-001-AC-01; intake identity, duplicate prevention, and Customer Vehicle search.
- PRODUCT.md: AC-002 -> SPEC-001-AC-03; new Repair Job visit and idempotent ERPNext Project creation.
- PRODUCT.md: AC-003 -> SPEC-001-AC-11; optional evidence remains non-blocking during reassociation.
- PRODUCT.md: AC-004 -> SPEC-001-AC-05; invalid or unauthorized workflow actions remain atomic.
- PRODUCT.md: AC-010 -> SPEC-001-AC-06; Gate Pass closure and Service History preservation.
- PRODUCT.md: AC-011 -> SPEC-001-AC-07; Customer LPO vehicle association and one-job-per-vehicle controls.
- PRODUCT.md: AC-012 -> SPEC-001-AC-08; submitted portal privacy after reassociation.
- PRODUCT.md: AC-013 -> SPEC-001-AC-09; permission-scoped association reads and mutations.
- PRODUCT.md: AC-014 -> SPEC-001-AC-10; migration, install, and reinstall safety as regression gates.
- PRODUCT.md: AC-015 -> SPEC-001-AC-03; one reused vehicle may have explicit, dated customer associations while each visit retains its canonical customer.
- ARCHITECTURE.md: AD-001, AD-002, AD-003, AD-004; app-owned workshop records, Repair Job aggregate, server-authoritative POST mutations, and native Frappe surfaces.
- ARCHITECTURE.md: Sections 5, 8-11, 16, and 18; domain/integration boundaries, permissions, API semantics, testing, and explicit-site tooling.
- DESIGN.md: Sections 2, 8, 10, 13-15, 18-20, and 22; native identity-first forms, readable states, responsive tables, accessibility, and direct runtime inspection.

## Objective

- Actor: Service Advisor.
- Trigger: The advisor creates or checks in a visit for a vehicle whose current customer is blank or different from the visit customer.
- Primary goal: Reuse one Customer Vehicle identity while recording the customer associated with each sequential visit.
- Observable outcome: The confirmed association interval becomes current, the new Repair Job retains its visit customer, and prior customer history remains unchanged.

## User Value

The workshop avoids duplicate vehicle masters when responsibility or ownership changes. Staff can see the dated customer relationship without rewriting old jobs, billing, payment, portal, or service-history context.

## Scope

- Make `Customer Vehicle.customer` optional for vehicle creation while retaining registration/VIN identity and make/model/engine validation.
- Add an app-owned append-only association record with vehicle, customer, start/end timestamps, source trace, and server audit metadata.
- Create an initial interval only when a new vehicle has a customer; leave a newly unassigned vehicle without a current association.
- Provide a permission-checked POST association action, one open interval per vehicle, atomic close/open timestamps, and idempotent repeat requests.
- Bind the visit's `Repair Job.customer` as the canonical customer for reassociation, Contact validation, and downstream matching; reuse an existing vehicle in a new Repair Job or Customer LPO flow only after explicit confirmation when the requested customer differs.
- Show a read-only chronological association timeline on native Customer Vehicle/Customer dashboard surfaces and preserve per-visit customer snapshots.
- Treat product-wide AC-004, AC-010, AC-011, AC-012, AC-013, and AC-014 entries above as regression boundaries; AC-003 is explicitly covered by SPEC-001-AC-11, while this spec does not reimplement the other existing capabilities.

## Out of Scope

- Concurrent co-ownership, multiple current customers, household semantics, or customer-scoped vehicle identifiers.
- Changing the required Repair Job customer, one-vehicle/one-Project rule, ERPNext accounting/stock authority, portal mutation boundary, or existing historical records.
- Silent reassignment from a Link-field selection, automatic inference from untrusted text, bulk ownership import, custom portal pages, or guessed historical dates.

## Dependencies

None - the slice consumes the existing Customer Vehicle and Repair Job contracts. Shared Repair Job Check In behavior with SPEC-002 is a resource synchronization point, not a hard dependency.

## Ordering Rationale

- Core user value: 5 - prevents duplicate vehicle identity and restores safe cross-customer intake.
- Architectural risk: 5 - changes a customer pointer into an audited time-bounded association without corrupting historical consumers.
- Implementation effort: 5 - spans data, migration, permissioned actions, Repair Job/LPO matching, native history surfaces, and privacy regression checks.

## Affected Existing Functionality

Customer Vehicle creation/search, Repair Job Check In and customer synchronization, Customer LPO resolution, Customer/Customer Vehicle dashboards, Service History, invoices/payments, Gate Pass closure, reports, and the submitted-only portal can regress. The current vehicle identity master, Repair Job customer snapshot, ERPNext authority, and native Frappe navigation remain authoritative.

## Implementation Requirements

### Data

- [SPEC-001-AC-01, SPEC-001-AC-02, SPEC-001-AC-06, SPEC-001-AC-08, SPEC-001-AC-10, SPEC-001-AC-11] Requirement: store a nullable current Customer Vehicle customer plus append-only association intervals and immutable per-visit Repair Job customer snapshots with valid links, server timestamps, source trace, audit metadata, and idempotent migration; Evidence: metadata, database, migration, and repeated-install tests show no duplicate intervals or changed legacy records.

### Authorization

- [SPEC-001-AC-05, SPEC-001-AC-07, SPEC-001-AC-09] Requirement: enforce Customer Vehicle/Customer/Repair Job/LPO permissions and row scope on every read and mutation; Evidence: denied users receive safe errors and no pointer, association, job, LPO, or portal data changes.

### Business Logic

- [SPEC-001-AC-02, SPEC-001-AC-03, SPEC-001-AC-04, SPEC-001-AC-05, SPEC-001-AC-06, SPEC-001-AC-07, SPEC-001-AC-11] Requirement: one server-side Check In orchestration validates the canonical `Repair Job.customer`, Contact/company rules, active conflicts, and vehicle reassociation before atomically creating one Project path, one visit snapshot, and one interval transition; repeated identical requests are no-ops, stale/conflicting requests roll back, and optional evidence remains non-blocking; Evidence: integration scenarios prove interval ordering, idempotency, old-record preservation, optional-evidence progression, and exact rejection reasons.

### API

- [SPEC-001-AC-02, SPEC-001-AC-03, SPEC-001-AC-05, SPEC-001-AC-07, SPEC-001-AC-09, SPEC-001-AC-11] Requirement: expose `associate_customer(customer_vehicle, customer, expected_version, idempotency_key)` and `RepairJob.check_in(confirm_customer_association, expected_version, idempotency_key)` as typed POST actions plus `get_customer_vehicle_association_history(customer_vehicle)` as a GET read; re-fetch vehicle, job, customer, Contact, and Project state server-side, return HTTP 200 with typed `message` on success, return stable `PERMISSION_DENIED`, `VALIDATION_FAILED`, `STALE_REQUEST`, or `ACTIVE_CONFLICT` errors with no mutation on failure, and make a replay return the existing state; Evidence: method contract tests prove route/method declarations, request/response fields, server re-fetch, permission checks, replay behavior, and no controller commit.

### State

- [SPEC-001-AC-02, SPEC-001-AC-03, SPEC-001-AC-04, SPEC-001-AC-06, SPEC-001-AC-07, SPEC-001-AC-11] Requirement: model blank, current, superseded, confirmed, cancelled, stale, loading, empty, denied, error, success, and migration states without overlapping open intervals, blocking optional evidence, or rewriting old visit state; shared Check In validates all sibling inputs first and commits vehicle interval, canonical visit customer, Contact snapshot, status, and Project as one transaction; Evidence: state-transition tests show unchanged data on cancel/conflict, one current interval after success, replay no-op behavior, and optional records do not regress a valid path.

### UI

- [SPEC-001-AC-01, SPEC-001-AC-02, SPEC-001-AC-03, SPEC-001-AC-08, SPEC-001-AC-09, SPEC-001-AC-11] Requirement: put vehicle identity, canonical visit customer, current status, and available actions before primary actions, then use native Frappe forms, Link/action confirmation, read-only association timeline, consistent text states, keyboard focus, WCAG 2.2 AA contrast/labels/status/error semantics, text reflow, touch targets, reduced motion, and responsive table behavior at 1310x683 desktop, 768x1024 tablet, and 390x844 narrow viewports; Evidence: authenticated Desk plus Job Card/Repair Summary HTML/PDF scenarios show optional Customer, explicit reassociation, chronological history, discoverable actions, selected/total counts, optional-evidence non-blocking states, correct print identity/traces/terms/signatures, and no page-level or measured container overflow.

### Automated Tests

- [SPEC-001-AC-01, SPEC-001-AC-02, SPEC-001-AC-04, SPEC-001-AC-10, SPEC-001-AC-11] Requirement: cover nullable metadata, blank creation, interval constraints, idempotency/replay, immutable visit snapshots, and repeated migration; Evidence: unit/controller/migration assertions prove exact rows, timestamps, snapshot values, replay no-op behavior, and preserved legacy values.
- [SPEC-001-AC-03, SPEC-001-AC-05, SPEC-001-AC-06, SPEC-001-AC-07, SPEC-001-AC-09] Requirement: cover confirmed/cancelled/stale reassociation, Repair Job/LPO matching, closure, and denied access; Evidence: integration and permission tests prove atomic rollback and scoped results.
- [SPEC-001-AC-08] Requirement: cover portal and dashboard privacy for two customers sharing one vehicle; Evidence: permitted and unrelated users receive only authorized submitted records.

### User Verification

- [SPEC-001-AC-01, SPEC-001-AC-02, SPEC-001-AC-03, SPEC-001-AC-08] Runtime: authenticated Frappe/ERPNext v16 Desk and customer portal; Setup: create one blank vehicle, associate Customer A, then use the same vehicle for Customer B; Action: save, associate, confirm Check In, open history, and open each portal session; Expected: the vehicle is not duplicated, intervals are chronological/read-only, each visit retains its customer, and portal data remains customer-scoped.
- [SPEC-001-AC-05, SPEC-001-AC-07, SPEC-001-AC-09] Runtime: authenticated Desk at 1310x683 and 390x844; Setup: use denied, loading, stale, empty-history, long-history, and LPO mismatch states; Action: cancel confirmation, retry a conflict, navigate by keyboard, and inspect dashboard links; Expected: state text and next actions are clear, no unauthorized data appears, native controls remain usable, and no page-level horizontal overflow occurs.

## Security and Permission Requirements

- Permitted actor: Service Advisor, Workshop Manager, or Auto Service Admin with existing Customer Vehicle/Customer/Repair Job/LPO permissions.
- Forbidden actor: unauthorized staff, unrelated customer, guest, or portal user attempting association mutation or cross-customer history enumeration.
- Unauthenticated behavior: no association read or mutation endpoint is available to guest callers.
- Data boundary: return only permitted vehicle, customer, association, visit, LPO, dashboard, and submitted portal records; never expose another customer's relationship through search, errors, or counts.
- Safe failure: reject before mutation with an actionable permission, confirmation, stale, or active-conflict message and preserve all existing records.

## Edge Cases

- A vehicle remains unassigned until a later explicit association; registration/VIN search still works.
- A→B→A creates three bounded intervals, while repeating the current customer creates no new row.
- An active conflicting Repair Job, stale document, invalid link, duplicate identifier, or cancelled confirmation leaves all records unchanged.
- Existing vehicles receive exactly one migration association from original creation time; repeated migration is a no-op.
- Prior and later portal customers see only their own submitted repairs, and long histories remain native-scrollable and readable.

## Automated Tests

### Unit Tests

- [SPEC-001-AC-01, SPEC-001-AC-02, SPEC-001-AC-04] Setup: use valid, blank, current, and repeated association fixtures; Action: create and reassociate vehicles; Assertion: nullable creation, one open interval, ordered timestamps, and idempotent rows are enforced.
- [SPEC-001-AC-05, SPEC-001-AC-06, SPEC-001-AC-10] Setup: use invalid transitions, Gate Pass closure, and legacy vehicles; Action: attempt each state or run migration twice; Assertion: failures are atomic, closure remains idempotent, and legacy values are unchanged.

### Integration/API Tests

- [SPEC-001-AC-03, SPEC-001-AC-07, SPEC-001-AC-09] Setup: create prior A and later B visits plus an LPO row; Action: call the typed POST association/check-in and GET history methods as permitted and denied users; Assertion: explicit confirmation succeeds only in scope, LPO rules remain intact, and denied/unauthenticated data is not returned.
- [SPEC-001-AC-08] Setup: link portal users to A and B; Action: open submitted portal queries after reassociation; Assertion: each result set excludes the other customer's jobs and the internal timeline.

### UI Tests

- [SPEC-001-AC-01, SPEC-001-AC-02, SPEC-001-AC-03, SPEC-001-AC-05, SPEC-001-AC-11] Setup: use native Customer Vehicle and Repair Job forms; Action: save blank, associate, cancel, confirm, replay, and refresh; Assertion: optional Customer, canonical visit customer, required markers, warning text, focus, read-only history/snapshot, replay no-op, and unchanged cancelled state match the contract.
- [SPEC-001-AC-07, SPEC-001-AC-08, SPEC-001-AC-09] Setup: use LPO, portal, denied, narrow, and long-history fixtures; Action: navigate, scroll, and inspect errors; Assertion: scope, text states, responsive layout, and no-clipping behavior pass.

## UI Verification Scenarios

- [SPEC-001-AC-01, SPEC-001-AC-02, SPEC-001-AC-03] Runtime: authenticated Frappe Desk; Viewport/device: desktop 1310x683; State/data: new blank vehicle and A→B associations; Interaction: save, associate, confirm reassignment, and open the timeline; Expected: normal success state shows optional Customer, one current interval, equal close/open timestamp, readable chronology, and prior rows unchanged.
- [SPEC-001-AC-05, SPEC-001-AC-07, SPEC-001-AC-09] Runtime: authenticated Frappe Desk; Viewport/device: narrow 390x844 and tablet width; State/data: cancelled confirmation, denied user, stale request, empty history, long customer names, and LPO mismatch; Interaction: keyboard-focus actions, cancel, retry, and inspect errors; Expected: alternate/error/denied states provide next actions, hide unauthorized values, keep focus visible, and avoid page-level overflow.
- [SPEC-001-AC-08] Runtime: authenticated customer portal; Viewport/device: desktop and narrow; State/data: two customers with submitted visits on one vehicle; Interaction: refresh each `/my-repairs` session; Expected: each session shows only its own submitted repair/finance data and no association timeline or other customer's job.

## Acceptance Criteria

- [ ] SPEC-001-AC-01: Given a permitted Service Advisor and valid vehicle identity, when the advisor creates a Customer Vehicle without Customer, then it saves with a blank current customer and remains searchable without creating a duplicate.
- [ ] SPEC-001-AC-02: Given a saved vehicle with no current association, when the advisor associates Customer A, then one open interval is recorded with a server timestamp and A becomes current.
- [ ] SPEC-001-AC-03: Given a vehicle currently associated with A, when the advisor explicitly confirms a B visit at Repair Job Check In, then A closes where B begins, the new job records B, and the vehicle master is reused.
- [ ] SPEC-001-AC-04: Given a vehicle currently associated with B, when the advisor repeats the B association request, then no duplicate interval is created and existing timestamps remain unchanged.
- [ ] SPEC-001-AC-05: Given a cancelled confirmation, invalid transition, stale document, active conflict, or denied user, when reassociation or Check In is attempted, then the server rejects it and records no false state change.
- [ ] SPEC-001-AC-06: Given a later customer uses a vehicle with an earlier closed job, when the earlier job closes through its valid Gate Pass path, then one Service History snapshot and the approved vehicle updates remain tied to that earlier visit.
- [ ] SPEC-001-AC-07: Given a Customer LPO customer differs from the vehicle's current customer, when resolution runs before explicit association and after explicit association, then the first attempt is blocked and the second obeys one-vehicle-per-job and ceiling rules without duplication.
- [ ] SPEC-001-AC-08: Given two customers have submitted visits for one vehicle, when each customer or an unrelated user opens permitted portal/history surfaces, then only authorized submitted records are shown and the internal association timeline is not exposed.
- [ ] SPEC-001-AC-09: Given a user lacks the required row or document scope, when the user reads or mutates association data, then access is denied without leaking customer names, counts, timestamps, or linked totals.
- [ ] SPEC-001-AC-10: Given an isolated install or migration is repeated, when the association schema/backfill runs, then no core file is edited, no duplicate backfill appears, and existing vehicle, Repair Job, finance, and Service History values remain unchanged.
- [ ] SPEC-001-AC-11: Given optional inspection evidence is absent during a valid blank-to-customer or A-to-B visit reassociation, when the shared Check In orchestration runs, then evidence absence does not block or regress the visit, while the canonical visit customer, immutable visit snapshot, Project path, and vehicle interval transition are committed exactly once.

## Definition of Done

- [ ] All acceptance criteria are implemented later without changing ERPNext/Frappe core or historical identifiers.
- [ ] Automated unit, integration/API, permission, migration, portal, and regression tests provide evidence for every criterion.
- [ ] User and UI verification covers success, loading, empty, denied, stale, cancellation, long-content, keyboard, narrow, and portal states.
- [ ] Security and permission checks prove no cross-customer association or history leakage.
- [ ] Shared Check In tests prove validation-before-mutation, replay no-op, stale/conflict rollback, one Project path, one visit snapshot, and one interval transition across vehicle/customer/contact inputs.
- [ ] Affected Repair Job, LPO, billing, release, closure, dashboard, and portal regressions are tested.
- [ ] Documentation, PROGRESS.md, coherence evidence, and the downstream execution map reconcile before separate implementation authorization.
