# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document

from auto_service_management.auto_service_management.workflow_compatibility import recompute_repair_job_state


class GatePass(Document):
	def validate(self):
		self.purpose = self.purpose or "Final Release"
		self.sync_with_repair_job()
		self.validate_invoice_submitted()
		self.validate_unique_for_repair_job()

	def on_update(self):
		self.sync_primary_link()
		if self.repair_job and self.purpose == "Final Release":
			recompute_repair_job_state(self.repair_job)

	def _require_write_permission(self):
		self.check_permission("write")

	def validate_invoice_submitted(self):
		"""Gate pass requires complete submitted component-level billing."""
		if self.purpose == "Road Test":
			return
		if self.repair_job:
			from auto_service_management.auto_service_management.integration.erpnext.document_sync import (
				validate_job_invoices_for_gate_pass,
			)

			invoices = validate_job_invoices_for_gate_pass(self.repair_job)
			if not self.sales_invoice:
				self.sales_invoice = invoices[0]

	def sync_with_repair_job(self):
		if not self.repair_job:
			return

		job = frappe.get_doc("Repair Job", self.repair_job)
		if not self.customer_vehicle:
			self.customer_vehicle = job.customer_vehicle
		elif self.customer_vehicle != job.customer_vehicle:
			frappe.throw(_("Gate Pass vehicle must match the linked Repair Job vehicle."))

		if self.purpose == "Final Release" and not self.sales_invoice:
			from auto_service_management.auto_service_management.integration.erpnext.document_sync import (
				get_repair_job_sales_invoices,
			)

			invoices = get_repair_job_sales_invoices(self.repair_job, submitted_only=True)
			self.sales_invoice = invoices[0] if invoices else None

	def validate_unique_for_repair_job(self):
		if not self.repair_job:
			return

		existing = frappe.db.get_value(
			"Gate Pass",
			{
				"repair_job": self.repair_job,
				"purpose": self.purpose or "Final Release",
				"status": ["in", ["Pending", "Issued"]],
				"name": ["!=", self.name or ""],
			},
			"name",
		)
		if existing:
			frappe.throw(
				_("Repair Job {0} already has active {1} Gate Pass {2}.").format(
					self.repair_job,
					self.purpose,
					existing,
				)
			)

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
		if self.repair_job and self.purpose == "Final Release":
			job = frappe.get_doc("Repair Job", self.repair_job)
			job.gate_pass = self.name
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

	@frappe.whitelist()
	def mark_returned(self):
		self._require_write_permission()
		if self.purpose != "Road Test":
			frappe.throw(_("Only Road Test gate passes can be marked as returned."))
		if self.status not in {"Issued", "Used"}:
			frappe.throw(_("Only issued or used road-test gate passes can be marked as returned."))
		self.status = "Returned"
		self.returned_by = frappe.session.user
		self.returned_on = datetime.now()
		self.save()

	def sync_primary_link(self):
		if (
			self.purpose != "Final Release"
			or not self.repair_job
			or not frappe.db.exists("Repair Job", self.repair_job)
		):
			return

		job = frappe.get_doc("Repair Job", self.repair_job)
		if job.gate_pass == self.name:
			return

		job.gate_pass = self.name
		job.flags.ignore_links = True
		job.save(ignore_permissions=True)
