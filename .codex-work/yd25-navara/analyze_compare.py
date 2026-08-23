import csv
import json
import re
from collections import Counter, defaultdict

root = r"C:\Users\user\Documents\Coded\DMS"
source = r"C:\Users\user\Documents\Coded\DMS\.codex-work\yd25-navara\source_inspect.json"
previous_audit = root + r"\docs\import\parts-catalog\catalog_audit.csv"

def clean(value):
    return "" if value is None else str(value).strip()

def key(value):
    value = clean(value).upper()
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

payload = json.load(open(source, encoding="utf-8"))
values = payload["sheets"][0]["values"]
previous = list(csv.DictReader(open(previous_audit, encoding="utf-8-sig", newline="")))
previous_keys = {key(row.get("source_item_name")) for row in previous if clean(row.get("source_item_name"))}

sections = []
current_section = "Unclassified"
source_rows = []
for source_row, row in enumerate(values, start=1):
    name = clean(row[0] if len(row) > 0 else "")
    qty = row[1] if len(row) > 1 else None
    unit = clean(row[2] if len(row) > 2 else "")
    exclusive = row[3] if len(row) > 3 else None
    if not name and qty is None:
        continue
    if qty is None or not isinstance(qty, (int, float)):
        if name and name.upper() not in {"TOTAL PRICE", "PARTS LIST FOR NISSAN VEHICLES", "SYSTEM COMPONENTS"}:
            current_section = name.title()
            sections.append((source_row, current_section))
        continue
    if exclusive is None:
        continue
    source_rows.append({
        "source_row": source_row,
        "name": name,
        "name_key": key(name),
        "qty": qty,
        "unit": unit,
        "exclusive": exclusive,
        "vat": row[4] if len(row) > 4 else None,
        "inclusive": row[5] if len(row) > 5 else None,
        "total": row[6] if len(row) > 6 else None,
        "section": current_section,
    })

groups = defaultdict(list)
for row in source_rows:
    groups[row["name_key"]].append(row)

summary = {
    "source_candidate_rows": len(source_rows),
    "unique_source_names": len(groups),
    "previous_audit_rows": len(previous),
    "exact_normalized_overlap_rows": sum(1 for row in source_rows if row["name_key"] in previous_keys),
    "new_rows_by_exact_normalized_name": sum(1 for row in source_rows if row["name_key"] not in previous_keys),
    "overlap_names": sorted({row["name_key"] for row in source_rows if row["name_key"] in previous_keys}),
    "new_names": sorted({row["name"] for row in source_rows if row["name_key"] not in previous_keys}),
    "sections": sections,
    "within_source_duplicate_groups": [
        {"key": k, "count": len(v), "rows": [r["source_row"] for r in v], "names": [r["name"] for r in v]}
        for k, v in groups.items() if len(v) > 1
    ],
}
print(json.dumps(summary, indent=2, ensure_ascii=False))
