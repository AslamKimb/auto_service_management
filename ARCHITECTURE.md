# ARCHITECTURE.md

This contract documents the existing approved and implemented architecture of `auto_service_management`. It is not permission to alter application code, infrastructure, production data, or deployment state.

## 1. Architecture Summary

Auto Service Management is a Frappe/ERPNext v16 modular monolith. The app owns automobile-workshop domain records, state transitions, permission-scoped reads, audit evidence, portal filtering, and focused ERPNext adapters. Frappe/ERPNext owns identity, document persistence, accounting, taxes, pricing, stock, payments, credit limits, and native Desk/website primitives.

The system runs as a Docker Compose bench with Nginx, Frappe backend, Socket.IO, MariaDB, Redis cache/queue/socket services, scheduler, workers, ERPNext, HRMS, and Uganda Compliance. The architecture favors one cohesive transaction boundary, explicit POST-only mutations, native document mapping, server-side permission gates, and deployable local/image environments over custom services or speculative distribution.

## 2. Product Constraints Driving Architecture

| Product requirement | Architectural consequence | Supporting capability |
|---|---|---|
| One vehicle visit must be traceable end to end | Repair Job is the app-owned aggregate root for one Customer Vehicle and one ERPNext Project | Repair Job controller, Project adapter, trace fields, Service History |
| ERPNext remains financial/stock authority | Do not duplicate prices, taxes, ledger, payment, stock, or credit rules | ERPNext native DocTypes plus focused adapters/sync hooks |
| Optional evidence cannot surprise-block work | Evidence DocTypes are linked records, not hidden transition gates | Workflow validation and optional evidence tests |
| Staff need role-scoped operational work | Native Desk workspaces plus DocType/row permissions | Fixtures, permission hooks, scoped reporting and queries |
| Customers need read-only visibility | Website route and portal service filter to linked submitted data | `/my-repairs`, `portal.py`, website route rules |
| Fleet LPOs create independent vehicle jobs | Customer LPO/Fleet Service Campaign orchestration preserves one job per vehicle | Typed customer-LPO workflow methods and batching tests |
| High-risk mutations need server authority | Whitelisted methods declare GET/POST, check permissions, validate state, and avoid controller commits | integration modules, controllers, test contracts |
| Deployment must be repeatable and gated | Docker Compose dev/image stacks, explicit migrations/assets, immutable image tag rule | deployment files and project AGENTS.md |

## 3. System Context

Human actors are the seven workshop roles plus linked customer portal users. The application boundary contains Frappe Desk/website routes, app-owned DocTypes, controllers, integration adapters, hooks, reports, print formats, fixtures, tests, and static assets.

External or platform systems are Frappe, ERPNext, HRMS, Uganda Compliance, MariaDB, Redis, Nginx, Socket.IO, Docker Compose, and optional configured ERPNext company/payment/tax/warehouse data. The browser crosses a trust boundary at authenticated Desk/website requests; server methods, DocType permissions, row filters, and ERPNext validation remain authoritative. Customer portal users cross a narrower boundary and receive only linked submitted data.

Primary flow: browser → Nginx → Frappe backend → app controller/DocType → MariaDB/ERPNext; asynchronous work uses Redis queue/workers; realtime updates use Socket.IO/Redis socket. ERPNext document events call app synchronization adapters and preserve trace fields.

## 4. Architecture Pattern

**Accepted pattern:** platform-integrated modular monolith with synchronous document transactions and bounded background work.

App modules are separated by cohesion (domain, integration, reporting, printing, portal, workspace/setup) but run in the same bench/site and database transaction model. Frappe supplies routing, ORM/document lifecycle, permissions, queues, scheduler, website rendering, and Desk.

This pattern is rejected only if a future approved product requirement proves a separately deployable boundary necessary. Microservices, event sourcing, offline-first, or a separate frontend are not current architecture.

## 5. System and Module Boundaries

- **Workshop domain:** app-owned DocTypes, controllers, workflow compatibility, transition rules, fitment, service calculations, override/audit/history.
- **ERPNext integration:** `integration/erpnext` adapters, component mapping, document sync, quotation/sales-order mapping, and Customer LPO orchestration. It may call ERPNext APIs but does not own ERPNext financial semantics.
- **Desk/workspace:** native Workspace fixtures, desktop setup, dashboard cards, DocType JS, and form layout. It may improve navigation and presentation but never grant permission.
- **Reporting:** report definitions and permission-safe runner/control definitions. Reports resolve scope through the business parent where child records are not independently permissioned.
- **Printing:** Jinja context/branding and app-owned print formats/includes. ERPNext/company data remains source for branding, amounts, taxes, and terms.
- **Portal:** website route/controller/template and portal read services. It is read-only and may expose only submitted, customer-linked records.
- **Setup/migrations:** filtered fixtures, patches, lifecycle hooks, indexes, role/permission reconciliation, and cache/workspace setup.

Allowed dependency direction: UI/portal/report/print → app domain services → integration adapters → Frappe/ERPNext. Domain logic must not reach into browser state; platform core must not be modified.

## 6. Technology Stack

| Technology | Responsibility | Evidence/compatibility |
|---|---|---|
| Frappe `version-16` | Framework, bench, ORM, DocTypes, Desk, website, permissions, jobs | Approved spec/README baseline. |
| ERPNext `version-16` | Customer, Project, Task, Timesheet, Item, sales, stock, payments, accounting | Required app and integration contract. |
| Python 3.14 | App runtime and tests | `auto_service_management/pyproject.toml`. |
| MariaDB 11.8 | Site database | README platform baseline and Compose stack. |
| Node.js 24 | Asset/realtime runtime | README platform baseline; image WebSocket path is explicit in project instructions. |
| Redis | Cache, queue, Socket.IO pub/sub | Compose services and Frappe runtime. |
| Nginx | Reverse proxy/static asset and websocket entry | `nginx.conf` and deployment resources. |
| Docker Compose | Reproducible dev/image environments | `docker-compose.dev.yml` and image/deployment files. |
| Ruff/Flit | Python packaging/lint/format and app build metadata | `pyproject.toml`. |

Rejected: a custom frontend framework, separate service fleet, custom auth, custom accounting/stock engine, and dependency-heavy component system because native Frappe/ERPNext already supplies the cohesive capabilities.

## 7. Frontend Architecture

The primary frontend is native Frappe Desk: Workspaces, lists, forms, Link fields, child grids, dialogs, dashboards, reports, and document connections. Small app-owned JavaScript modules extend Sales Invoice, Customer LPO, Material Request, and Repair Job billing interactions; they call typed server methods and preserve native save/submit flows. Static CSS/assets are app-scoped and must not replace the native design system.

The secondary frontend is Frappe website/Jinja for read-only `My Repairs`. Server-rendered portal data is permission/customer scoped. Client/server state is document state plus server-returned summaries; financial and transition truth is never client-owned. Design behavior follows `DESIGN.md` and requires direct authenticated visual/interaction inspection.

## 8. Backend Architecture

Python DocType controllers enforce validation, naming, state transitions, derived values, and lifecycle behavior. Pure domain services handle money, margin, transition, fitment, and release-policy rules where they can be tested independently. Integration adapters isolate ERPNext API/document mapping. Hooks synchronize submitted/cancelled/trash effects for Sales Order, Sales Invoice, Payment Entry, Material Request, and Timesheet.

Background workers handle explicitly asynchronous fleet creation/progress where configured; idempotency and permission-scoped status reads are required. Synchronous paths retain server validation before mutation. Controllers do not call `frappe.db.commit()`.

## 9. Database and Data Architecture

MariaDB is the authoritative site database through Frappe's document/ORM layer. App-owned DocTypes store workshop state and traces; ERPNext DocTypes store financial/stock/accounting authority. Query Builder is preferred over raw SQL. Transactions follow Frappe request/document lifecycle; app methods avoid partial multi-document success through validation and idempotency controls.

Patches reconcile released data models and indexes; fixtures are filtered to app-owned roles/fields/permissions. Identifier uniqueness, linked ownership, component references, and permission-safe lookup indexes are explicit invariants. Backups, restore rehearsals, isolated test sites, and migration/reinstall checks are release gates; retention/privacy follow site and ERPNext governance rather than a second storage system.

## 10. Authentication and Authorization

Frappe manages users, sessions, roles, website users, and portal Customer linkage. App roles are fixtures: Service Advisor, Workshop Technician, Parts Interpreter, Workshop Manager, Cashier, Security Gate Officer, and Auto Service Admin. DocType permissions and row-level filters control access; workspace/sidebar visibility is not security.

Protected methods call document permission checks and server-side role/business-policy checks. Sensitive actions include transitions, overrides, credit release, invoice/order/material creation, Gate Pass issue/use, and LPO batching. Portal access requires an authenticated website user linked under ERPNext Customer Portal Users and returns submitted customer-scoped finance data only.

## 11. API and Communication

Internal app actions are Frappe RPC methods with typed inputs/outputs. Reads and previews use GET; user-triggered mutations use POST-only methods, server-side permission checks, validation, and actionable errors. ERPNext native mapping remains available and app overrides wrap it only where traceability/business rules require.

Methods are idempotent where repeated user action or worker retry is expected: Project/Service History creation, fleet campaign/job creation, trace synchronization, and request ownership checks. Errors identify missing permission, invalid transition, component conflict, ceiling excess, or release condition without leaking hidden records. No public guest mutation API is supported.

## 12. Storage

Document data and audit metadata live in MariaDB through Frappe. Uploaded inspection photos, signatures, LPO attachments, and print assets use Frappe's configured File storage and permission model; metadata remains linked to the owning document. No separate object-storage service is required by current product scope. Portal/print access must preserve record permissions and configured retention; tests use synthetic fixtures only.

## 13. Background Jobs, Events, and Realtime

Redis queues and Frappe workers support bounded asynchronous fleet creation/progress and normal scheduled bench work. Job triggers are explicit POST actions; status is polled through permission-scoped GET when a long operation is used. Retries must be safe through idempotency and row ownership checks; failures expose an actionable status and recoverable error rather than silently duplicating jobs.

Frappe document hooks synchronize downstream summaries on submit/cancel/trash. Socket.IO is platform realtime for Desk; it is not a second source of business state. Cache use is limited to documented settings/desktop lookups with clear invalidation through lifecycle hooks and clear-cache operations.

## 14. External Services and Integrations

The required integration surface is ERPNext within the same bench/site: Customer, Project, Task, Timesheet, Item/price lists, Quotation compatibility, Sales Order, Sales Invoice, Payment Entry, Material Request, Stock Entry, warehouses, taxes, payment terms, credit limits, and accounting. HRMS and Uganda Compliance are suite-installed dependencies; EFRIS is dormant until separately configured.

Integration adapters preserve source traces and let native ERPNext controllers calculate prices/taxes/ledger/stock. Failures are surfaced before or during document validation; native downstream workflows remain available for non-Material-Issue requests and standard Sales Order → Sales Invoice mapping.

## 15. Security

Security controls are Frappe sessions/roles/permissions, server-side document checks, row-scoped queries, input/link validation, POST-only mutations, safe Jinja escaping, permission-aware reports/portal, filtered fixtures, and no secrets/customer production data in tests. Sensitive values are not copied to client-only authority. Use configured platform encryption/TLS/secrets management; do not add custom cryptography.

Audit Repair Job Log, Override, LPO amendment, component trace, and source-document linkage where the product requires accountability. Dependency/lint/test gates and backup/restore rehearsal support release safety. Incident response follows the deployment owner and site backup/restore runbook.

## 16. Testing Strategy

| Test layer | Proves |
|---|---|
| Pure unit tests | Money, margins, fitment, transition, release, identifier, and policy invariants. |
| DocType/controller tests | Validation, naming, lifecycle, optional evidence, permissions, and idempotency. |
| ERPNext integration contracts | Project/Task/Timesheet, price, Sales Order/Invoice, payment, Material Request/Stock Entry behavior. |
| Permission/report/portal tests | Row scopes, hidden totals/records, customer linkage, submitted-only portal data. |
| Migration/fixture tests | Fresh install, repeat migrate, uninstall/reinstall, filtered fixtures, patches/indexes. |
| Browser/interactive tests | Authenticated Desk forms, dialogs, workspace routing, primary workflows, and portal navigation. |
| Visual/print tests | Real runtime states, responsive behavior, HTML/PDF print output, and `DESIGN.md` acceptance. |
| Deployment tests | Compose setup, health, asset build, websocket path, image parity after approval. |

The proving path is the approved acceptance scenario: customer/vehicle → Repair Job/Project → optional evidence → services/fitment/tasks/timesheets → material/stock → invoices/payments/credit → Gate Pass → Service History, plus diagnosis-only, rework, cancellation, and fleet/LPO branches.

## 17. Observability

Use Frappe/application logs, worker/scheduler logs, document audit records, permission-safe operation status, health/ping checks, and Compose service status. Record job IDs/source documents for asynchronous fleet work and trace fields for ERPNext documents. Monitor failed migrations, queues, websocket/backend health, invoice/payment synchronization, and duplicate/ceiling/release conflicts.

Operational responders need the exact document, method, role, gate, and failure reason; logs must not expose secrets or hidden customer/financial data. Add tracing/metrics systems only when an approved scale/operations requirement justifies them.

## 18. Development Tooling

Use Git, Docker Compose, Frappe bench inside the backend container, Python/Flit/Ruff, Node asset tooling, and Graphify for repository navigation/refresh. Explicit site commands are required: `auto-service.localhost` for development and `auto-service-test.localhost` for automated tests. Build assets after Python/JS changes and hard-refresh authenticated Desk for runtime checks.

Required project checks include targeted tests, full app tests, migration/reinstall/fixture checks, `pre-commit`, `git diff --check`, and Graphify refresh after major changes. Generated `graphify-out` artifacts are preserved and checked for hook side effects.

## 19. Deployment and Environments

- **Local development:** `docker-compose.dev.yml`, editable app, Nginx on 8080 by default, dev/test sites, developer mode.
- **Isolated image verification:** separate `docker-compose.image.yml`, independent `dms-image_*` volumes, port 18080 by default, only after non-image verification and explicit user approval to build.
- **Production/Dokploy:** immutable image tag `dev-<short-git-sha>`, explicit variables, backup/restore and staging/UAT approval gates; no production migration by default.

Configuration holds site/company/price/tax/warehouse/terms/credit values. Migrations and asset builds run through named site commands. Rollback is a new verified immutable image/source commit or restored backup, never an in-place overwrite of a tag.

## 20. CI/CD

Changes must pass static/lint/format checks, targeted and full app tests, migration/fixture checks, and relevant browser/visual/print evidence before release consideration. Image builds require committed source, a new commit-derived tag, non-image dev verification, explicit approval, local image-stack parity verification, and recorded tag/evidence. Protected production operations additionally require backup/restore rehearsal, staging UAT, and explicit rollout approval. Rollback triggers include failed migration, failed health/asset/websocket checks, broken critical workflow, permission leak, or financial/stock mismatch.

## 21. Architecture Decision Log

### AD-001 — Frappe/ERPNext modular monolith

- Status: Accepted
- Approved or delegated by: approved `docs/specs/automobile-repair-management.md` baseline and current repository architecture; documented under Aslam's request.
- Reason: native platform already supplies the cohesive document, permission, workflow, accounting, stock, website, and operations capabilities.
- Verified evidence: `required_apps = ["erpnext"]`, current app hooks, Compose stack, and Graphify module/adapter communities.
- Alternatives considered: custom frontend/backend services; rejected for added moving parts and duplicated authority.
- Trade-offs accepted: platform coupling and shared site transaction boundary.

### AD-002 — Repair Job aggregate and ERPNext authority

- Status: Accepted
- Approved or delegated by: approved product specification.
- Reason: one job must tell the full workshop story while ERPNext remains financially authoritative.
- Verified evidence: Repair Job controller, service/component DocTypes, ERPNext adapters, trace fields, and acceptance tests.
- Alternatives considered: separate workshop ledger or one job per fleet campaign; rejected because they break traceability/authority.
- Trade-offs accepted: adapter complexity and dependency on ERPNext document semantics.

### AD-003 — Server-authoritative POST mutations and permission-scoped reads

- Status: Accepted
- Approved or delegated by: repository `AGENTS.md` and approved specification.
- Reason: protect workflow, financial, stock, customer, and portal boundaries.
- Verified evidence: whitelisted GET/POST methods, `check_permission`/`has_permission` usage, report runner scope, and portal tests.
- Alternatives considered: client-authoritative transitions or guest mutations; rejected as unsafe.
- Trade-offs accepted: more server validation and explicit mapping methods.

### AD-004 — Native Frappe Desk/website surfaces

- Status: Accepted
- Approved or delegated by: existing design contracts and product scope.
- Reason: preserve platform accessibility, permissions, navigation, forms, reports, and maintainability.
- Verified evidence: workspace fixtures/setup, DocType JS, native form layout contracts, and `/my-repairs` route.
- Alternatives considered: Vue/custom shell and custom portal; rejected as outside approved scope.
- Trade-offs accepted: less bespoke visual freedom and reliance on native responsive behavior.

### AD-005 — Docker Compose bench plus gated immutable image deployment

- Status: Accepted
- Approved or delegated by: repository deployment rules.
- Reason: reproducible local/runtime parity with explicit non-image-first and immutable-tag controls.
- Verified evidence: Compose files, deployment Containerfile/resources, README, and project instructions.
- Alternatives considered: direct host install or mutable production tags; rejected for drift and rollback risk.
- Trade-offs accepted: multi-container local resource cost and explicit approval sequencing.

## 22. Dependencies and Technology Relationships

```text
Browser / customer portal
        -> Nginx
        -> Frappe backend + website/Desk
        -> auto_service_management domain/controllers
        -> Frappe ORM + ERPNext DocTypes
        -> MariaDB

Frappe backend -> Redis cache/queue/socket -> workers/scheduler/Socket.IO
ERPNext documents <-> app integration adapters/hooks/traces
Docker Compose -> all local runtime services
```

Data ownership: app owns workshop records and policy snapshots; ERPNext owns commercial/stock/accounting records; Frappe owns identity/session/platform metadata; MariaDB persists the site; Redis is operational cache/queue/pub-sub, never business authority. Independent failure components are Nginx, backend, database, Redis/queues, websocket, and workers; each must have health/log evidence before release claims.

## 23. Known Constraints and Accepted Trade-offs

- Frappe/ERPNext v16 compatibility constrains APIs, DocType behavior, and native UI patterns.
- Python 3.14/Node 24 and Docker Desktop improve reproducibility but increase local resource requirements.
- Shared ERPNext authority simplifies accounting correctness but requires focused adapters and contract tests.
- Native Desk reduces frontend maintenance but limits bespoke interaction/visual freedom.
- MariaDB/Frappe document transactions fit current scale; no speculative sharding, search service, or event bus is justified.
- Customer portal privacy is strong because it is read-only/submitted-only, but customer self-service mutation is intentionally unavailable.
- Image deployment is intentionally gated behind non-image dev proof and explicit approval.

## 24. Explicitly Deferred Architecture

- Custom Vue portal or mobile app — deferred because current product requires native Desk plus read-only website; reconsider only with approved self-service mutation/mobile requirements.
- External object storage/search/observability platform — deferred because current scale and platform storage/logging are sufficient; reconsider with measured volume, search, or operations requirements.
- Microservices/event-sourced workflow — deferred because one-site transactional consistency and current team/operations favor a modular monolith; reconsider only with independently scaling bounded contexts proven by measurements.
- OCR, third-party messaging, EFRIS activation, offline-first, and multi-currency conversion — deferred by product scope; each requires a new product/architecture decision.

## 25. Remaining OPEN Decisions

None - no material unresolved decisions. This file records the current existing architecture; any future material change must create a new decision record and reconcile `PRODUCT.md` and `DESIGN.md` first.

ARCHITECTURE CONTRACT: COMPLETE

Major decisions: [5]
Open material decisions: 0
Architecture coherence: PASS
Product coverage: PASS
Unnecessary complexity review: PASS

STATUS: READY FOR TRACER-BULLET SPECIFICATION
