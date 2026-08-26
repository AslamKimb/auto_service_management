from __future__ import annotations

import json
from pathlib import Path

import frappe
from frappe import _
from frappe.utils import flt

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	get_repair_job_services,
)
from auto_service_management.auto_service_management.workflow_compatibility import (
	build_repair_job_invoice_rows,
	build_repair_job_payment_rows,
	build_repair_job_service_workshop_bay_rows,
)

RELEASE_A_PATCH = "auto_service_management.patches.phase11_materialize_template_services"


def execute():
	issues = _collect_release_a_safety_issues()
	if issues:
		frappe.throw(_("RWF-040 blocked migration: {0}").format(json.dumps(issues, sort_keys=True)))


def _collect_release_a_safety_issues() -> list[dict]:
	issues = []
	patch_issue = _patch_log_issue()
	if patch_issue:
		issues.append(patch_issue)
	if not frappe.db.table_exists("Repair Job"):
		return issues

	issues.extend(_road_test_issues())
	issues.extend(_template_reference_issues())
	issues.extend(_workshop_bay_issues())
	issues.extend(_financial_issues())
	return issues


def _patch_log_issue() -> dict | None:
	patch_log = Path(__file__).resolve().parents[1] / "patches.txt"
	if RELEASE_A_PATCH in patch_log.read_text(encoding="utf-8"):
		return None
	return {
		"check": "patch_log",
		"reason": "Release A patch is missing from the Patch Log.",
		"patch": RELEASE_A_PATCH,
	}


def _road_test_issues() -> list[dict]:
	if not frappe.db.exists("DocType", "Road Test Report"):
		return []
	if not frappe.db.table_exists("Road Test Report"):
		return []
	count = len(frappe.get_all("Road Test Report", pluck="name", limit_page_length=0))
	if not count:
		return []
	return [
		{
			"check": "road_test_reports",
			"count": count,
			"reason": "Standalone Road Test Report rows still exist.",
		}
	]


def _template_reference_issues() -> list[dict]:
	if not frappe.db.table_exists("Repair Job Service"):
		return []
	issues = []
	for row in frappe.get_all(
		"Repair Job Service",
		fields=["name", "repair_job", "repair_service_template"],
		limit_page_length=0,
		order_by="creation asc, name asc",
	):
		if not getattr(row, "repair_service_template", None):
			continue
		issues.append(
			{
				"check": "template_references",
				"repair_job": getattr(row, "repair_job", None),
				"repair_job_service": getattr(row, "name", None),
				"template": getattr(row, "repair_service_template", None),
				"reason": "Legacy Repair Service Template references still exist.",
			}
		)
	return issues


def _workshop_bay_issues() -> list[dict]:
	issues = []
	if not frappe.db.table_exists("Repair Job Service"):
		return issues
	for repair_job_name in frappe.get_all(
		"Repair Job", pluck="name", order_by="creation asc, name asc", limit_page_length=0
	):
		_, job_issues = build_repair_job_service_workshop_bay_rows(repair_job_name)
		issues.extend({"check": "workshop_bay", **issue} for issue in job_issues)
	return issues


def _financial_issues() -> list[dict]:
	issues = []
	for repair_job_name in frappe.get_all(
		"Repair Job", pluck="name", order_by="creation asc, name asc", limit_page_length=0
	):
		job = frappe.get_doc("Repair Job", repair_job_name)
		invoice_rows = build_repair_job_invoice_rows(repair_job_name)
		payment_rows = build_repair_job_payment_rows(repair_job_name)

		service_total = _active_service_total(repair_job_name)
		invoice_total = _sum_rows(invoice_rows, "grand_total")
		payment_total = _sum_rows(payment_rows, "allocated_amount")

		if _money(getattr(job, "total_amount", 0)) != _money(service_total):
			issues.append(
				{
					"check": "service_totals",
					"repair_job": repair_job_name,
					"stored": _money(getattr(job, "total_amount", 0)),
					"expected": _money(service_total),
					"reason": "Repair Job total amount does not match the service rows.",
				}
			)
		if _money(getattr(job, "payment_total", 0)) != _money(payment_total):
			issues.append(
				{
					"check": "payment_totals",
					"repair_job": repair_job_name,
					"stored": _money(getattr(job, "payment_total", 0)),
					"expected": _money(payment_total),
					"reason": "Repair Job payment total does not match the payment entries.",
				}
			)
		expected_payment_status = _derive_payment_status(invoice_total, payment_total)
		if (getattr(job, "payment_status", None) or "Not Invoiced") != expected_payment_status:
			issues.append(
				{
					"check": "payment_status",
					"repair_job": repair_job_name,
					"stored": getattr(job, "payment_status", None) or "Not Invoiced",
					"expected": expected_payment_status,
					"reason": "Repair Job payment status does not match the invoice and payment totals.",
				}
			)
	return issues


def _sum_rows(rows: list[dict], fieldname: str) -> float:
	return sum(flt(row.get(fieldname)) for row in rows)


def _money(value) -> float:
	return round(flt(value), 2)


def _active_service_total(repair_job_name: str) -> float:
	total = 0.0
	for service in get_repair_job_services(repair_job_name):
		if getattr(service, "docstatus", 0) == 2:
			continue
		total += flt(getattr(service, "total_amount", 0))
	return total


def _derive_payment_status(invoice_total: float, payment_total: float) -> str:
	if invoice_total <= 0:
		return "Not Invoiced"
	if payment_total <= 0:
		return "Unpaid"
	if payment_total < invoice_total:
		return "Partially Paid"
	return "Paid"
