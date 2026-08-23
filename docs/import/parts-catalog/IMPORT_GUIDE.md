# Parts Catalog Import Guide

Prepared from `docs/item details.csv` for manual ERPNext Data Import.

## Output summary

- Stock Items: 1458
- Non-stock service Items: 25
- Item Prices: 1482
- Ambiguous source rows held for review: 37 rows across 18 item keys
- Exact duplicate source rows collapsed: 7 rows
- Source VAT arithmetic mismatches flagged in the audit: 380; differences greater than 1 UGX: 5

## Import order

1. Back up the target site.
2. Verify the target company, UGX currency, Standard Selling price list, and existing standard UOMs/Item Groups.
3. Open **Home > Data > Data Import**.
4. For each import below, select **Insert New Records**, use the matching DocType, attach the CSV, validate, resolve warnings, and click **Start Import**:
   - `01_uoms.csv` → **UOM**
   - `02_item_groups.csv` → **Item Group**
   - `03_stock_items.csv` → **Item**
   - `04_service_items.csv` → **Item**
   - `05_item_prices.csv` → **Item Price**
5. Do not import `review_duplicate_items.csv` until each conflict has been resolved.
6. Use `catalog_audit.csv` as the source-to-output audit file, not as an import file.

## Important rules

- Keep the generated `item_code` values unchanged; Item Price rows link to them.
- Prices use the VAT-exclusive source value in UGX. ERPNext should calculate VAT through its configured tax setup.
- No opening stock or stock quantities are included.
- UTF-8 CSV encoding is intentional; do not convert it to a local legacy encoding.

## Verification after import

- Search for an item using each vehicle group, for example `Nissan vehicles - YD25 engine`.
- Add a stock part to a Repair Job Service Part row and confirm Item, UOM, warehouse, and Standard Selling price fetch correctly.
- Add a service Item to a Labour/service flow and confirm it does not create stock quantities.
- Create a test quotation/invoice and confirm ERPNext applies the configured VAT behavior once.
- Compare imported counts with this guide before resolving review rows.

Official references:
- https://docs.frappe.io/erpnext/data-import
- https://docs.frappe.io/erpnext/item
- https://docs.frappe.io/erpnext/item-price
