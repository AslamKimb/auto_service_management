import frappe


def execute():
	"""Ensure all required app roles exist and DocType naming rules are set."""
	roles = [
		"Auto Service Admin",
		"Cashier",
		"Parts Interpreter",
		"Security Gate Officer",
		"Service Advisor",
		"Workshop Manager",
		"Workshop Technician",
	]
	for role_name in roles:
		if not frappe.db.exists("Role", role_name):
			doc = frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": role_name,
					"desk_access": 1,
					"is_custom": 0,
				}
			)
			doc.insert(ignore_permissions=True)
			frappe.db.commit()

	# Normalize format-based autoname definitions for fresh installs and upgrades.
	# Frappe v16 resolves `format:` names through braced tokens and should not have
	# an explicit naming_rule set on these DocTypes.
	naming_fixes = [
		("Repair Job", "format:RJ-{YYYY}-{#####}"),
		("Walkaround Inspection", "format:WI-{YYYY}-{#####}"),
		("Customer Authorization", "format:CA-{YYYY}-{#####}"),
		("Diagnosis Report", "format:DR-{YYYY}-{#####}"),
		("Fleet Service Campaign", "format:FSC-{YYYY}-{#####}"),
		("Quality Check", "format:QC-{YYYY}-{#####}"),
		("Gate Pass", "format:GP-{YYYY}-{#####}"),
		("Repair Job Override", "format:RJO-{YYYY}-{#####}"),
		("Road Test Report", "format:RT-{YYYY}-{#####}"),
		("Service History", "format:SH-{YYYY}-{#####}"),
	]
	for dt_name, autoname_fmt in naming_fixes:
		frappe.db.sql(
			"UPDATE tabDocType SET naming_rule = NULL, autoname = %s WHERE name = %s",
			(autoname_fmt, dt_name),
		)
	frappe.db.commit()
