import csv
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(r"C:\Users\user\Documents\Coded\DMS")
SOURCE_JSON = ROOT / ".codex-work" / "yd25-navara" / "source_inspect.json"
SOURCE_XLSX = Path(r"C:\Users\user\Downloads\YD25- NAVARA.xlsx")
PREVIOUS_AUDIT = ROOT / "docs" / "import" / "parts-catalog" / "catalog_audit.csv"
PREVIOUS_GROUPS = ROOT / "docs" / "import" / "parts-catalog" / "02_item_groups.csv"
OUT = ROOT / "docs" / "import" / "parts-catalog" / "yd25-navara-additions"
VEHICLE_GROUP = "Nissan Navara – YD25 engine"

def text(value):
    return "" if value is None else str(value).strip()

def norm(value):
    value = unicodedata.normalize("NFKD", text(value)).encode("ascii", "ignore").decode()
    value = re.sub(r"[^A-Za-z0-9]+", " ", value.upper())
    return re.sub(r"\s+", " ", value).strip()

def slug(value):
    return re.sub(r"[^A-Z0-9]+", "-", norm(value)).strip("-")

def money(value):
    try:
        return f"{Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"
    except (InvalidOperation, TypeError, ValueError):
        return ""

def decimal_value(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None

def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)

def write_csv(path, headers, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

payload = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
values = payload["sheets"][0]["values"]
previous = list(csv.DictReader(PREVIOUS_AUDIT.open(encoding="utf-8-sig", newline="")))
previous_keys = {norm(row.get("source_item_name")) for row in previous if text(row.get("source_item_name"))}
previous_groups = {text(row.get("item_group_name")) for row in csv.DictReader(PREVIOUS_GROUPS.open(encoding="utf-8-sig", newline=""))}
existing_groups = previous_groups | {"Services", "All Item Groups"}
existing_uoms = {"PCS", "Set", "Litre", "Hour", "Unit", "Kilometer", "0.25L", "Lump Sum"}

uom_map = {
    "PC": "PCS",
    "PCS": "PCS",
    "SET": "Set",
    "L": "Litre",
    "LITRE": "Litre",
    "HOUR": "Hour",
    "UNIT": "Unit",
    "KILOMETER": "Kilometer",
    "0.25L": "0.25L",
    "LUMP SUM": "Lump Sum",
}

section_names = set()
current_section = "Unclassified"
raw_rows = []
for source_row, row in enumerate(values, start=1):
    name = text(row[0] if len(row) > 0 else None)
    qty = row[1] if len(row) > 1 else None
    unit = text(row[2] if len(row) > 2 else None)
    exclusive = row[3] if len(row) > 3 else None
    if not name and qty is None:
        continue
    if not numeric(qty):
        if name.upper() in {"PARTS LIST FOR NISSAN VEHICLES", "SYSTEM COMPONENTS", "TOTAL PRICE"} or text(qty).upper() == "QTY":
            continue
        if name and exclusive is None:
            current_section = name.title()
            section_names.add(norm(name))
        elif name and exclusive is not None:
            raw_rows.append({
                "source_row": source_row, "name": name, "name_key": norm(name), "qty": qty,
                "unit": unit, "exclusive": exclusive, "vat": row[4] if len(row) > 4 else None,
                "inclusive": row[5] if len(row) > 5 else None, "total": row[6] if len(row) > 6 else None,
                "section": current_section, "incomplete": True,
            })
        continue
    if exclusive is None:
        continue
    raw_rows.append({
        "source_row": source_row, "name": name, "name_key": norm(name), "qty": qty,
        "unit": unit, "exclusive": exclusive, "vat": row[4] if len(row) > 4 else None,
        "inclusive": row[5] if len(row) > 5 else None, "total": row[6] if len(row) > 6 else None,
        "section": current_section, "incomplete": False,
    })

by_key = defaultdict(list)
for row in raw_rows:
    by_key[row["name_key"]].append(row)

def catalog_type(row):
    name = norm(row["name"])
    if re.search(r"LABOUR|ALIGNMENT|BALANC|SKIMM|DIAGNOST|RE GRIND|REGRIND|TRANSPORT CHARGE", name):
        return "service"
    return "stock"

def audit_row(row, status, reason=""):
    ctype = catalog_type(row)
    stock = "0" if ctype == "service" else "1"
    normalized_uom = uom_map.get(norm(row["unit"]), row["unit"] or "")
    qualified_name = f"{VEHICLE_GROUP} - {row['name']}"
    item_code = f"ASM-{slug(VEHICLE_GROUP)}-{slug(row['name'])}"
    delta = ""
    inclusive = decimal_value(row["inclusive"])
    exclusive = decimal_value(row["exclusive"])
    vat = decimal_value(row["vat"])
    if inclusive is not None and exclusive is not None and vat is not None:
        delta = money(inclusive - exclusive - vat)
    return {
        "source_row": row["source_row"], "vehicle_group": VEHICLE_GROUP,
        "source_full_item_name": f"{VEHICLE_GROUP} {row['name']}", "source_item_name": row["name"],
        "system_category": row["section"], "source_item_group": "not supplied by workbook",
        "source_unit": row["unit"], "normalized_uom": normalized_uom, "item_code": item_code,
        "item_name": qualified_name, "catalog_type": ctype, "stock_item": stock,
        "source_qty": text(row["qty"]), "source_exclusive": money(row["exclusive"]) if row["exclusive"] is not None else "",
        "source_vat": money(row["vat"]) if row["vat"] is not None else "",
        "source_inclusive": money(row["inclusive"]) if row["inclusive"] is not None else "",
        "vat_arithmetic_delta": delta, "price_status": "ready" if status == "ready" else "not_imported",
        "status": status, "review_reason": reason, "dedup_key": row["name_key"],
        "source_section": row["section"],
    }

audit = []
ready = []
review_duplicates = []
review_incomplete = []
for row in raw_rows:
    if row["name_key"] in previous_keys:
        status, reason = "ignored_previous_package_duplicate", "same normalized source item name exists in previous catalog_audit.csv"
    elif row["incomplete"]:
        status, reason = "excluded_incomplete_missing_qty", "quantity is missing; confirm quantity before importing"
    elif len(by_key[row["name_key"]]) > 1:
        status, reason = "review_source_duplicate_conflict", "same normalized item name has multiple source variants/prices"
    else:
        status, reason = "ready", ""
    audit.append(audit_row(row, status, reason))
    if status == "ready":
        ready.append(row)
    elif status == "review_source_duplicate_conflict":
        review_duplicates.append({
            "vehicle_group": VEHICLE_GROUP, "item_name": row["name"],
            "full_item_name": f"{VEHICLE_GROUP} {row['name']}", "source_row": row["source_row"],
            "system_category": row["section"], "source_unit": row["unit"],
            "exclusive_price": money(row["exclusive"]), "vat": money(row["vat"]),
            "inclusive_price": money(row["inclusive"]),
            "conflict_type": "new source duplicate with conflicting prices",
            "recommended_action": "Choose the correct variant; if both are distinct, rename them before importing",
        })
    elif status == "excluded_incomplete_missing_qty":
        review_incomplete.append({
            "vehicle_group": VEHICLE_GROUP, "item_name": row["name"], "source_row": row["source_row"],
            "system_category": row["section"], "source_unit": row["unit"],
            "quantity": text(row["qty"]), "exclusive_price": money(row["exclusive"]),
            "vat": money(row["vat"]), "inclusive_price": money(row["inclusive"]),
            "issue": "Missing quantity; source total is zero",
            "recommended_action": "Confirm quantity and whether this is stock or service before importing",
        })

OUT.mkdir(parents=True, exist_ok=True)
write_csv(OUT / "01_uoms.csv", ["name", "uom_name", "must_be_whole_number"], [])
write_csv(OUT / "02_item_groups.csv", ["name", "item_group_name", "parent_item_group", "is_group"], [])

item_headers = ["name", "item_code", "item_name", "item_group", "stock_uom", "description", "is_stock_item", "is_sales_item", "is_purchase_item", "disabled"]
item_rows = []
for row in ready:
    ctype = catalog_type(row)
    normalized_uom = uom_map.get(norm(row["unit"]), row["unit"])
    item_group = "Services" if norm(row["section"]) == "SERVICE" else row["section"]
    item_rows.append({
        "name": "", "item_code": f"ASM-{slug(VEHICLE_GROUP)}-{slug(row['name'])}",
        "item_name": f"{VEHICLE_GROUP} - {row['name']}", "item_group": item_group,
        "stock_uom": normalized_uom,
        "description": f"Vehicle applicability: {VEHICLE_GROUP}; System category: {row['section']}; Source section: {row['section']}; Source unit: {row['unit']}",
        "is_stock_item": 0 if ctype == "service" else 1, "is_sales_item": 1,
        "is_purchase_item": 0 if ctype == "service" else 1, "disabled": 0,
    })
write_csv(OUT / "03_stock_items.csv", item_headers, [r for r in item_rows if r["is_stock_item"] == 1])
write_csv(OUT / "04_service_items.csv", item_headers, [r for r in item_rows if r["is_stock_item"] == 0])

price_headers = ["name", "item_code", "price_list", "price_list_rate", "uom", "currency", "selling", "buying", "note", "reference"]
price_rows = []
for row in ready:
    price_rows.append({
        "name": "", "item_code": f"ASM-{slug(VEHICLE_GROUP)}-{slug(row['name'])}",
        "price_list": "Standard Selling", "price_list_rate": money(row["exclusive"]),
        "uom": uom_map.get(norm(row["unit"]), row["unit"]), "currency": "UGX", "selling": 1, "buying": 0,
        "note": f"Source VAT: {money(row['vat'])}; source inclusive: {money(row['inclusive'])}; arithmetic delta: {money(Decimal(str(row['inclusive'])) - Decimal(str(row['exclusive'])) - Decimal(str(row['vat'])))}",
        "reference": "C:/Users/user/Downloads/YD25- NAVARA.xlsx",
    })
write_csv(OUT / "05_item_prices.csv", price_headers, price_rows)

audit_headers = list(audit[0].keys()) if audit else ["source_row"]
write_csv(OUT / "catalog_audit.csv", audit_headers, audit)
write_csv(OUT / "review_duplicate_items.csv", [
    "vehicle_group", "item_name", "full_item_name", "source_row", "system_category", "source_unit",
    "exclusive_price", "vat", "inclusive_price", "conflict_type", "recommended_action",
], review_duplicates)
write_csv(OUT / "review_incomplete_items.csv", [
    "vehicle_group", "item_name", "source_row", "system_category", "source_unit", "quantity",
    "exclusive_price", "vat", "inclusive_price", "issue", "recommended_action",
], review_incomplete)

source_hash = hashlib.sha256(SOURCE_XLSX.read_bytes()).hexdigest()
guide = f"""# Nissan Navara YD25 additions import guide

Prepared from `YD25- NAVARA.xlsx` as an additions-only package.

## Result

- New importable stock Items: {sum(1 for r in item_rows if r['is_stock_item'] == 1)}
- New importable service Items: {sum(1 for r in item_rows if r['is_stock_item'] == 0)}
- New Item Prices: {len(price_rows)}
- Rows ignored because they already exist in the previous package: {sum(1 for r in audit if r['status'] == 'ignored_previous_package_duplicate')}
- New source conflict rows held for review: {len(review_duplicates)}
- Incomplete rows held for review: {len(review_incomplete)}
- Source SHA-256: `{source_hash}`

## Import order

1. Do not re-import the previous package.
2. Skip `01_uoms.csv`, `02_item_groups.csv`, and `04_service_items.csv` if they contain only headers.
3. Import `03_stock_items.csv` as **Item** using **Insert New Records**.
4. Import `05_item_prices.csv` as **Item Price** using **Insert New Records**.
5. Do not import `review_duplicate_items.csv` or `review_incomplete_items.csv` until each row is manually resolved.
6. Keep `catalog_audit.csv` as the traceability file; it is not an import file.

## Important rules

- The item name includes the vehicle: `{VEHICLE_GROUP}`.
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
"""
(OUT / "IMPORT_GUIDE.md").write_text(guide, encoding="utf-8")

print(json.dumps({
    "output": str(OUT),
    "source_rows": len(raw_rows),
    "ready": len(ready),
    "ignored_previous": sum(1 for r in audit if r["status"] == "ignored_previous_package_duplicate"),
    "review_duplicates": len(review_duplicates),
    "review_incomplete": len(review_incomplete),
}, indent=2))
