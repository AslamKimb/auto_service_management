# Nissan Navara YD25 additions import guide

Prepared from `YD25- NAVARA.xlsx` as an additions-only package.

## Result

- New importable stock Items: 1
- New importable service Items: 0
- New Item Prices: 1
- Rows ignored because they already exist in the previous package: 263
- New source conflict rows held for review: 2
- Incomplete rows held for review: 1
- Source SHA-256: `3b680290c5f7c57717a603e19d5ecab4532b343727f9436de2c0e65b4f220af7`

## Import order

1. Do not re-import the previous package.
2. Skip `01_uoms.csv`, `02_item_groups.csv`, and `04_service_items.csv` if they contain only headers.
3. Import `03_stock_items.csv` as **Item** using **Insert New Records**.
4. Import `05_item_prices.csv` as **Item Price** using **Insert New Records**.
5. Do not import `review_duplicate_items.csv` or `review_incomplete_items.csv` until each row is manually resolved.
6. Keep `catalog_audit.csv` as the traceability file; it is not an import file.

## Important rules

- The item name includes the vehicle: `Nissan Navara – YD25 engine`.
- Prices use the source VAT-exclusive unit rate in UGX; ERPNext should calculate VAT.
- `BLADE ASSY WIND` has two different source prices and is intentionally excluded.
- `AC pipe brazing` has a missing quantity and is held in `review_incomplete_items.csv`.
- `Seat Covers` is excluded because it already exists in the previous package.
- No opening stock or stock quantities are included.
- CSV files are UTF-8 encoded.

## Verification

- Confirm the new item code is unique and searchable by `Nissan Navara` and `YD25`.
- Confirm its UOM is `PCS`, Item Group is `Services`, and its Standard Selling price is UGX 8,661.28.
- Create a test quotation/invoice and verify VAT is applied once.
- Keep this package separate from the previous catalog package.
