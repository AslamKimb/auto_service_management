# Phase 6 Role UI Walkthrough — 2026-06-30

## Goal

Verify the live Desk access surface for the five Phase 6 personas against the `Workshop Management` workspace and its role-targeted shortcuts after the permission-matrix repair.

## Method

- Verified on the active Docker bench site: `auto-service.localhost`
- Reused the dedicated walkthrough users, each scoped to a single custom role plus `Desk User`
- Audited live Desk permissions server-side after local browser automation remained blocked on `http://auto-service.localhost:8000`

## Global Finding

- All five walkthrough users now have `default_workspace = "Workshop Management"`.
- All five walkthrough users can read the `Workshop Management` workspace.
- The landing-route defect is resolved without granting broad `Page` read access.

## Role Results

| Role | Intended surface | Result | Notes |
| --- | --- | --- | --- |
| Service Advisor | Workshop Management workspace | Pass | Default workspace set and workspace readable |
| Service Advisor | Vehicle Search (`Customer Vehicle`) | Pass | `read` allowed |
| Service Advisor | New Repair Job (`Repair Job` create) | Pass | `create` allowed |
| Service Advisor | Approval Queue (`Customer Authorization`) | Pass | `read` allowed |
| Service Advisor | Open Repair Jobs report | Pass | Report executed successfully |
| Workshop Manager | Workshop Management workspace | Pass | Default workspace set and workspace readable |
| Workshop Manager | Repair Queue (`Repair Job`) | Pass | `read` allowed |
| Workshop Manager | QC Queue (`Quality Check`) | Pass | `read` allowed |
| Workshop Manager | Jobs by Status report | Pass | Report executed successfully |
| Parts Interpreter | Workshop Management workspace | Pass | Default workspace set and workspace readable |
| Parts Interpreter | Parts Queue report | Pass | Report executed successfully |
| Parts Interpreter | Repair Queue (`Repair Job`) | Pass | `read` allowed |
| Cashier | Workshop Management workspace | Pass | Default workspace set and workspace readable |
| Cashier | Invoice Queue (`Sales Invoice`) | Pass | `read` allowed through app-owned custom permission |
| Cashier | Jobs by Status report | Pass | Report executed successfully |
| Security Gate Officer | Workshop Management workspace | Pass | Default workspace set and workspace readable |
| Security Gate Officer | Gate Passes (`Gate Pass`) | Pass | `read` allowed |
| Security Gate Officer | Service History | Pass | `read` allowed |

## Conclusion

The Phase 6 role walkthrough now passes end to end on the live site for all five target personas.

## Verification Source

Audit rerun executed on 2026-06-30 against the live site with these users:

- `walkthrough.service.advisor@example.com`
- `walkthrough.workshop.manager@example.com`
- `walkthrough.parts.interpreter@example.com`
- `walkthrough.cashier@example.com`
- `walkthrough.security.gate@example.com`
