# Auto Service Management

`auto_service_management` is a GPL-3.0 Frappe/ERPNext v16 vertical app for automobile workshop operations. It provides a garage-facing Repair Job while reusing ERPNext for Projects, Tasks, Timesheets, Items, stock movements, sales documents, payments, and accounting.

The local development suite now runs four bench apps together:

- `erpnext` on `version-16`
- `auto_service_management` from this workspace
- `hrms` on `version-16`
- `uganda_compliance` on `hotfix-v-16`

## Planned Workflow

Customer Vehicle → Repair Job → Walkaround Inspection → Diagnosis → Estimate → Customer Authorization → Tasks and Timesheets → Parts Issue → Quality Check → Road Test → Sales Invoice → Gate Pass → Service History.

One Repair Job always represents one Customer Vehicle and one ERPNext Project. Fleet Service Campaigns group multiple independent Repair Jobs.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose on Linux)
- Git

## Quick Start (Docker)

1. **Clone the repo:**

```bash
git clone https://github.com/your-org/auto_service_management.git
cd auto_service_management
```

2. **Add the hostname** (required on every machine):

```bash
# Windows (run PowerShell as Administrator)
Add-Content -Path C:\Windows\System32\drivers\etc\hosts -Value "127.0.0.1 auto-service.localhost auto-service-test.localhost"

# Linux/macOS
echo "127.0.0.1 auto-service.localhost auto-service-test.localhost" | sudo tee -a /etc/hosts
```

3. **Start the stack:**

```bash
docker compose -f docker-compose.dev.yml up -d
```

First run takes 15–20 minutes (bench init, app installs, site migrations, asset builds). Re-running the same command upgrades an existing local bench in place and should not require deleting `bench-data`.

4. **Verify:**

```bash
curl http://auto-service.localhost:8080/api/method/ping
# {"message":"pong"}
```

5. **Open the app:**

Navigate to [http://auto-service.localhost:8080](http://auto-service.localhost:8080) and log in:

| Field | Value |
|-------|-------|
| Username | `Administrator` |
| Password | `admin` |

6. **Run tests:**

```bash
docker exec dms-backend-1 bench --site auto-service-test.localhost run-tests --app auto_service_management
docker exec dms-backend-1 bench --site auto-service-test.localhost run-tests --app hrms
docker exec dms-backend-1 bench --site auto-service-test.localhost run-tests --app uganda_compliance
```

For suite-integration verification on July 22, 2026, the currently stable targeted HRMS check is:

```bash
docker exec dms-backend-1 bench --site auto-service-test.localhost run-tests --module hrms.hr.report.employee_hours_utilization_based_on_timesheet.test_employee_util --skip-before-tests
```

7. **Check installed apps on either site:**

```bash
docker exec dms-backend-1 bench --site auto-service.localhost list-apps
docker exec dms-backend-1 bench --site auto-service-test.localhost list-apps
```

Expected installed apps on both sites:

- `frappe`
- `erpnext`
- `auto_service_management`
- `hrms`
- `uganda_compliance`

## Services

| Service | Purpose | Port |
|---------|---------|------|
| `frontend` | Nginx reverse proxy | 8080 |
| `backend` | Frappe web server | 8000 |
| `websocket` | Socket.IO server | 9000 |
| `db` | MariaDB 11.8 | internal |
| `redis-cache` | Cache store | internal |
| `redis-queue` | Background job queue | internal |
| `redis-socketio` | Socket.IO pub/sub | internal |
| `scheduler` | Frappe scheduler | internal |
| `queue-default/short/long` | Background workers | internal |
| `setup` | Bench init, app sync/install, site migrate, asset build | exits after setup |

## Development

From inside the backend container:

```bash
docker exec -it dms-backend-1 bash

# Inside container:
bench --site auto-service.localhost migrate
bench build --app auto_service_management
bench build --app hrms
bench build --app uganda_compliance
bench --site auto-service.localhost run-tests --app auto_service_management
```

The backend runs `bench serve --noreload` for stability. To rebuild assets after code changes:

```bash
docker exec dms-backend-1 bench build --app auto_service_management
docker exec dms-backend-1 bench build --app hrms
docker exec dms-backend-1 bench build --app uganda_compliance
```

Then hard-refresh the browser.

## Platform Baseline

- Frappe and ERPNext: `version-16`
- Python: 3.14
- Node.js: 24
- MariaDB: 11.8
- Development: Docker Compose with official `frappe/bench` image
- Application license: GPL-3.0

## Safety

Do not edit ERPNext or Frappe core. Do not hardcode company accounts, tax rates, warehouses, price lists, or credit limits. Never use production customer, vehicle, signature, or attachment data in tests.

Uganda Compliance is installed for suite compatibility, but EFRIS remains dormant until a company explicitly configures the Uganda app settings and credentials. Local smoke tests should use the normal non-EFRIS Auto Service billing flow.

## Test Troubleshooting

Run bench tests sequentially on `auto-service-test.localhost`. Concurrent `bench run-tests` processes against the same site can produce misleading MariaDB deadlocks during ERPNext bootstrap on shared setup tables such as `tabSingles` and `tabGender`.

Known current upstream boundaries as of July 22, 2026:

- HRMS: `bench --site auto-service-test.localhost run-tests --module hrms.hr.report.project_profitability.test_project_profitability --skip-before-tests` is not currently blocked by the earlier bootstrap deadlock when run alone. It fails later during Salary Slip submit because wkhtmltopdf tries to render/email the payslip PDF and returns `HostNotFoundError`.
- Uganda Compliance: `bench --site auto-service-test.localhost run-tests --app uganda_compliance --skip-before-tests` currently fails in discovery because `uganda_compliance/efris/doctype/e_invoice/test_e_invoice.py` imports `get_sales_invoice_for_e_invoice` from ERPNext's `test_sales_invoice.py`, and that helper is absent in this ERPNext v16 checkout. The placeholder files `uganda_compliance/tests/test_integration.py` and `uganda_compliance/tests/test_vat_compliance.py` are empty, so the meaningful failure is the import mismatch, not those top-level test files.
- Baseline integrated smoke remains valid despite those upstream test boundaries: non-EFRIS Auto Service invoice submit/cancel works with Uganda Compliance installed, and HRMS Timesheet submit works with Auto Service trace-field synchronization.

See `AGENTS.md` for repository rules and `IMPLEMENTATION_PLAN.md` for tracked delivery status.
