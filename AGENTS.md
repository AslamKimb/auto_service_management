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

## Development Environment

The dev stack runs via Docker Compose. All bench commands go through the backend container.

```bash
# Start the stack (first run takes ~15 min)
docker compose -f docker-compose.dev.yml up -d

# Enter the backend container
docker exec -it dms-backend-1 bash

# Or run a single command without entering
docker exec dms-backend-1 bench --site auto-service.localhost migrate
```

### Sites

| Site | Purpose |
|------|---------|
| `auto-service.localhost` | Interactive development |
| `auto-service-test.localhost` | Automated tests only |

### Ports

| Service | Port |
|---------|------|
| Nginx (frontend) | 8080 |
| Frappe backend | 8000 |
| Socket.IO | 9000 |

### Key files

| File | Role |
|------|------|
| `docker-compose.dev.yml` | Full 12-service Docker stack definition |
| `nginx.conf` | Reverse proxy config. Root is `.../sites` — do not change to `.../sites/assets` or CSS/JS will 404. |
| `bench-data/` | Ephemeral runtime data (DB, Redis, bench). Gitignored. |

## Development Commands

Run bench commands inside the backend container. Always name the site.

```bash
docker exec dms-backend-1 bench --site auto-service.localhost migrate
docker exec dms-backend-1 bench build --app auto_service_management
docker exec dms-backend-1 bench --site auto-service-test.localhost run-tests --app auto_service_management
docker exec dms-backend-1 bench --site auto-service.localhost export-fixtures --app auto_service_management
docker exec dms-backend-1 pre-commit run --all-files
```

Never run bare `bench migrate` or tests against the working development site (`auto-service.localhost`). The backend runs `bench serve --noreload`; after code changes, rebuild assets manually with `bench build --app auto_service_management` and hard-refresh the browser.

## Code and Data Conventions

Follow generated Frappe v16 structure and naming. Keep controllers focused, use small integration adapters for ERPNext internals, and prefer `frappe.qb` over raw SQL. Do not call `frappe.db.commit()` in controllers. Do not use `frappe.db.set_value()` for workflow transitions. Export only filtered, app-owned fixtures. Use patches for released data migrations, not initial setup.

## Verification and Safety

Write a failing test before behavior code, then run the smallest relevant test and the full app suite. Verify fresh install, repeated migration, fixture sync, and uninstall on the test site. Never commit credentials, populated `.env` files, backups, customer records, signatures, or vehicle photos. Production database migration and rollout require the approval gates recorded in `IMPLEMENTATION_PLAN.md`.