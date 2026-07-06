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
| `nginx.conf` | Reverse proxy config. Root is `.../sites` â€” do not change to `.../sites/assets` or CSS/JS will 404. |
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

## Docker Dev Workflow Gotchas

### 1. Stale Redis Cache â€” Module Map Empty

**Symptom:** Clicking the app icon shows "Page X not found". `bench migrate` completes but no DocTypes are created.

**Root cause:** When `frappe serve` starts, it calls `setup_module_map(include_all_apps=True)` which caches `app_modules` in Redis. If the editable install was broken at startup time (e.g., Python 3.14 namespace package issue), `get_module_list('auto_service_management')` returns empty, and Redis caches `{"auto_service_management": []}`. Every subsequent `bench init()` loads from this stale cache, so `sync_for()` iterates over an empty list and never syncs DocTypes.

**Fix:**
```bash
# Clear stale Redis cache
docker exec dms-backend-1 python -c "
import frappe
frappe.init('auto-service.localhost', sites_path='/home/frappe/bench-home/frappe-bench/sites')
frappe.connect()
app_modules = {}
apps = frappe.get_all_apps(with_internal_apps=True)
for app in apps:
    app_modules.setdefault(app, [])
    for module in frappe.get_module_list(app):
        module = frappe.scrub(module)
        app_modules[app].append(module)
frappe.cache.set_value('app_modules', app_modules)
frappe.destroy()
print('Redis cache fixed')
"

# Restart backend to pick up corrected cache
docker compose -f docker-compose.dev.yml restart backend
```

**Verify:**
```bash
docker exec dms-backend-1 python -c "
import frappe
frappe.init('auto-service.localhost', sites_path='/home/frappe/bench-home/frappe-bench/sites')
frappe.connect()
print(frappe.local.app_modules.get('auto_service_management'))
"
# Should show: ['auto_service_management']
```

### 2. Desktop Icon Must Use Workspace Sidebar

**Symptom:** App icon on desk triggers `getpage` 404 error.

**Root cause:** The Desktop Icon was created with `link_type = "External"`. In Frappe v16, workspace icons must use `link_type = "Workspace Sidebar"` with `link_to` set to the workspace name.

**Fix (DB):**
```sql
UPDATE `tabDesktop Icon`
SET link_type = 'Workspace Sidebar', link_to = 'Workshop Management'
WHERE name = 'Auto Service Management';
```

**Fix (code):** See `auto_service_management/desktop.py` â€” the `create_app_desktop_icon()` function must set `link_type = "Workspace Sidebar"` and `link_to = workspace_name`.

### 3. Editable Install on Python 3.14

**Symptom:** `pip install -e .` fails with namespace package errors.

**Fix:**
```bash
docker exec dms-backend-1 pip install -e /home/frappe/bench-home/frappe-bench/apps/auto_service_management --no-deps
```

### 4. Browser Cache After Server Fixes

**Symptom:** Server-side fixes are in place but the desk still shows old errors.

**Fix:** Hard-refresh the browser (`Ctrl+Shift+R` / `Cmd+Shift+R`). The Frappe desk caches boot session data in `localStorage`. A hard refresh forces a fresh boot payload.

### 5. PowerShell Gotchas

- Backticks in SQL strings are consumed by PowerShell â€” use `sh -c` wrapper or write SQL to file + `docker cp`
- Heredocs don't work through PowerShell â€” use `Set-Content` + `docker cp`
- Profile noise from `Set-PSReadLineOption` is harmless

### 6. bench migrate Can Take Several Minutes

`bench migrate` with DocType sync can take 5-10+ minutes on first run. Use background execution:
```bash
docker exec -d dms-backend-1 sh -c "bench --site auto-service.localhost migrate > /tmp/migrate_output.log 2>&1"
docker exec dms-backend-1 tail -f /tmp/migrate_output.log
```

Remove stale lock files if a previous migrate was killed:
```bash
docker exec dms-backend-1 rm -f /home/frappe/bench-home/frappe-bench/sites/auto-service.localhost/locks/bench_migrate.lock
```

### 7. Container Paths

```
Bench root:    /home/frappe/bench-home/frappe-bench/
Apps:          /home/frappe/bench-home/frappe-bench/apps/
Site config:   /home/frappe/bench-home/frappe-bench/sites/auto-service.localhost/
Virtual env:   /home/frappe/bench-home/frappe-bench/env/
Logs:          /home/frappe/bench-home/frappe-bench/logs/
```

### 8. Database Access

```bash
docker exec dms-db-1 sh -c "mariadb -u _d0285d3abb0895b4 -p1fRi5pW1fwcK769i _d0285d3abb0895b4 < /tmp/query.sql"
```

### 9. Socket.IO "Invalid origin" in Docker

**Symptom:** Browser console shows `Error connecting to socket.io: Invalid origin`. The Desk loads but real-time features (notifications, document updates) fail.

**Root cause:** The Socket.IO authenticate middleware (`realtime/middlewares/authenticate.js`) compares the hostname from the `Host` header with the hostname from the `Origin` header using `get_hostname()`. In Docker, nginx proxies WebSocket connections and sets `Host` to `auto-service.localhost` (no port), while the browser sends `Origin: http://auto-service.localhost:8080`. Both resolve to `auto-service.localhost` via `get_hostname()`, but if the WebSocket connection bypasses nginx or headers are missing, the comparison fails.

**Fix:** Add `allow_cors` to `common_site_config.json`:

```bash
docker exec dms-backend-1 python3 -c "
import json
path = '/home/frappe/bench-home/frappe-bench/sites/common_site_config.json'
with open(path) as f:
    conf = json.load(f)
conf['allow_cors'] = ['http://auto-service.localhost:8080', 'http://auto-service.localhost']
with open(path, 'w') as f:
    json.dump(conf, f, indent=1)
print('done')
"
docker compose -f docker-compose.dev.yml restart websocket
```

The `docker-compose.dev.yml` setup flow already includes this config step (added in `setup` service after `bench migrate`).

**Verify:**
```bash
# Check config is set
docker exec dms-backend-1 python3 -c "
import json
with open('/home/frappe/bench-home/frappe-bench/sites/common_site_config.json') as f:
    print('allow_cors' in json.load(f))
"
# Should print: True
```

### 10. Workspace Fixture Must Include `type` Field

**Symptom:** Fresh install via `bench migrate` fails to create the workspace, or `bench export-fixtures` produces an incomplete workspace JSON.

**Root cause:** The Workspace DocType defines `type` as a required field (`reqd: 1`), with a DB default of `'Workspace'`. The fixture JSON must include `"type": "Workspace"` for clean exports/imports.

**File:** `auto_service_management/auto_service_management/auto_service_management/workspace/workshop_management/workshop_management.json`

**Required field at top level:**
```json
{
  "type": "Workspace",
  "doctype": "Workspace",
  ...
}
```

**Verify:**
```bash
Get-Content "auto_service_management\auto_service_management\auto_service_management\workspace\workshop_management\workshop_management.json" -Raw | ConvertFrom-Json | Select-Object type
# Should output: Workspace
```


### 11. Workspace Fixture Must Include `app` Field

**Symptom:** Workspace exists in DB but clicking the app icon gives "Page X not found" 404. The boot data shows 0 workspace pages and empty sidebar items. The desk SPA can't resolve the workspace route.

**Root cause:** The 	abWorkspace.app column is NULL. Frappe v16's oot.py load_desktop_data() joins Workspace records with Module Def to build per-app workspace lists. When `app` is NULL, the workspace doesn't appear in any app's workspace list, so the SPA doesn't recognize the route and falls back to calling the legacy getpage API which looks for a Page doctype.

**Fix (fixture):** Add "app": "auto_service_management" to the workspace fixture JSON.

**File:** uto_service_management/auto_service_management/auto_service_management/workspace/workshop_management/workshop_management.json

**Required field at top level:**
`json
{
  "app": "auto_service_management",
  "type": "Workspace",
  "doctype": "Workspace",
  ...
}
`

**Fix (DB, existing installs):**
`sql
UPDATE 	abWorkspace SET app = 'auto_service_management' WHERE name = 'Workshop Management';
`

**Verify:**
`sql
SELECT name, app, module FROM 	abWorkspace WHERE name = 'Workshop Management';
-- app should be 'auto_service_management', not NULL
`

### 12. Workspace Sidebar Entry Required for Desk Navigation

**Symptom:** Desktop Icon exists with correct link_type = "Workspace Sidebar" and link_to = "Workshop Management", but clicking the app icon still gives 404.

**Root cause:** Frappe v16's desk loads workspace route resolution from Workspace Sidebar records. The get_desktop_icons() function in desktop_icon.py checks ootinfo.workspace_sidebar_item.get(s.label.lower()) to determine if the sidebar exists and has items. Without a Workspace Sidebar record, the sidebar check fails and the workspace isn't registered in the boot data.

**Fix:** Create a Workspace Sidebar record with a child Workspace Sidebar Item linking to the workspace:

`sql
-- Sidebar parent (skip if already exists)
INSERT IGNORE INTO 	abWorkspace Sidebar (name, title, app, standard, owner, creation, modified, modified_by, docstatus, idx)
VALUES ('Workshop Management', 'Workshop Management', 'auto_service_management', 1, 'Administrator', NOW(6), NOW(6), 'Administrator', 0, 0);

-- Sidebar item (check if already exists first)
INSERT IGNORE INTO 	abWorkspace Sidebar Item (name, creation, modified, modified_by, owner, docstatus, idx, label, link_type, link_to, type, parent, parentfield, parenttype)
SELECT UUID(), NOW(6), NOW(6), 'Administrator', 'Administrator', 0, 0, 'Workshop Management', 'Workspace', 'Workshop Management', 'Link', 'Workshop Management', 'items', 'Workspace Sidebar'
WHERE NOT EXISTS (SELECT 1 FROM 	abWorkspace Sidebar Item WHERE parent = 'Workshop Management' AND link_to = 'Workshop Management');
`

**Verify:**
`sql
SELECT s.name, s.app, i.label, i.link_type, i.link_to
FROM 	abWorkspace Sidebar s
JOIN 	abWorkspace Sidebar Item i ON i.parent = s.name
WHERE s.name = 'Workshop Management';
`

**Also run after creating the sidebar:**
`ash
docker exec dms-backend-1 bench --site auto-service.localhost clear-cache
docker exec dms-backend-1 bench build --app auto_service_management
docker compose -f docker-compose.dev.yml restart
`

## Quick Diagnostic Commands

```bash
# Check DocTypes synced
docker exec dms-db-1 sh -c "mariadb -u _d0285d3abb0895b4 -p1fRi5pW1fwcK769i _d0285d3abb0895b4 -e 'SELECT count(*) FROM tabDocType WHERE module=\"Auto Service Management\";'"
# Expected: 17

# Check workspace exists
docker exec dms-db-1 sh -c "mariadb -u _d0285d3abb0895b4 -p1fRi5pW1fwcK769i _d0285d3abb0895b4 -e 'SELECT name FROM tabWorkspace WHERE module=\"Auto Service Management\";'"

# Check module map
docker exec dms-backend-1 python -c "
import frappe
frappe.init('auto-service.localhost', sites_path='/home/frappe/bench-home/frappe-bench/sites')
frappe.connect()
print(frappe.local.app_modules.get('auto_service_management'))
"

# Check container health
docker compose -f docker-compose.dev.yml ps -a
```



