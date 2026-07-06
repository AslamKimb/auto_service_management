# Auto Service Management

`auto_service_management` is a GPL-3.0 Frappe/ERPNext v16 vertical app for automobile workshop operations. It provides a garage-facing Repair Job while reusing ERPNext for Projects, Tasks, Timesheets, Items, stock movements, sales documents, payments, and accounting.

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

First run takes 15–20 minutes (bench init, ERPNext install, asset build). Subsequent starts are under a minute.

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
```

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
| `setup` | First-run bench init | exits after setup |

## Development

From inside the backend container:

```bash
docker exec -it dms-backend-1 bash

# Inside container:
bench --site auto-service.localhost migrate
bench build --app auto_service_management
bench --site auto-service.localhost run-tests --app auto_service_management
```

The backend runs `bench serve --noreload` for stability. To rebuild assets after code changes:

```bash
docker exec dms-backend-1 bench build --app auto_service_management
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

See `AGENTS.md` for repository rules and `IMPLEMENTATION_PLAN.md` for tracked delivery status.