---
id: SPEC-002
title: Capture the company contact for each Repair Job visit
dependencies: []
core_user_value: 4
architectural_risk: 5
implementation_effort: 4
---

## Source Contract Trace

- PRODUCT.md: AC-002 -> SPEC-002-AC-02; Company Repair Job Check In remains a valid new visit with one Project.
- PRODUCT.md: AC-003 -> SPEC-002-AC-03; optional evidence remains non-blocking for the contact flow.
- PRODUCT.md: AC-004 -> SPEC-002-AC-05; invalid, stale, or unauthorized contact actions do not change workflow state.
- PRODUCT.md: AC-012 -> SPEC-002-AC-07; company-contact details do not broaden the submitted-only portal boundary.
- PRODUCT.md: AC-013 -> SPEC-002-AC-08; Contact lookup and job reads remain permission-scoped.
- PRODUCT.md: AC-014 -> SPEC-002-AC-09; installability and legacy compatibility remain regression gates.
- PRODUCT.md: AC-016 -> SPEC-002-AC-02; Company jobs capture one validated Contact snapshot while Individual jobs remain valid without Contact.
- ARCHITECTURE.md: AD-001, AD-002, AD-003, AD-004; native ERPNext Contact identity, Repair Job aggregate ownership, server-authoritative mutations, and native Desk/print surfaces.
- ARCHITECTURE.md: Sections 5, 8-11, 16, and 18; domain boundaries, document validation, permissions, typed RPC, testing, and explicit-site tooling.
- DESIGN.md: Sections 2, 8, 10, 13-15, 18-20, and 22; identity-first Repair Job forms, company/individual states, native controls, accessibility, responsive layout, and direct inspection.

## Objective

- Actor: Service Advisor.
- Trigger: The advisor checks in a Draft Repair Job for a Company Customer.
- Primary goal: Record the person handled for that specific job without changing the company Customer master.
- Observable outcome: The job enters Assessment with a validated Contact and immutable server snapshot, or remains Draft with a specific corrective error.

## User Value

The workshop can identify who brought a company vehicle on each visit. Company-level billing and portal identity stay intact, while separate jobs for the same company retain the person-specific context needed by staff and customers.

## Scope

- Add an optional-on-Draft `Repair Job.contact_person` Link to the native ERPNext `Contact`, labelled `Company Contact / Responsible Person`.
- Require the Contact only at Check In when the authoritative `Repair Job.customer` is a Company, validate its Customer link, and capture a one-time server snapshot of contact identity/details.
- Keep Individual jobs valid without a Contact, reject incompatible stale values, and make the selected Contact/snapshot read-only after Check In.
- Use the immutable job snapshot in internal Job Card and Repair Summary output; do not rewrite Customer/Contact masters or legacy job history.
- Provide permission-scoped native lookup, error states, keyboard/focus behavior, and company/individual/empty/denied responsive states.
- Treat product-wide AC-003, AC-004, AC-012, AC-013, and AC-014 entries above as regression boundaries; this spec does not reimplement evidence, portal, permissions, or installation foundations.

## Out of Scope

- A custom person/history DocType, free-text replacement for ERPNext Contact, company/customer master changes, automatic primary-contact inference, or multiple contacts on one job.
- Requiring a Contact merely to save a Draft, changing billing/portal scope, adding Contact data to the portal, or broadcasting one LPO Contact to every generated job.
- Messaging, OCR, bulk reassignment, retrospective guessing of legacy contacts, or changing ERPNext/Frappe core.

## Dependencies

None - the slice consumes the existing Customer, Contact, Repair Job, and Check In contracts. Its shared Check In boundary with SPEC-001 is a resource synchronization point, not a hard dependency.

## Ordering Rationale

- Core user value: 4 - identifies the actual company representative for each visit while preserving account identity.
- Architectural risk: 5 - introduces a job-specific immutable snapshot and conditional state rule at a shared Repair Job transition.
- Implementation effort: 4 - spans metadata, permissioned lookup, Check In validation, print context, native UI, and regression coverage.

## Affected Existing Functionality

Repair Job Customer/vehicle intake and Check In, Project creation, Job Card and Repair Summary print context, Customer LPO-generated Draft jobs, Customer/Contact permissions, Customer-primary-Contact fallback, and portal privacy can regress. Individual jobs, legacy jobs, ERPNext Customer/Contact masters, billing, stock, and accounting remain authoritative.

## Implementation Requirements

### Data

- [SPEC-002-AC-01, SPEC-002-AC-02, SPEC-002-AC-04, SPEC-002-AC-06, SPEC-002-AC-09] Requirement: add an optional Draft Contact Link and hidden/read-only one-time job snapshot containing Contact identity, available phone/mobile/email, canonical Customer, type, and capture time without changing legacy jobs; Evidence: metadata, snapshot, print, and migration tests show exact values and no inferred legacy person.

### Authorization

- [SPEC-002-AC-02, SPEC-002-AC-05, SPEC-002-AC-08] Requirement: enforce readable Customer/Contact and Repair Job permissions, Contact-to-Customer link scope, and post-Check-In immutability on the server; Evidence: permitted/denied tests prove safe rejection and no Contact enumeration.

### Business Logic

- [SPEC-002-AC-01, SPEC-002-AC-02, SPEC-002-AC-03, SPEC-002-AC-04, SPEC-002-AC-05, SPEC-002-AC-06] Requirement: allow Company Draft save without Contact, require a linked Contact at Check In, reject Contact on Individual jobs, capture once, and preserve optional evidence/workflow behavior; the shared Check In owner validates customer type, canonical customer, Contact link, vehicle reassociation, and active conflicts before atomically creating one Project path, the snapshot, and status; identical replay returns the existing state and stale/conflicting replay changes nothing; Evidence: controller tests show correct status, Project, snapshot, fallback, replay, and rollback outcomes.

### API

- [SPEC-002-AC-02, SPEC-002-AC-05, SPEC-002-AC-08] Requirement: expose `get_company_contacts(customer, query)` as a GET-only scoped lookup and retain `RepairJob.check_in(contact_person, confirm_customer_association, expected_version, idempotency_key)` as a typed POST-only action; validate all inputs and re-fetch state before snapshot/status/Project/vehicle mutation, return typed success or stable `COMPANY_CONTACT_REQUIRED`, `CONTACT_NOT_LINKED`, `STALE_REQUEST`, `PERMISSION_DENIED`, or `ACTIVE_CONFLICT` errors, and make an identical replay a no-op; Evidence: RPC contract tests prove methods, response shape, permission checks, replay, and atomic failure.

### State

- [SPEC-002-AC-01, SPEC-002-AC-02, SPEC-002-AC-03, SPEC-002-AC-04, SPEC-002-AC-05, SPEC-002-AC-06] Requirement: represent Company Draft incomplete, Company ready, checked-in immutable, Individual no-contact, stale, denied, and legacy fallback states; shared Check In validates sibling vehicle/customer/contact inputs before one transaction, with replay no-op and stale/conflict rollback; Evidence: state tests prove no false transitions, duplicate Project/snapshot/intervals, or snapshot rewrites.

### UI

- [SPEC-002-AC-01, SPEC-002-AC-02, SPEC-002-AC-05, SPEC-002-AC-06, SPEC-002-AC-07, SPEC-002-AC-08] Requirement: place the native Company Contact/Responsible Person Link after Customer and before vehicle/actions, expose clear conditional/readonly/error states and selected identity, preserve keyboard focus, WCAG 2.2 AA contrast/labels/status/error semantics, text reflow, touch targets, and reduced motion, and keep print/portal boundaries visible at 1310x683, 768x1024, and 390x844; Evidence: authenticated Desk and print scenarios show readable native behavior without page-level overflow.

### Automated Tests

- [SPEC-002-AC-01, SPEC-002-AC-02, SPEC-002-AC-03, SPEC-002-AC-04, SPEC-002-AC-09] Requirement: cover Draft save, Company Check In, Individual behavior, optional evidence, per-job identity, one Project/snapshot/interval transaction, replay no-op, legacy fallback, and install/reinstall; Evidence: DocType, controller, integration, and migration assertions prove exact state and unchanged masters.
- [SPEC-002-AC-05, SPEC-002-AC-06, SPEC-002-AC-08] Requirement: cover mismatched/unreadable Contacts, stale/post-check-in edits, snapshot immutability, permission denial, and scoped lookup; Evidence: API/permission/print tests prove rollback and no leakage.
- [SPEC-002-AC-07] Requirement: cover portal privacy for company jobs; Evidence: portal tests exclude contact phone/email and preserve Customer-scoped submitted data.

### User Verification

- [SPEC-002-AC-01, SPEC-002-AC-02, SPEC-002-AC-04, SPEC-002-AC-06] Runtime: authenticated Frappe/ERPNext v16 Desk; Setup: create Company X with Contacts A/B, one Draft job, and one Individual job; Action: save without Contact, select A, Check In, open a second job with B, and inspect Job Card/Repair Summary; Expected: normal success shows Draft optionality, per-job contact identity, immutable snapshots, and unchanged company master.
- [SPEC-002-AC-03, SPEC-002-AC-05, SPEC-002-AC-07, SPEC-002-AC-08] Runtime: authenticated Desk and portal at 1310x683, tablet width, and 390x844; Setup: no-contact, Individual-with-stale-contact, denied, stale, legacy, long-value, and portal states; Action: keyboard-navigate lookup, cancel/ retry Check In, refresh, and open `/my-repairs`; Expected: alternate/error/denied states explain the next action, hide unauthorized details, keep optional evidence non-blocking, and show no page-level overflow or portal contact leak.

## Security and Permission Requirements

- Permitted actor: Service Advisor, Workshop Manager, or Auto Service Admin with existing Repair Job, Customer, and Contact permissions.
- Forbidden actor: unauthorized staff, unrelated customer, guest, portal user, or caller attempting Contact enumeration or post-Check-In mutation.
- Unauthenticated behavior: no guest Contact lookup, Check In, snapshot read, or contact mutation is exposed.
- Data boundary: Contact details appear only in permitted internal Repair Job reads, reports, and prints; the portal remains submitted Customer-scoped and excludes contact details.
- Safe failure: reject missing/unlinked/unreadable Contact, invalid Customer type, stale job, or denied action before Project/status/snapshot mutation.

## Edge Cases

- A Company Draft without Contact saves, but Check In fails with `COMPANY_CONTACT_REQUIRED` until a linked Contact is selected.
- A Contact linked to multiple companies is valid only for the selected Customer; an Individual Customer cannot retain it.
- Company X may use Contact A on Job A and Contact B on Job B; editing A later does not rewrite Job A's snapshot.
- Missing phone, mobile, or email stays blank; no other Contact or Customer primary Contact value is borrowed.
- Legacy checked-in jobs remain readable with the existing fallback; LPO-created Draft jobs use the normal per-job Check In gate.

## Automated Tests

### Unit Tests

- [SPEC-002-AC-01, SPEC-002-AC-02, SPEC-002-AC-03, SPEC-002-AC-04] Setup: use Company/Individual, linked/unlinked, and blank-contact fixtures; Action: save, Check In, and change Customer type; Assertion: conditional requirement, link validation, per-job identity, and optional evidence behavior match the contract.
- [SPEC-002-AC-05, SPEC-002-AC-06, SPEC-002-AC-09] Setup: use stale, post-check-in, legacy, and migration fixtures; Action: attempt forbidden edits and repeat install/migrate; Assertion: errors are atomic, snapshots remain immutable, and no legacy contact is invented.

### Integration/API Tests

- [SPEC-002-AC-02, SPEC-002-AC-05, SPEC-002-AC-08] Setup: create permitted and denied users plus Contact links; Action: call GET lookup and POST Check In with valid, invalid, unreadable, stale, missing, replayed, and concurrently repeated values; Assertion: only linked readable Contacts are returned, one Project/snapshot/interval is created, identical replay is a no-op, and failed calls create no Project, snapshot, status, or vehicle change.
- [SPEC-002-AC-06, SPEC-002-AC-07] Setup: check in jobs for Contacts A/B and link a customer portal user; Action: edit Contact A and query Job Card, Summary, and portal output; Assertion: snapshots remain historical and portal output contains no internal contact details.

### UI Tests

- [SPEC-002-AC-01, SPEC-002-AC-02, SPEC-002-AC-03, SPEC-002-AC-05] Setup: use native Repair Job form; Action: save Draft, open Contact lookup, select/cancel, Check In, and switch Company/Individual; Assertion: field placement, conditional required state, focus, errors, and read-only state are correct.
- [SPEC-002-AC-06, SPEC-002-AC-07, SPEC-002-AC-08] Setup: use long values, no-contact, denied, narrow, print, and portal fixtures; Action: refresh, print, keyboard-scroll, and inspect `/my-repairs`; Assertion: text states, privacy, wrapping, and responsive behavior pass.

## UI Verification Scenarios

- [SPEC-002-AC-01, SPEC-002-AC-02, SPEC-002-AC-04, SPEC-002-AC-06] Runtime: authenticated Frappe Desk; Viewport/device: desktop 1310x683; State/data: Company Draft with Contacts A/B and Individual job; Interaction: save without Contact, select A, Check In, replay, open Job B with B, and refresh; Expected: normal success shows Customer → Contact → vehicle/action hierarchy, one Project and one per-job snapshot, read-only checked-in values, and no duplicate state after replay.
- [SPEC-002-AC-03, SPEC-002-AC-05, SPEC-002-AC-08] Runtime: authenticated Frappe Desk; Viewport/device: narrow 390x844 and tablet width; State/data: no-contact Company, Individual stale Contact, denied user, stale job, and long email; Interaction: use keyboard lookup, cancel, retry, and inspect errors; Expected: alternate/error/denied states have actionable text, visible focus, no leaked Contact data, and no page-level overflow.
- [SPEC-002-AC-06, SPEC-002-AC-07] Runtime: authenticated Desk and customer portal; Viewport/device: desktop and narrow; State/data: Job A with Contact A, Job B with Contact B, then edited live Contact A; Interaction: refresh jobs and render Job Card/Repair Summary plus `/my-repairs`; Expected: historical snapshots remain stable, internal contact details stay out of the portal, and legacy fallback remains readable.

## Acceptance Criteria

- [ ] SPEC-002-AC-01: Given a Company Customer and a new Repair Job, when the advisor saves a Draft without Contact, then the Draft saves and Check In remains visibly gated by the missing contact requirement.
- [ ] SPEC-002-AC-02: Given a Company Draft with a Contact linked to its Customer, when the advisor checks in, then the job enters Assessment, exactly one existing Project path is used, and one server snapshot is captured.
- [ ] SPEC-002-AC-03: Given a job with no optional inspection, diagnosis, authorization, QC, or road-test record, when the valid contact flow progresses it, then those absent records do not block or regress the job.
- [ ] SPEC-002-AC-04: Given Company X has two jobs, when the advisor uses Contact A on one and Contact B on the other, then each job retains its own contact and Company X's master remains unchanged.
- [ ] SPEC-002-AC-05: Given an unlinked Contact, Individual Customer, stale job, or denied user, when save or Check In is attempted, then the server rejects it before status, Project, snapshot, or downstream mutation.
- [ ] SPEC-002-AC-06: Given a checked-in job snapshot and later edits to the live Contact, when staff render the Job Card or Repair Summary, then the original job snapshot remains visible and legacy jobs retain their fallback.
- [ ] SPEC-002-AC-07: Given a Company job with a contact snapshot, when a linked customer opens `/my-repairs`, then only submitted Customer-scoped repair/finance data appears and Contact phone/email remain hidden.
- [ ] SPEC-002-AC-08: Given a user lacks Customer, Contact, or Repair Job scope, when lookup or job read is attempted, then access is denied without enumerating names, links, phone numbers, or email addresses.
- [ ] SPEC-002-AC-09: Given a fresh, repeated, or uninstall/reinstall cycle, when the feature metadata and legacy records are synchronized, then no core edit occurs, no unknown contact is invented, and existing job/customer values remain unchanged.

## Definition of Done

- [ ] All acceptance criteria are implemented later inside the app using native ERPNext Contact identity and no core edits.
- [ ] Automated unit, API, permission, print, portal, migration, and regression tests provide evidence for every criterion.
- [ ] User/UI verification covers Company/Individual, Draft, loading, empty, denied, stale, long-content, keyboard, narrow, and print states.
- [ ] Security and permission checks prove Contact links and snapshots cannot leak or be changed outside permitted job scope.
- [ ] Repair Job, Project, LPO, Customer Vehicle, portal, Job Card, Summary, and optional-evidence regressions are recorded.
- [ ] Documentation, PROGRESS.md, coherence evidence, and the downstream execution map reconcile before separate implementation authorization.
