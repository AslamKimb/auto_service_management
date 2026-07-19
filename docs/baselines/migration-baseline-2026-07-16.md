# Migration Baseline

Site: `auto-service-test.localhost`

Backup created:

- Database: `sites/auto-service-test.localhost/private/backups/20260717_003646-auto-service-test_localhost-database.sql.gz`
- Config: `sites/auto-service-test.localhost/private/backups/20260717_003646-auto-service-test_localhost-site_config_backup.json`
- Public files: `sites/auto-service-test.localhost/private/backups/20260717_003646-auto-service-test_localhost-files.tar`
- Private files: `sites/auto-service-test.localhost/private/backups/20260717_003646-auto-service-test_localhost-private-files.tar`

## Snapshot

The test site is currently empty for the repair workflow domain. All core records, linked documents, and payment records below have zero rows.

## Counts

| Document | Count |
| --- | ---: |
| Repair Job | 0 |
| Repair Job Service | 0 |
| Repair Service Template | 0 |
| Customer Authorization | 0 |
| Road Test Report | 0 |
| Quality Check | 0 |
| Sales Invoice | 0 |
| Payment Entry | 0 |

## Relationships

| Relationship | Count |
| --- | ---: |
| Repair Jobs with any service | 0 |
| Repair Jobs with invoice link | 0 |
| Repair Jobs with paid payment status | 0 |
| Repair Job Services linked to template | 0 |
| Sales Invoice Items linked to job | 0 |
| Sales Invoice Items linked to service | 0 |
| Payment Entry References to Sales Invoice | 0 |

## Totals

| Metric | Value |
| --- | ---: |
| Repair Job total amount | 0 |
| Repair Job Service total amount | 0 |
| Repair Job Service cost total | 0 |
| Repair Job Service gross margin | 0 |
| Sales Invoice grand total | 0 |
| Sales Invoice outstanding amount | 0 |
| Sales Invoice paid amount | 0 |
| Sales Invoice payment allocation total | 0 |

## Notes

- `Repair Job Service` relationship fields are stored on the service itself.
- `Sales Invoice` service linkage is captured through `Sales Invoice Item` rows.
- The backup is restorable from the site private backups directory above.
