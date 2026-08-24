from __future__ import annotations

import frappe

COMPONENT_CHILD_DOCTYPES = (
	"Repair Job Service Part",
	"Repair Job Service Consumable",
	"Repair Job Service Labour",
)


def execute():
	"""Give existing v16 component-table roles explicit select access for reports."""
	roles = ("Workshop Manager", "System Manager", "Service Advisor", "Parts Interpreter")
	for doctype in COMPONENT_CHILD_DOCTYPES:
		rows = frappe.get_all(
			"DocPerm",
			filters={"parent": doctype, "role": ["in", roles], "permlevel": 0},
			fields=["name", "select"],
			limit_page_length=0,
		)
		for row in rows:
			if not row.select:
				frappe.db.set_value("DocPerm", row.name, "select", 1, update_modified=False)
	frappe.clear_cache()
