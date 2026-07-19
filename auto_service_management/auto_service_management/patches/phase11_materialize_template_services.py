from __future__ import annotations

import frappe


def execute():
	_materialize_template_services()


def _materialize_template_services():
	if not frappe.db.table_exists("Repair Job Service"):
		return

	for service_row in frappe.get_all(
		"Repair Job Service",
		fields=["name", "repair_service_template"],
		order_by="creation asc",
		limit_page_length=0,
	):
		if not service_row.repair_service_template:
			continue

		service = frappe.get_doc("Repair Job Service", service_row.name)
		if service.materialize_template_components():
			service.save(ignore_permissions=True)
