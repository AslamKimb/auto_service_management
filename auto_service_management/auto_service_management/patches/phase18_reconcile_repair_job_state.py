from __future__ import annotations

import frappe

from auto_service_management.auto_service_management.workflow_compatibility import (
	_derive_repair_job_status,
)


def execute():
	if not frappe.db.table_exists("Repair Job"):
		return

	for name in frappe.get_all("Repair Job", pluck="name", order_by="creation asc, name asc", limit_page_length=0):
		job = frappe.get_doc("Repair Job", name)
		job_status = _derive_repair_job_status(job) or "Draft"
		if job_status != job.job_status and job_status != "Closed":
			frappe.db.set_value("Repair Job", name, "job_status", job_status, update_modified=False)
		if frappe.db.has_column("Repair Job", "workflow_state"):
			frappe.db.set_value("Repair Job", name, "workflow_state", job_status, update_modified=False)
