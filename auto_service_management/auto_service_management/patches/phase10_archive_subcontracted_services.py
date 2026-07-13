import frappe

LEGACY_TABLES = (
	("Repair Job Service Subcontracted Service", "legacy_subcontracted_services"),
	("Repair Service Template Subcontracted Service", "legacy_subcontracted_services"),
)


def execute():
	"""Move active subcontract child rows under their hidden legacy table fields."""
	for child_doctype, legacy_fieldname in LEGACY_TABLES:
		if not frappe.db.table_exists(child_doctype):
			continue
		for row_name in frappe.get_all(
			child_doctype,
			filters={"parentfield": ["!=", legacy_fieldname]},
			pluck="name",
		):
			frappe.db.set_value(
				child_doctype,
				row_name,
				"parentfield",
				legacy_fieldname,
				update_modified=False,
			)
