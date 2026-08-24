# Car Workshop Navigation Design

## Decision

Car Workshop uses native Frappe v16 App and Workspace navigation. The app icon opens a compact parent modal containing eight role-filtered workspaces:

1. Overview
2. Intake
3. Workshop
4. Parts & Billing
5. Quality & Release
6. Fleet & History
7. Reports
8. Setup

The existing `Workshop Management` route remains the Overview workspace so existing bookmarks and the default desk route continue to work.

## Intent and audience

The navigation is for service advisors, technicians, parts and cashier staff, gate officers, workshop managers, accounts staff, and system administrators. It should make the next operational action obvious without exposing a long, undifferentiated menu. Role visibility is a navigation aid only; DocType permissions remain the authority.

## Reference direction and principles

The reference is the native Frappe HRMS app launcher: one branded parent app icon, a small grid of workspace cards, and each workspace using a short, grouped sidebar. Use native Frappe surfaces, labels, icons, routes, empty states, and permission filtering. Do not introduce a custom Vue shell, custom CSS navigation, or duplicate business actions.

## Information architecture

- **Overview**: operational charts, five operational KPI cards, and three high-frequency shortcuts.
- **Intake**: customer, vehicle, repair-job creation, and optional assessment/authorization records.
- **Workshop**: active repair queues, service lines, bays, templates, and technician-oriented reports.
- **Parts & Billing**: parts queue, material requests, Sales Orders, Sales Invoices, payments, and finance reports.
- **Quality & Release**: quality checks, gate passes, service history, and release reports.
- **Fleet & History**: fleet campaigns, customers, vehicles, and service history.
- **Reports**: all registered operational reports grouped by operations, parts/labour, customer/release, and finance/controls.
- **Setup**: app settings, bays, vehicle catalog, templates, overrides, and logs.

## Layout, density, and responsive behavior

The parent launcher uses the native Frappe four-column modal grid. Cards use concise labels and familiar line icons. Workspace sidebars use one Home link followed by a small number of section breaks and permission-filtered links. Keep labels to one line where possible and group links by a user's workflow rather than by database table type. On narrow screens, rely on Frappe's native launcher/sidebar collapse and allow the workspace content to stack; do not add horizontal navigation or custom overflow behavior.

## Color, typography, and icon treatment

Use the active Frappe/ERPNext theme and typography. Do not hard-code a new palette. Use the app's existing car-front icon/logo and native Lucide icons for workspace links. Status colors and badges remain governed by Frappe and ERPNext conventions.

## Interaction and states

Clicking Car Workshop opens the app launcher; clicking a child card opens its workspace. Workspace links must remain permission-aware and must not grant access. Empty and filtered states should use native Desk behavior. Existing creation buttons, workflows, and document permissions are unchanged.

## Metrics policy

Overview keeps only operational charts and KPI cards: repair status, intake trend, closed-repair revenue, gate-pass status, quality-check status, open jobs, pending authorizations, pending quality checks, issued gate passes, and ongoing fleet campaigns. Technical DocType and child-table coverage counters are not placed on staff-facing workspace pages; their records and server-side card definitions may remain for compatibility.

## Acceptance

- The app launcher has eight distinct native workspace cards for permitted users.
- The Overview route remains `/desk/workshop-management`.
- Each hub has a role-filtered sidebar with no duplicate links within that sidebar.
- Workspace content contains operational metrics only; no technical coverage section is visible.
- Desktop and narrow viewport rendering use the native Frappe launcher/sidebar without clipping or custom shells.
