# DESIGN.md

## 1. Design Summary

Selected direction: **Native Workshop Control**.

Native Frappe/ERPNext operational language
+ restrained industrial clarity
+ workflow-first Desk forms, queues, tables, and dashboards
+ no decorative cultural lens unless supplied by governed brand assets
+ a persistent vehicle/work-order trace from intake to release.

The product should feel like a dependable service-control instrument: the next action, current state, accountable record, and release risk are obvious. Recognizable signatures are the Car Workshop launcher, eight role-filtered operational hubs, compact native forms, vehicle/job identity near the top, and traceable connections rather than decorative cards or custom shells.

## 2. Product and Audience Context

Service Advisors and managers need fast, high-density Desk work; technicians and parts staff need focused queues; cashiers and gate officers need unambiguous financial/release states; customers need a calm read-only repair view. Use is frequent, authenticated, and task-driven on desktop and tablet-sized screens, with narrow viewport support for native Desk behavior. The product contains sensitive customer, vehicle, financial, and identity data, so trust comes from explicit labels, visible state, restrained decoration, and audit traces.

The existing approved direction is native Frappe: active theme, typography, spacing, status colors, Lucide icons, native tabs, dialogs, tables, dashboards, breadcrumbs, and permission filtering. Do not introduce a competing palette, custom Vue shell, duplicate navigation, or decorative imagery that competes with vehicle/job identity. High-risk actions—workflow transition, override approval, billing, credit release, Gate Pass issue/use, cancellation—must expose consequence and require clear confirmation where applicable.

## 3. Design Success Criteria

- A staff member can identify the vehicle, customer, Repair Job, current state, and next valid action without hunting across unrelated fields.
- Frequent work remains compact and keyboard reachable while long descriptions, identifiers, tables, and financial values remain legible.
- Primary actions outrank secondary links; permission-hidden actions do not leave misleading empty controls.
- Native Frappe patterns remain recognizable across workspaces, forms, dialogs, reports, prints, and the customer portal.
- Empty, loading, error, disabled, denied, and success states explain what happened and what can happen next.
- No relevant desktop/tablet/mobile state clips, introduces page-level horizontal overflow, or hides release-critical information.
- Important meaning is available through text, labels, structure, and state—not color alone.
- Future changes remain feasible within native Frappe assets and theme tokens without global CSS drift.

## 4. Design Tensions

| Tension | Position | Observable consequence |
|---|---|---|
| Restrained vs expressive | Restrained | Theme-led surfaces, short labels, no ornamental gradients or hero imagery in operational screens. |
| Dense vs spacious | Dense but breathable | Compact native grids for work; consistent section gaps prevent field/table collapse. |
| Familiar vs novel | Familiar | Native Desk controls and routes win over bespoke widgets; signature comes from information grouping and traceability. |
| Functional vs immersive | Functional | Motion and imagery are used only for orientation, evidence, or feedback. |
| Formal vs approachable | Formal with plain language | Clear labels such as `Remaining Amount` and `Return to Repair`; calm actionable errors. |
| Systematic vs organic | Systematic | One spacing, state, icon, and navigation grammar across every hub. |
| Calm vs energetic | Calm | Status urgency is explicit in text/indicators; no flashing, noisy animation, or competing accents. |

## 5. Research Summary

The material design decisions are grounded in the existing approved repository contracts: `docs/design/car-workshop-navigation.md`, `docs/design/repair-job-form-layout.md`, `docs/design/repair-job-sales-order.md`, `docs/design/customer-lpo.md`, and `docs/design/repair-job-service-templates-and-history.md`. They consistently require native Frappe/ERPNext surfaces, active theme inheritance, compact grouped navigation, readable tables, and direct authenticated runtime inspection.

Accessibility baseline: [WCAG 2.2](https://www.w3.org/TR/WCAG22/). Contract consequence: keyboard access, visible focus, non-color state cues, readable reflow, labeling, and error identification are acceptance conditions, not polish.

## 6. Candidate Directions

### Candidate A — Native Workshop Control

Formal logic: ERP/operations control; aesthetic: restrained theme-led industrial UI; structure: native launcher, sidebar hubs, tabbed forms, dense queues; signature: vehicle/job identity and trace connections. Best product/audience fit, strongest feasibility and longevity, lowest visual novelty risk, and directly aligned with existing contracts.

### Candidate B — Service Bay Command Board

Formal logic: kanban/dispatch board; aesthetic: bold status lanes and larger tiles; structure: board-first workshop dashboard with side panels; signature: bay occupancy and job movement. Strong for dispatch but risks duplicating native list/workflow behavior, overemphasizing status color, and requiring a new responsive interaction model.

### Candidate C — Customer Journey Atelier

Formal logic: guided journey/progress narrative; aesthetic: spacious editorial cards and vehicle imagery; structure: stepper-led record experience; signature: visual journey from check-in to handover. Approachable for customers but unsuitable for high-density staff billing, permissions, parts tables, and native ERPNext work; conflicts with the approved read-only portal boundary.

Comparison: A wins on product fit, accessibility, feasibility, maintainability, and longevity. B is deferred because it adds a second operational model. C is rejected because it prioritizes presentation over the staff control surface and would encourage a custom shell.

## 7. Selected Design Direction

**Native Workshop Control** is selected because the product is a high-frequency operational system embedded in Frappe/ERPNext, not a marketing site or standalone customer app. It preserves native permission, table, form, print, and route behavior while making the workshop information architecture more legible.

- B was rejected for introducing duplicate board semantics and excessive status visualization.
- C was rejected for weak fit with dense staff workflows and the approved portal limitation.

## 8. Design Principles

1. **Put identity before action** → staff must know which vehicle/job they are changing → show customer, registration, job number, and current status before primary actions → reject screens where action buttons precede record identity.
2. **Make release risk explicit** → billing and Gate Pass errors have operational and financial consequences → show coverage, payment/credit state, exact unmet condition, and next remedy in text → reject color-only badges or vague “not ready” messages.
3. **Use native grammar, improve grouping** → users already rely on Frappe/ERPNext conventions → use native forms, tabs, tables, dialogs, breadcrumbs, dashboards, and indicators grouped by workflow → reject custom shells or duplicate paths.
4. **Evidence is optional until the rule says otherwise** → inspection/diagnosis/authorization/QC support auditability but should not create surprise blockers → show optional evidence as an available, clearly labeled section/state → reject empty states that imply a valid job is broken.
5. **Quiet surfaces, loud decisions** → frequent data entry needs low visual noise while exceptions need attention → reserve strong emphasis for primary actions, errors, warnings, and release gates → reject equal-weight cards, decorative shadows, and competing accents.

## 9. Semantic Design Tokens

Use the active Frappe/ERPNext theme as the foundation. The app must define semantic roles only where a component needs a stable meaning; it must not hard-code a new global palette.

### Color

| Foundation/theme source | Semantic token | Use |
|---|---|---|
| Frappe canvas/background | `--dms-canvas` | Page and workspace background. |
| Frappe surface/card | `--dms-surface` | Forms, tables, dialogs, and native panels. |
| Frappe primary text | `--dms-fg` | Body, headings, identifiers. |
| Frappe muted text | `--dms-fg-muted` | Metadata, help, timestamps. |
| Frappe border/divider | `--dms-border` | Field/table/group separation. |
| Frappe primary action | `--dms-action-primary` | One main action per context. |
| Frappe secondary action | `--dms-action-secondary` | Safe supporting actions. |
| Frappe info/success/warning/danger | `--dms-state-info/success/warning/danger` | State indicators and messages. |
| Frappe focus ring | `--dms-focus` | Keyboard focus, always visible. |

Status meaning must also use text, icon/shape, labels, or structure. If a print or portal surface cannot access theme variables, use the active Frappe/ERPNext rendered values rather than inventing replacements.

### Typography

Use the active Frappe/ERPNext UI font stack and fallbacks; do not add a new font family. Use native Frappe heading/body/control sizes, with these semantic roles: page title, section title, field label, body value, metadata/help, table numeric value, and alert/action text. Numeric amounts, quantities, dates, and identifiers align consistently and retain their native locale formatting. Long readable prose should remain within approximately 70–85 characters per line where composition allows.

### Spacing

Use the native Frappe spacing scale. Apply the smallest scale step inside controls, one step between label/value groups, two steps between fields, three steps between sections, and four or more steps between major page regions. Do not introduce one-off margins to repair a broken hierarchy.

### Shape

Use native Frappe field, table, dialog, button, and indicator geometry. Prefer modest radii and standard borders. Vehicle/job identity may receive grouping, not oversized rounded containers.

### Surface and Elevation

Prefer flat theme surfaces with border separation. Use native dialog elevation and overlays only for modal context. Shadows do not encode status or ownership; no glass/transparency or decorative layered cards.

### Motion

Use native Frappe transitions and frozen-call/loading feedback. Motion may explain navigation, loading, confirmation, or state continuity; keep it short and non-blocking. Respect `prefers-reduced-motion` by removing nonessential movement and never use flashing or auto-advancing motion.

## 10. Layout and Composition

The application shell is native Frappe: app launcher → workspace sidebar → page/form content. Workspaces use a compact four-column launcher and short grouped sidebar. Forms use native two-column density and the approved Repair Job tabs: Details, Services, Workshop, Billing, Connections.

Reading order is identity/context → current state and primary action → task data → supporting evidence → connections/history. Overview prioritizes operational KPIs and shortcuts; queues prioritize status, age, vehicle/job identity, owner, and next action; financial surfaces prioritize amount, coverage, authority, and exception. Whitespace separates tasks, not every field.

## 11. Navigation and Application Shell

Use only native Frappe navigation: Car Workshop app launcher, eight role-filtered hubs, workspace sidebars, breadcrumbs, list routes, document connections, tabs, and contextual action menus. `Workshop Management` remains `/desk/workshop-management`. Permission filtering changes visibility but never grants access. On tablet/narrow screens use native sidebar collapse, tab overflow/stacking, and content stacking; do not add horizontal navigation or a second mobile shell.

## 12. Component System

- **Buttons/actions:** native primary, secondary, subtle, and destructive intents; one primary action per context; labels name the outcome (`Check In`, `Continue to Billing`, `Issue Gate Pass`).
- **Fields/Link controls:** native labels, required markers, help, link pickers, read-only states, and keyboard behavior.
- **Forms/tabs:** native Tab Breaks and section/column breaks; keep related fields in their task tab.
- **Tables:** native Frappe grids with readable headers, wrapping/truncation rules, row status, and safe horizontal scrolling inside the table only.
- **Dialogs:** native mapping/selection dialogs; explicit checkbox labels, selected counts, totals, and review-before-save behavior.
- **Indicators/alerts/toasts:** native semantic indicators plus text; warnings identify cause and remedy.
- **Dashboards/reports:** native cards/charts/tables with a clear primary KPI and actionable detail; no equal-weight metric wall.
- **Print/portal:** use governed Jinja print language and the portal's simple read-only table/list patterns.

## 13. Interaction and Semantic States

Every interactive feature must define default, hover, focus, pressed/active, selected, disabled, loading, empty, error, success, and permission-denied behavior where applicable. Loading uses native frozen-call treatment and preserves record identity. Errors are inline/actionable and identify the exact row/field/gate. Disabled actions explain the prerequisite when safe to expose. High-risk actions require explicit labels and confirmation; no icon-only destructive control.

Operational states include Draft, Assessment, Awaiting Approval, In Repair, Quality Check, Billing, Ready for Release, Closed, Cancelled, available, draft, submitted, cancelled, invoiced, and not billable. State is expressed with text and native indicator treatment.

## 14. Forms and Data Entry

Labels sit with controls; required/optional status is native and visible. Use help text for tax basis, fitment, payment/credit, and workflow consequences. Validate at the earliest useful point without interrupting valid typing; place errors next to the field/row and summarize the correction. Keep child-table editing keyboard reachable. On narrow screens, fields stack in reading order and long values wrap; input controls retain usable touch targets and native focus.

## 15. Tables, Dense Data, and Dashboards

Use compact-but-readable density. Align identifiers/text left, quantities/dates centrally where native conventions allow, and money/numbers by decimal significance. Support native search/filter/sort/pagination where the list requires it; keep key identity columns discoverable. Long registration, LPO, job, and description values wrap or truncate safely with full value available in the record. Overview hierarchy: primary operational state → supporting KPIs/trend → actionable queue/detail. Empty tables explain the next valid action.

## 16. Data Visualization

Existing dashboards are operational only: Repair Job status, intake trend, closed-repair revenue, Gate Pass status, Quality Check status, open jobs, pending authorizations/QC, issued passes, and active campaigns. Use the native Frappe chart renderer and semantic state colors; labels and tables must provide an accessible alternative. Do not add charts for technical DocType coverage or decorative utilization. Any future chart work must follow the project Flint chart workflow.

## 17. Imagery, Illustration, and Icons

Imagery is justified for evidence and print context, not decoration. Walkaround/Job Card may use the approved static vehicle silhouette/diagram with numbered damage references and photos. Use the governed company/logo resolution for prints; never use workspace/car icons as a logo fallback. Use native Lucide line icons and approved Car Workshop icon assets, aligned optically with labels. Icons clarify actions and never replace critical text.

## 18. Responsive Rules

- **Mobile/narrow:** native sidebar collapse; tabs overflow/stack; two-column fields stack; tables scroll within their container; identity, status, attachment, remaining authority, and primary action remain discoverable; no page-level horizontal overflow.
- **Tablet:** preserve two-column forms where readable; allow table wrapping/scrolling; keep dialogs' primary action visible.
- **Desktop:** use native workspace/form width and compact grids; keep primary action and identity above the fold where practical.
- **Wide desktop:** increase breathing room before increasing card count or font size; never stretch text measures unnecessarily.

## 19. Accessibility Contract

Target WCAG 2.2 AA for web surfaces. Preserve semantic headings, native labels, keyboard order, visible focus, accessible tab labels, and screen-reader-readable errors/status. Meet 4.5:1 normal-text and 3:1 large-text contrast through the active theme; do not rely on color alone. Support text zoom/reflow, native touch targets, reduced motion, descriptive links, alt text for meaningful vehicle/print imagery, and clear localization-safe labels. Every CSV error identifies row/column/correction; every ceiling failure states authorized/proposed/excess/amendment. Portal and print outputs remain understandable without internal-only fields.

## 20. Key Screen Guidance

### Car Workshop launcher and hubs

Purpose: route each role to the next operational workspace. Primary action: choose a permitted hub. Hierarchy: app identity → eight concise cards → role-filtered sidebar. States: hidden/permission-filtered, active, empty, narrow. Rule: no duplicate business action or custom shell.

### Repair Job form

Purpose: operate one vehicle visit. Primary action changes by state: Check In, Start Work, Continue to Billing, issue/use Gate Pass. Hierarchy: identity/status → Details → Services → Workshop evidence → Billing → Connections. Empty optional evidence is valid. Connections are navigation/visibility, not a replacement for actions.

### Customer LPO

Purpose: control commercial batch intake. Primary action is the next valid import/resolve/create/reconcile action. Hierarchy: customer/LPO identity and attachment → vehicle rows → authorization/reconciliation → connections. Show row-level errors, remaining authority, and ceiling consequences in text.

### Component mapping dialog

Purpose: choose billable/stock components explicitly. Primary action: create a reviewable draft. Show service, type, description, quantity, amount, current state, selected count, and totals. Loading/empty/error/permission states must be actionable.

### My Repairs portal

Purpose: let a linked customer follow submitted work. Primary action: open a repair detail. Use plain status, dates, vehicle/job identity, service/invoice/payment summaries, and pagination. Do not expose internal notes, drafts, costs, margins, accounts, or technician identities.

### Prints and reports

Purpose: carry a traceable record outside the Desk. Prioritize company/customer/job/vehicle identity, source traces, line items, totals, status, terms, signatures, and audit-relevant notes. A4 outputs must be legible in HTML and PDF with no invented branding or fallback data.

## 21. Anti-Patterns

- Custom Vue/app shell, duplicate navigation, or custom global CSS replacing native Frappe behavior.
- Equal-weight card walls, decorative gradients, excess shadows, giant rounded containers, or imagery unrelated to evidence.
- Tiny controls, icon-only critical actions, hidden release gates, or status communicated only by color.
- Optional evidence rendered as a false blocker or empty state described as an error.
- Desktop layout merely shrunk onto mobile, page-level horizontal overflow, clipped dialogs, or truncated money/identifiers.
- Invented testimonials, prices, metrics, certification, outcomes, customer data, or branding claims.
- Technical counters on staff Overview, duplicate component rows, or silent server state changes.

## 22. Visual Testing and Inspection

Future visual work must follow: implement → render the real authenticated Frappe runtime → use realistic and long data → interact with the workflow → inspect directly → compare with this contract → log defect → fix → retest.

Inspect normal, loading, empty, error, permission-denied, long-content, realistic-table, mobile/narrow, tablet, desktop, hover/focus/pressed, and print/PDF states. Interactive evidence must include the actual primary controls, transitions, dialogs, tabs, and gates; screenshots or static code review alone are insufficient. Record runtime, viewport, state/interaction, observed result, defect, fix, and retest.

## 23. Design Acceptance Criteria

- **DA-001 Navigation:** Permitted users see the eight native hubs, and `Workshop Management` remains the overview route without duplicate sidebar links.
- **DA-002 Identity hierarchy:** Repair Job and LPO screens show customer/vehicle/job/LPO identity and current state before primary actions.
- **DA-003 Native grammar:** Forms, tabs, tables, dialogs, dashboards, and indicators use native Frappe patterns and active theme tokens.
- **DA-004 State clarity:** Loading, empty, error, success, disabled, denied, and release-blocked states explain cause and next action in text.
- **DA-005 Dense data:** Long identifiers/descriptions and realistic component tables remain readable with no page-level horizontal overflow.
- **DA-006 Accessibility:** Keyboard focus/order, labels, contrast, reflow, touch targets, reduced motion, and non-color cues pass WCAG 2.2 AA review.
- **DA-007 Optional evidence:** Valid jobs with empty optional evidence sections remain visibly valid and operable.
- **DA-008 Commercial control:** Mapping dialogs expose explicit selected components, totals, review-before-save, and actionable ceiling/duplicate errors.
- **DA-009 Portal privacy:** My Repairs exposes only linked submitted customer data and has no mutation controls.
- **DA-010 Print fidelity:** Job, inspection, authorization, estimate/proforma, gate-pass, repair-summary, and LPO outputs retain identity, traces, totals, terms, and signatures without clipping.
- **DA-011 Signature:** Direct rendered inspection shows the Native Workshop Control signature: role-filtered hubs, compact task tabs, vehicle/job identity, and trace connections.

## 24. Assumptions and Constraints

- Existing approved design notes are the governing visual evidence and are preserved as detailed feature contracts.
- Native Frappe theme values vary by installation; semantic tokens alias the active theme rather than inventing a new palette.
- Visual implementation requires explicit design-direction approval unless Aslam delegates that approval; this document alone is not approval.
- No visual PASS is implied by this documentation-only change; runtime rendering and interaction remain implementation gates.

## 25. Decision Record

| Decision | Status | Rationale/source |
|---|---|---|
| Native Workshop Control | Selected | Product is a high-frequency Frappe/ERPNext staff system; existing navigation/form/LPO contracts require native surfaces. |
| Active Frappe theme and typography | Accepted | Existing approved design notes prohibit a parallel palette and global CSS. |
| Eight role-filtered operational hubs | Accepted | `docs/design/car-workshop-navigation.md`; improves findability without granting permission. |
| Five-tab Repair Job form | Accepted | `docs/design/repair-job-form-layout.md`; preserves field names and workflow semantics. |
| Explicit component mapping and reviewable drafts | Accepted | `docs/design/repair-job-sales-order.md`; protects traceability and ERPNext review. |
| Native four-tab Customer LPO | Accepted | `docs/design/customer-lpo.md`; keeps commercial control above independent Repair Jobs. |
| Read-only customer portal | Accepted | Product scope and existing `/my-repairs` implementation; no customer mutation surface. |

DESIGN CONTRACT: COMPLETE
Product coverage: PASS
Accessibility contract: PASS
Responsive contract: PASS
Visual verification rules: PASS

STATUS: READY FOR TRACER-BULLET SPECIFICATION
