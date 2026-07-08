# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document


class GatePass(Document):
	def validate(self):
		self.sync_with_repair_job()
		self.validate_invoice_submitted()
		self.validate_unique_for_repair_job()

	def on_update(self):
		self.sync_primary_link()

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

	def sync_with_repair_job(self):
		if not self.repair_job:
			return

		job = frappe.get_doc("Repair Job", self.repair_job)
		if not self.customer_vehicle:
			self.customer_vehicle = job.customer_vehicle
		elif self.customer_vehicle != job.customer_vehicle:
			frappe.throw(_("Gate Pass vehicle must match the linked Repair Job vehicle."))

		if not self.sales_invoice:
			self.sales_invoice = job.sales_invoice

	def validate_unique_for_repair_job(self):
		if not self.repair_job:
			return

		existing = frappe.db.get_value(
			"Gate Pass",
			{"repair_job": self.repair_job, "name": ["!=", self.name or ""]},
			"name",
		)
		if existing:
			frappe.throw(_("Repair Job {0} already has Gate Pass {1}.").format(self.repair_job, existing))

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
		if self.repair_job:
			job = frappe.get_doc("Repair Job", self.repair_job)
			job.gate_pass = self.name
			if job.job_status != "Gate Pass Issued":
				job.job_status = "Gate Pass Issued"
			job.flags.ignore_links = True
			job.save(ignore_permissions=True)

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

	def sync_primary_link(self):
		if not self.repair_job or not frappe.db.exists("Repair Job", self.repair_job):
			return

		job = frappe.get_doc("Repair Job", self.repair_job)
		if job.gate_pass == self.name:
			return

		job.gate_pass = self.name
		job.flags.ignore_links = True
		job.save(ignore_permissions=True)
