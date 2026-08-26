from __future__ import annotations

import json

import frappe

from auto_service_management.auto_service_management.workflow_compatibility import (
	build_repair_job_service_workshop_bay_rows,
)


def execute():
	_backfill_workshop_bays()


def _backfill_workshop_bays():
	if not frappe.db.table_exists("Repair Job"):
		return
	if not frappe.db.table_exists("Repair Job Service"):
		return

	exceptions = []
	for repair_job_name in frappe.get_all(
		"Repair Job", pluck="name", order_by="creation asc", limit_page_length=0
	):
		rows, job_exceptions = build_repair_job_service_workshop_bay_rows(repair_job_name)
		exceptions.extend(job_exceptions)
		for row in rows:
			service = frappe.get_doc("Repair Job Service", row["repair_job_service"])
			service.workshop_bay = row["workshop_bay"]
			service.save(ignore_permissions=True)

	if exceptions:
		frappe.logger("auto_service_management").warning(
			"RWF-021 workshop bay exceptions: %s",
			json.dumps(exceptions, sort_keys=True),
		)
