from __future__ import annotations

import json

import frappe


def execute():
	_reconcile_diagnosis_status()
	_reconcile_service_docstatus()
	_backfill_service_bays()


def _has_column(table: str, column: str) -> bool:
	return bool(frappe.db.sql(f"SHOW COLUMNS FROM `tab{table}` LIKE %s", column))


def _reconcile_diagnosis_status():
	if not frappe.db.table_exists("Diagnosis Report") or not _has_column("Diagnosis Report", "status"):
		return

	unknown = frappe.db.sql(
		"""SELECT name, status FROM `tabDiagnosis Report`
		WHERE COALESCE(status, '') NOT IN ('', 'Draft', 'Submitted', 'Cancelled')""",
		as_dict=True,
	)
	if unknown:
		frappe.throw(f"Unknown Diagnosis Report statuses: {json.dumps(unknown, default=str)}")

	frappe.db.sql("UPDATE `tabDiagnosis Report` SET docstatus = 0 WHERE status IS NULL OR status = 'Draft'")
	frappe.db.sql("UPDATE `tabDiagnosis Report` SET docstatus = 1 WHERE status = 'Submitted'")
	frappe.db.sql("UPDATE `tabDiagnosis Report` SET docstatus = 2 WHERE status = 'Cancelled'")


def _reconcile_service_docstatus():
	if not frappe.db.table_exists("Repair Job Service"):
		return

	child_tables = (
		"Repair Job Service Part",
		"Repair Job Service Labour",
		"Repair Job Service Consumable",
		"Repair Job Service Subcontracted Service",
	)
	for child_table in child_tables:
		if frappe.db.table_exists(child_table):
			frappe.db.sql(
				f"""UPDATE `tab{child_table}` child
				JOIN `tabRepair Job Service` service ON service.name = child.parent
				SET child.docstatus = 0
				WHERE service.docstatus = 1"""
			)
	frappe.db.sql("UPDATE `tabRepair Job Service` SET docstatus = 0 WHERE docstatus = 1")


def _backfill_service_bays():
	if not frappe.db.table_exists("Repair Job") or not frappe.db.table_exists("Repair Job Service"):
		return
	if not _has_column("Repair Job", "workshop_bay") or not _has_column("Repair Job Service", "workshop_bay"):
		return

	frappe.db.sql(
		"""UPDATE `tabRepair Job Service` service
		JOIN `tabRepair Job` job ON job.name = service.repair_job
		SET service.workshop_bay = job.workshop_bay
		WHERE COALESCE(service.workshop_bay, '') = ''
		AND COALESCE(job.workshop_bay, '') <> ''"""
	)

