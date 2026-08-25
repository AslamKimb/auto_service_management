# Fitment-aware parts catalog import

This package separates stock identity from vehicle compatibility:

```text
Item (one physical part / stock balance)
        └── Item Vehicle Fitment (zero or more make/model/engine/year matches)
```

One oil filter that fits five vehicles is one ERPNext **Item** with five fitment
rows. Do not create five stock Items just because the part has five
applications.

## Files and import order

1. `vehicle_reference.csv` — controlled make/model reference used by the validator.
2. `engine_reference.csv` — controlled engine-model reference; include make/model
   when an engine is restricted to a vehicle family.
3. `01_items.csv` → **Item** — insert Items first. Use the standard ERPNext
   fields shown in the template. `item_code` is the stock identity used by the
   Item Price and fitment imports.
4. `02_item_vehicle_fitment.csv` → **Item Vehicle Fitment** — insert fitments
   only after their Item, vehicle, and engine references exist.
5. `03_item_manufacturers.csv` → **Item Manufacturer** child rows — use this
   when a part has more than the Item's default manufacturer number, or when
   the OEM number needs its own manufacturer-scoped identity.

The reference CSVs are validator inputs, not ERPNext Data Import files. Keep
them with the package for review. The validator never connects to a site and
never changes the database.

## Identifier rules

- The Item template uses native ERPNext fields
  `default_item_manufacturer` and `default_manufacturer_part_no`. For multiple
  manufacturer/OEM numbers, use the native `Item Manufacturer` child template
  (`03_item_manufacturers.csv`) rather than inventing top-level Item fields.
  The validator also accepts `manufacturer_part_no`, `oem_part_no`, and
  `manufacturer` source columns so legacy review files can be checked without
  losing independent identities.
- Keep a barcode in `barcodes.barcode` when it is known. Preserve leading zeroes
  by formatting the spreadsheet column as text before saving CSV.
- When neither is available, use a controlled internal code beginning with
  `ASM-` or `PROV-` (for example `PROV-NAVARA-OIL-FILTER-001`). Do not use a
  vehicle description as a substitute identifier.
- The validator normalizes case and punctuation for duplicate checks, so
  `15208-65F0A` and `15208 65F0A` are reviewed as the same part number.

## Fitment rules

- `item` must equal an Item `item_code` in `01_items.csv`.
- The fitment DocType fields are `item`, `vehicle_make`, `vehicle_model`,
  `vehicle_engine`, `year_from`, `year_to`, and `verification_status`. The
  validator accepts the older `engine_model`, `from_year`, `to_year`, and
  `status` aliases only for legacy review files; new imports must use the
  canonical fields in the template.
- Make/model/engine are optional to support a universal part. A model requires
  a make. If a reference CSV is supplied, every named make/model/engine must be
  present and an engine tied to a make/model must belong to that pair.
- `year_from` and `year_to` are optional; when present they must be integer
  years from 1886 through 2100, with `year_from <= year_to`.
- `verification_status` is exactly `Verified` or `Provisional` (case-insensitive for
  validation). Use `Provisional` until a trusted catalogue, supplier document,
  or technician check supports the match.
- A duplicate fitment key is the same Item + make + model + engine + year range,
  regardless of notes or source. Resolve every duplicate before importing.

## Validate and review

From the repository root:

```powershell
python scripts/validate_fitment_import.py `
  --items docs/import/parts-catalog/fitment/01_items.csv `
  --fitments docs/import/parts-catalog/fitment/02_item_vehicle_fitment.csv `
  --vehicle-reference docs/import/parts-catalog/fitment/vehicle_reference.csv `
  --engine-reference docs/import/parts-catalog/fitment/engine_reference.csv `
  --report docs/import/parts-catalog/fitment/review_report.csv
```

The command exits `0` only when there are no errors. It exits `1` when review
is required and writes a CSV with `severity`, `entity`, `row_number`, `code`,
`identity_key`, and `message`. Warnings for missing reference files are useful
signals, but do not make a package pass. A report is not an import file.

The validator catches duplicate Item identity (item code, OEM/manufacturer
number, or barcode), duplicate fitment keys, missing Item/vehicle/engine
references, invalid year values/ranges, invalid status, and uncontrolled
internal SKUs. It only reads the two import CSVs and reference CSVs; the only
write is the explicitly requested review report.

## Current source limitations

The current `docs/item details.csv` and earlier parts packages contain vehicle
groups embedded in item names (for example, `Nissan vehicles – YD25 engine`).
They do not reliably contain manufacturer/OEM part numbers, barcodes, exact
make/model/year ranges, or authoritative engine references. Existing duplicate
and incomplete review files also show category/price ambiguity. Therefore:

- do not infer a verified fitment merely from an Item name;
- do not mass-split the existing Items by make/model/engine;
- import a provisional Item and fitment only when its source is recorded in
  `source`, then resolve it through the review report;
- obtain authoritative identifiers and application data from supplier/OEM
  catalogues or technician confirmation before marking a row `Verified`.

The older `docs/import/parts-catalog/03_stock_items.csv` and
`04_service_items.csv` packages remain historical import artifacts. Regenerate
future parts packages in this fitment-aware shape instead of adding more
vehicle text to Item names.

Official ERPNext references:

- [Data Import](https://docs.frappe.io/erpnext/data-import)
- [Item](https://docs.frappe.io/erpnext/item)
