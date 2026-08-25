import csv
import hashlib
import subprocess
import sys
from pathlib import Path

from scripts.validate_fitment_import import validate_import


ROOT = Path(__file__).resolve().parents[1]


def write_csv(path: Path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


ITEM_HEADERS = [
    "name",
    "item_code",
    "item_name",
    "item_group",
    "stock_uom",
    "description",
    "is_stock_item",
    "is_sales_item",
    "is_purchase_item",
    "disabled",
    "manufacturer",
    "manufacturer_part_no",
    "oem_part_no",
    "barcodes.barcode",
]
FITMENT_HEADERS = [
    "name",
    "item",
    "vehicle_make",
    "vehicle_model",
    "vehicle_engine",
    "year_from",
    "year_to",
    "verification_status",
    "notes",
    "source",
]


def test_accepts_mixed_identifiers_and_exact_fitment_references(tmp_path):
    items = tmp_path / "items.csv"
    fitments = tmp_path / "fitments.csv"
    references = tmp_path / "vehicles.csv"
    engines = tmp_path / "engines.csv"
    write_csv(
        items,
        ITEM_HEADERS,
        [
            {
                "name": "",
                "item_code": "ASM-OEM-001",
                "item_name": "Oil filter",
                "item_group": "Auto Parts",
                "stock_uom": "PCS",
                "description": "",
                "is_stock_item": "1",
                "is_sales_item": "1",
                "is_purchase_item": "1",
                "disabled": "0",
                "manufacturer": "Nissan",
                "manufacturer_part_no": "15208-65F0A",
                "oem_part_no": "OEM-15208-65F0A",
                "barcodes.barcode": "",
            },
            {
                "name": "",
                "item_code": "PROV-FILTER-002",
                "item_name": "Air filter",
                "item_group": "Auto Parts",
                "stock_uom": "PCS",
                "description": "",
                "is_stock_item": "1",
                "is_sales_item": "1",
                "is_purchase_item": "1",
                "disabled": "0",
                "manufacturer": "",
                "manufacturer_part_no": "",
                "oem_part_no": "",
                "barcodes.barcode": "8901234567890",
            },
        ],
    )
    write_csv(
        fitments,
        FITMENT_HEADERS,
        [
            {
                "name": "",
                "item": "ASM-OEM-001",
                "vehicle_make": "Nissan",
                "vehicle_model": "Navara",
                "vehicle_engine": "YD25",
                "year_from": "2005",
                "year_to": "2015",
                "verification_status": "Verified",
                "notes": "",
                "source": "OEM catalogue",
            },
            {
                "name": "",
                "item": "PROV-FILTER-002",
                "vehicle_make": "",
                "vehicle_model": "",
                "vehicle_engine": "",
                "year_from": "",
                "year_to": "",
                "verification_status": "Provisional",
                "notes": "Universal until checked",
                "source": "Counter reference",
            },
        ],
    )
    write_csv(references, ["make", "model"], [{"make": "Nissan", "model": "Navara"}])
    write_csv(engines, ["make", "model", "engine_model"], [{"make": "Nissan", "model": "Navara", "engine_model": "YD25"}])

    result = validate_import(items, fitments, vehicle_reference=references, engine_reference=engines)

    assert result.ok
    assert result.item_count == 2
    assert result.fitment_count == 2
    assert not result.issues


def test_accepts_controlled_asm_and_prov_fallback_codes_without_external_ids(tmp_path):
    items = tmp_path / "items.csv"
    fitments = tmp_path / "fitments.csv"
    rows = []
    for code, name in (("ASM-NAVARA-OIL-FILTER-001", "Oil filter"), ("PROV-NAVARA-AIR-FILTER-002", "Air filter")):
        row = {h: "" for h in ITEM_HEADERS}
        row.update({"item_code": code, "item_name": name})
        rows.append(row)
    write_csv(items, ITEM_HEADERS, rows)
    write_csv(fitments, FITMENT_HEADERS, [])

    result = validate_import(items, fitments)

    assert result.ok
    assert "invalid_internal_sku" not in {issue.code for issue in result.issues}


def test_checks_manufacturer_and_oem_part_numbers_independently(tmp_path):
    items = tmp_path / "items.csv"
    fitments = tmp_path / "fitments.csv"
    rows = []
    for code, manufacturer_part_no, oem_part_no in (
        ("ASM-MFR-001", "MFR-001", "OEM-001"),
        ("ASM-MFR-002", "MFR-001", "OEM-002"),
        ("ASM-OEM-003", "", "OEM-003"),
        ("ASM-OEM-004", "", "OEM-003"),
    ):
        row = {h: "" for h in ITEM_HEADERS}
        row.update({"item_code": code, "item_name": code, "manufacturer_part_no": manufacturer_part_no, "oem_part_no": oem_part_no})
        rows.append(row)
    write_csv(items, ITEM_HEADERS, rows)
    write_csv(fitments, FITMENT_HEADERS, [])

    result = validate_import(items, fitments)
    duplicates = [issue for issue in result.issues if issue.code == "duplicate_item_identity"]

    assert {issue.identity_key for issue in duplicates} == {
        "manufacturer_part_no:MFR001",
        "oem_part_no:OEM003",
    }


def test_fitment_template_uses_current_doctype_field_names():
    template = ROOT / "docs" / "import" / "parts-catalog" / "fitment" / "02_item_vehicle_fitment.csv"
    with template.open(newline="", encoding="utf-8-sig") as handle:
        assert next(csv.reader(handle)) == FITMENT_HEADERS


def test_item_template_uses_native_erpnext_item_fields():
    template = ROOT / "docs" / "import" / "parts-catalog" / "fitment" / "01_items.csv"
    with template.open(newline="", encoding="utf-8-sig") as handle:
        headers = next(csv.reader(handle))
    assert "default_item_manufacturer" in headers
    assert "default_manufacturer_part_no" in headers
    assert "manufacturer" not in headers
    assert "oem_part_no" not in headers


def test_reports_duplicate_identity_and_fitment_key(tmp_path):
    items = tmp_path / "items.csv"
    fitments = tmp_path / "fitments.csv"
    write_csv(
        items,
        ITEM_HEADERS,
        [
            {h: ("ASM-ONE" if h == "item_code" else "890123" if h == "barcodes.barcode" else "Part" if h == "item_name" else "") for h in ITEM_HEADERS},
            {h: ("ASM-TWO" if h == "item_code" else "890123" if h == "barcodes.barcode" else "Part copy" if h == "item_name" else "") for h in ITEM_HEADERS},
        ],
    )
    fitment = {h: "" for h in FITMENT_HEADERS}
    fitment.update({"item": "ASM-ONE", "vehicle_make": "Nissan", "vehicle_model": "Navara", "verification_status": "Verified"})
    write_csv(fitments, FITMENT_HEADERS, [fitment, dict(fitment)])

    result = validate_import(items, fitments)
    codes = {issue.code for issue in result.issues}

    assert "duplicate_item_identity" in codes
    assert "duplicate_fitment_key" in codes
    assert not result.ok


def test_reports_missing_references_invalid_year_status_and_item(tmp_path):
    items = tmp_path / "items.csv"
    fitments = tmp_path / "fitments.csv"
    vehicles = tmp_path / "vehicles.csv"
    engines = tmp_path / "engines.csv"
    row = {h: "" for h in ITEM_HEADERS}
    row.update({"item_code": "PROV-ONE", "item_name": "Part"})
    write_csv(items, ITEM_HEADERS, [row])
    fitment = {h: "" for h in FITMENT_HEADERS}
    fitment.update({"item": "DOES-NOT-EXIST", "vehicle_make": "Toyota", "vehicle_model": "Hilux", "vehicle_engine": "BAD", "year_from": "2020", "year_to": "2010", "verification_status": "Draft"})
    write_csv(fitments, FITMENT_HEADERS, [fitment])
    write_csv(vehicles, ["make", "model"], [{"make": "Nissan", "model": "Navara"}])
    write_csv(engines, ["make", "model", "engine_model"], [{"make": "Nissan", "model": "Navara", "engine_model": "YD25"}])

    result = validate_import(items, fitments, vehicle_reference=vehicles, engine_reference=engines)
    codes = {issue.code for issue in result.issues}

    assert {"missing_item_reference", "missing_vehicle_reference", "missing_engine_reference", "invalid_year_range", "invalid_status"} <= codes


def test_cli_writes_review_report_without_changing_inputs(tmp_path):
    items = tmp_path / "items.csv"
    fitments = tmp_path / "fitments.csv"
    report = tmp_path / "review.csv"
    item = {h: "" for h in ITEM_HEADERS}
    item.update({"item_code": "not-controlled", "item_name": "Part"})
    write_csv(items, ITEM_HEADERS, [item])
    write_csv(fitments, FITMENT_HEADERS, [])
    before = hashlib.sha256(items.read_bytes()).hexdigest()

    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_fitment_import.py"), "--items", str(items), "--fitments", str(fitments), "--report", str(report)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert report.exists()
    assert hashlib.sha256(items.read_bytes()).hexdigest() == before
    with report.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert any(row["code"] == "invalid_internal_sku" for row in rows)
