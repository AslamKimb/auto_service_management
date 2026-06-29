# Repository Guidelines

## Goal and Sources of Truth

This repository contains the `auto_service_management` Frappe app for ERPNext v16. Implement the approved requirements in this order: `docs/specs/automobile-repair-management.md`, `IMPLEMENTATION_PLAN.md`, then `Automotive DMS.md` as contextual research only. Do not expand scope from the research notes.

## Architecture Rules

- Keep all behavior inside this app. Never edit Frappe or ERPNext core files.
- Reuse ERPNext Project, Task, Timesheet, Item, Quotation, Sales Order, Sales Invoice, Material Request, Stock Entry, Customer, payments, and accounting.
- Use `Customer Vehicle`; ERPNext already owns the `Vehicle` DocType.
- One Repair Job represents one vehicle and one Project. Fleet campaigns group separate jobs.
- ERPNext is authoritative for pricing, taxes, stock, credit limits, and ledger postings.
- Put user-triggered mutations in typed, POST-only controller methods with server-side permission checks.

## Development Commands

Run commands from the v16 bench inside the official development container. Use bare `bench` and always name the site.

- `bench --site auto-service.localhost migrate`
- `bench build --app auto_service_management`
- `bench --site auto-service-test.localhost run-tests --app auto_service_management`
- `bench --site auto-service.localhost export-fixtures --app auto_service_management`
- `pre-commit run --all-files`

Never run bare `bench migrate` or tests against the working development site. Start `bench start` only in a background terminal after confirming another instance is not running.

## Code and Data Conventions

Follow generated Frappe v16 structure and naming. Keep controllers focused, use small integration adapters for ERPNext internals, and prefer `frappe.qb` over raw SQL. Do not call `frappe.db.commit()` in controllers. Do not use `frappe.db.set_value()` for workflow transitions. Export only filtered, app-owned fixtures. Use patches for released data migrations, not initial setup.

## Verification and Safety

Write a failing test before behavior code, then run the smallest relevant test and the full app suite. Verify fresh install, repeated migration, fixture sync, and uninstall on the test site. Never commit credentials, populated `.env` files, backups, customer records, signatures, or vehicle photos. Production database migration and rollout require the approval gates recorded in `IMPLEMENTATION_PLAN.md`.
