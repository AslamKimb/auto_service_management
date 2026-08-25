"""Validate spare-parts Item and Item Vehicle Fitment CSVs without database access.

The validator deliberately treats CSVs as untrusted import proposals.  It only
reads the input files and optionally writes a review CSV; it never imports,
updates, or connects to Frappe.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping


ITEM_REQUIRED = ("item_code", "item_name")
FITMENT_REQUIRED = ("item", "verification_status")
ALLOWED_STATUSES = {"provisional", "verified"}
INTERNAL_SKU_RE = re.compile(r"^(?:ASM|PROV)-[A-Z0-9][A-Z0-9_-]*$")
YEAR_MIN = 1886
YEAR_MAX = 2100


def _header_key(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")


def _text(value: object) -> str:
    value = unicodedata.normalize("NFKC", str(value or "")).strip()
    return re.sub(r"\s+", " ", value)


def _match_text(value: object) -> str:
    return _text(value).casefold()


def _identifier(value: object) -> str:
    """Normalize part numbers/barcodes while retaining a stable identity key."""

    return re.sub(r"[^A-Z0-9]", "", _text(value).upper())


def _sku(value: object) -> str:
    """Normalize an internal SKU without stripping its structural hyphens."""

    return re.sub(r"\s+", "", _text(value).upper())


def _read_csv(path: Path) -> tuple[list[dict[str, str]], dict[str, str], list[str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        raw_headers = list(reader.fieldnames or [])
        headers = {_header_key(header): header for header in raw_headers if header}
        rows = [{_header_key(key): _text(value) for key, value in row.items() if key} for row in reader]
    return rows, headers, raw_headers


def _get(row: Mapping[str, str], headers: Mapping[str, str], *aliases: str) -> str:
    for alias in aliases:
        key = _header_key(alias)
        if key in row:
            return _text(row[key])
    return ""


@dataclass(frozen=True)
class Issue:
    row_number: int
    entity: str
    code: str
    message: str
    severity: str = "ERROR"
    identity_key: str = ""


@dataclass
class ValidationReport:
    item_count: int = 0
    fitment_count: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "ERROR"]

    @property
    def warnings(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "WARNING"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def write_csv(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["severity", "entity", "row_number", "code", "identity_key", "message"],
            )
            writer.writeheader()
            for issue in self.issues:
                writer.writerow(
                    {
                        "severity": issue.severity,
                        "entity": issue.entity,
                        "row_number": issue.row_number,
                        "code": issue.code,
                        "identity_key": issue.identity_key,
                        "message": issue.message,
                    }
                )


def _required_columns(
    headers: Mapping[str, str], aliases: Mapping[str, tuple[str, ...]], required: Iterable[str], report: ValidationReport, entity: str
) -> None:
    for canonical in required:
        if not any(_header_key(alias) in headers for alias in aliases[canonical]):
            report.issues.append(
                Issue(0, entity, f"missing_{entity}_column", f"Required CSV column is missing: {canonical}")
            )


def _item_identity_keys(row: Mapping[str, str]) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    code = _identifier(row.get("item_code"))
    manufacturer = _identifier(row.get("manufacturer") or row.get("default_item_manufacturer"))
    barcode = _identifier(row.get("barcodes_barcode") or row.get("barcode"))
    if code:
        seen.add(f"item_code:{code}")
    for source_field in ("manufacturer_part_no", "oem_part_no", "default_manufacturer_part_no"):
        part_no = _identifier(row.get(source_field))
        if part_no:
            seen.add(f"{source_field}:{part_no}")
            if manufacturer:
                seen.add(f"{manufacturer}:{source_field}:{part_no}")
    if barcode:
        seen.add(f"barcode:{barcode}")
    keys.extend(sorted(seen))
    return keys


def _vehicle_reference(path: Path | None, report: ValidationReport) -> tuple[set[tuple[str, str]], set[str], dict[tuple[str, str], set[str]]]:
    if not path:
        report.issues.append(Issue(0, "vehicle_reference", "vehicle_reference_not_supplied", "No vehicle make/model reference CSV was supplied", "WARNING"))
        return set(), set(), {}
    rows, headers, _ = _read_csv(path)
    make_aliases = ("make", "vehicle_make")
    model_aliases = ("model", "vehicle_model")
    pairs: set[tuple[str, str]] = set()
    makes: set[str] = set()
    for row in rows:
        make = _match_text(_get(row, headers, *make_aliases))
        model = _match_text(_get(row, headers, *model_aliases))
        if make:
            makes.add(make)
        if make and model:
            pairs.add((make, model))
    return pairs, makes, {}


def _engine_reference(path: Path | None, report: ValidationReport) -> tuple[set[str], dict[tuple[str, str], set[str]]]:
    if not path:
        report.issues.append(Issue(0, "engine_reference", "engine_reference_not_supplied", "No engine reference CSV was supplied", "WARNING"))
        return set(), {}
    rows, headers, _ = _read_csv(path)
    engines: set[str] = set()
    by_vehicle: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        engine = _match_text(_get(row, headers, "engine_model", "engine", "name"))
        make = _match_text(_get(row, headers, "make", "vehicle_make"))
        model = _match_text(_get(row, headers, "model", "vehicle_model"))
        if engine:
            engines.add(engine)
            if make and model:
                by_vehicle[(make, model)].add(engine)
    return engines, by_vehicle


def validate_import(
    items_path: str | Path,
    fitments_path: str | Path,
    *,
    vehicle_reference: str | Path | None = None,
    engine_reference: str | Path | None = None,
) -> ValidationReport:
    """Return a review report for Item and fitment CSVs, with no DB side effects."""

    items_path = Path(items_path)
    fitments_path = Path(fitments_path)
    report = ValidationReport()
    items, item_headers, _ = _read_csv(items_path)
    fitments, fitment_headers, _ = _read_csv(fitments_path)
    report.item_count = len(items)
    report.fitment_count = len(fitments)

    item_aliases = {
        "item_code": ("item_code", "code"),
        "item_name": ("item_name", "item_name", "name"),
    }
    fitment_aliases = {
        "item": ("item", "item_code", "item_name"),
        "verification_status": ("verification_status", "status"),
    }
    _required_columns(item_headers, item_aliases, ITEM_REQUIRED, report, "item")
    _required_columns(fitment_headers, fitment_aliases, FITMENT_REQUIRED, report, "fitment")

    seen_identities: dict[str, int] = {}
    item_codes: set[str] = set()
    for index, row in enumerate(items, start=2):
        code = _text(row.get("item_code"))
        code_key = _identifier(code)
        if code_key:
            item_codes.add(code_key)
        if not _text(row.get("item_name")):
            report.issues.append(Issue(index, "item", "missing_item_name", "Item name is required"))
        if not code:
            report.issues.append(Issue(index, "item", "missing_identifier", "item_code is required even when an OEM number or barcode exists"))
        external_identifier = any(
            _identifier(row.get(field))
            for field in (
                "manufacturer_part_no",
                "oem_part_no",
                "default_manufacturer_part_no",
                "barcodes_barcode",
                "barcode",
            )
        )
        if not external_identifier and not INTERNAL_SKU_RE.fullmatch(_sku(code)):
            report.issues.append(Issue(index, "item", "invalid_internal_sku", "Rows without OEM/manufacturer part number or barcode must use an ASM-* or PROV-* item_code", identity_key=f"item_code:{code_key}"))
        for identity_key in _item_identity_keys(row):
            if identity_key in seen_identities:
                report.issues.append(Issue(index, "item", "duplicate_item_identity", f"Identity {identity_key} already appears on item row {seen_identities[identity_key]}", identity_key=identity_key))
            else:
                seen_identities[identity_key] = index

    vehicle_pairs, vehicle_makes, _ = _vehicle_reference(Path(vehicle_reference) if vehicle_reference else None, report)
    engines, engines_by_vehicle = _engine_reference(Path(engine_reference) if engine_reference else None, report)
    seen_fitments: dict[str, int] = {}
    for index, row in enumerate(fitments, start=2):
        item = _text(row.get("item") or row.get("item_code") or row.get("item_name"))
        item_key = _identifier(item)
        if not item_key or item_key not in item_codes:
            report.issues.append(Issue(index, "fitment", "missing_item_reference", f"Fitment item {item or '<blank>'!r} does not match an Item item_code"))
        make = _match_text(row.get("vehicle_make"))
        model = _match_text(row.get("vehicle_model"))
        engine = _match_text(row.get("vehicle_engine") or row.get("engine_model") or row.get("engine"))
        if model and not make:
            report.issues.append(Issue(index, "fitment", "invalid_vehicle_reference", "vehicle_model requires vehicle_make"))
        if vehicle_pairs:
            if make and model and (make, model) not in vehicle_pairs:
                report.issues.append(Issue(index, "fitment", "missing_vehicle_reference", f"Vehicle make/model is absent from the supplied reference: {make}/{model}"))
            elif make and not model and make not in vehicle_makes:
                report.issues.append(Issue(index, "fitment", "missing_vehicle_reference", f"Vehicle make is absent from the supplied reference: {make}"))
        if engines and engine:
            if engine not in engines:
                report.issues.append(Issue(index, "fitment", "missing_engine_reference", f"Engine model is absent from the supplied reference: {engine or '<blank>'}"))
            elif make and model and engines_by_vehicle.get((make, model)) and engine not in engines_by_vehicle[(make, model)]:
                report.issues.append(Issue(index, "fitment", "invalid_engine_vehicle_reference", f"Engine {engine} is not listed for {make}/{model}"))
        from_year = _text(row.get("year_from") or row.get("from_year"))
        to_year = _text(row.get("year_to") or row.get("to_year"))
        years: list[int] = []
        for label, raw in (("from_year", from_year), ("to_year", to_year)):
            if raw:
                try:
                    value = int(raw)
                except ValueError:
                    value = None
                if value is None or not YEAR_MIN <= value <= YEAR_MAX:
                    report.issues.append(Issue(index, "fitment", "invalid_year", f"{label} must be an integer between {YEAR_MIN} and {YEAR_MAX}: {raw!r}"))
                else:
                    years.append(value)
        if len(years) == 2 and years[0] > years[1]:
            report.issues.append(Issue(index, "fitment", "invalid_year_range", "from_year cannot be later than to_year"))
        status = _match_text(row.get("verification_status") or row.get("status"))
        if status not in ALLOWED_STATUSES:
            report.issues.append(Issue(index, "fitment", "invalid_status", "status must be Verified or Provisional"))
        fitment_key = "|".join((item_key, make, model, engine, from_year, to_year))
        if fitment_key in seen_fitments:
            report.issues.append(Issue(index, "fitment", "duplicate_fitment_key", f"Fitment key already appears on row {seen_fitments[fitment_key]}", identity_key=fitment_key))
        else:
            seen_fitments[fitment_key] = index
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", required=True, type=Path, help="Frappe Item import CSV")
    parser.add_argument("--fitments", required=True, type=Path, help="Item Vehicle Fitment import CSV")
    parser.add_argument("--vehicle-reference", type=Path, help="CSV with make/model (or vehicle_make/vehicle_model) reference rows")
    parser.add_argument("--engine-reference", type=Path, help="CSV with engine_model and optional make/model reference rows")
    parser.add_argument("--report", type=Path, required=True, help="Review CSV to write")
    args = parser.parse_args(argv)
    input_paths = {args.items.resolve(), args.fitments.resolve()}
    if args.vehicle_reference:
        input_paths.add(args.vehicle_reference.resolve())
    if args.engine_reference:
        input_paths.add(args.engine_reference.resolve())
    if args.report.resolve() in input_paths:
        print("--report must be a separate output file; refusing to overwrite an input CSV", file=sys.stderr)
        return 2
    try:
        report = validate_import(args.items, args.fitments, vehicle_reference=args.vehicle_reference, engine_reference=args.engine_reference)
    except (OSError, csv.Error) as exc:
        report = ValidationReport(issues=[Issue(0, "input", "input_read_error", str(exc))])
    report.write_csv(args.report)
    print(f"Items: {report.item_count}; fitments: {report.fitment_count}; errors: {len(report.errors)}; warnings: {len(report.warnings)}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
