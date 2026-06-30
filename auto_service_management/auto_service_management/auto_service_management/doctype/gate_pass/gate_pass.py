# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document


class GatePass(Document):
	def validate(self):
		self.validate_invoice_submitted()

	def _require_write_permission(self):
		self.check_permission("write")

	def validate_invoice_submitted(self):
		"""Gate pass requires a submitted invoice."""
		if self.repair_job:
			invoice = frappe.db.get_value("Repair Job", self.repair_job, "sales_invoice")
			if not invoice:
				frappe.throw(_("A Sales Invoice must be created before issuing a Gate Pass."))
			invoice_status = frappe.db.get_value("Sales Invoice", invoice, "docstatus")
			if invoice_status != 1:
				frappe.throw(_("The linked Sales Invoice must be submitted before issuing a Gate Pass."))

	@frappe.whitelist()
	def issue(self):
		"""Issue the gate pass — called by workshop staff."""
		self._require_write_permission()
		if self.status != "Pending":
			frappe.throw(_("Only pending gate passes can be issued."))
		self.status = "Issued"
		self.issued_by = frappe.session.user
		self.issue_date = datetime.now()
		self.save()
		# Update Repair Job
		frappe.db.set_value(
			"Repair Job",
			self.repair_job,
			{"gate_pass_issued": 1, "gate_pass_number": self.name},
		)

	@frappe.whitelist()
	def use_gate_pass(self):
		"""Mark gate pass as used — called by security."""
		self._require_write_permission()
		if self.status != "Issued":
			frappe.throw(_("Only issued gate passes can be marked as used."))
		self.status = "Used"
		self.used_by = frappe.session.user
		self.use_date = datetime.now()
		self.save()
