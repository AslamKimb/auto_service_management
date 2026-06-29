# Auto Service Management

`auto_service_management` is a GPL-3.0 Frappe/ERPNext v16 vertical app for automobile workshop operations. It provides a garage-facing Repair Job while reusing ERPNext for Projects, Tasks, Timesheets, Items, stock movements, sales documents, payments, and accounting.

## Planned Workflow

Customer Vehicle → Repair Job → Walkaround Inspection → Diagnosis → Estimate → Customer Authorization → Tasks and Timesheets → Parts Issue → Quality Check → Road Test → Sales Invoice → Gate Pass → Service History.

One Repair Job always represents one Customer Vehicle and one ERPNext Project. Fleet Service Campaigns group multiple independent Repair Jobs.

## Platform Baseline

- Frappe and ERPNext: `version-16`
- Python: 3.14
- Node.js: 24
- MariaDB: 11.8
- Development: official `frappe_docker` development container
- Application license: GPL-3.0

## Development Sites

- `auto-service.localhost`: interactive development
- `auto-service-test.localhost`: automated tests only

From the v16 bench:

```bash
bench --site auto-service.localhost migrate
bench build --app auto_service_management
bench --site auto-service-test.localhost run-tests --app auto_service_management
```

See `AGENTS.md` for repository rules and `IMPLEMENTATION_PLAN.md` for tracked delivery status.

## Safety

Do not edit ERPNext or Frappe core. Do not hardcode company accounts, tax rates, warehouses, price lists, or credit limits. Never use production customer, vehicle, signature, or attachment data in tests.
