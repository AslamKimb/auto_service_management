import frappe


def execute():
	if not frappe.db.table_exists("Gate Pass") or not frappe.db.has_column("Gate Pass", "purpose"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabGate Pass`
		SET purpose = 'Final Release'
		WHERE purpose IS NULL OR purpose = ''
		"""
	)
