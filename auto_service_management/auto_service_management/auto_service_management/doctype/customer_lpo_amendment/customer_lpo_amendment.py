# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from datetime import date
from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class CustomerLPOAmendment(Document):
	def validate(self):
		self.validate_identity()
		self.validate_lpo_state()
		self.validate_amount_or_expiry()
		self.validate_dates()
		self.validate_replacement_expiry()

	def before_submit(self):
		self.validate()
		if not self.source_attachment:
			frappe.throw(_("A source attachment is required before submitting a Customer LPO Amendment."))
		if not self.reason:
			frappe.throw(_("A reason is required before submitting a Customer LPO Amendment."))

	def on_submit(self):
		self._refresh_lpo_status()

	def on_cancel(self):
		self.validate_cancellation_safety()
		self._refresh_lpo_status()

	def validate_identity(self):
		missing = [
			field for field in ("customer_lpo", "external_reference", "issue_date") if not self.get(field)
		]
		if missing:
			frappe.throw(_("Customer LPO Amendment requires: {0}.").format(", ".join(missing)))

	def validate_lpo_state(self):
		lpo = frappe.db.get_value("Customer LPO", self.customer_lpo, ["docstatus", "status"], as_dict=True)
		if not lpo:
			frappe.throw(_("Customer LPO {0} does not exist.").format(self.customer_lpo))
		if lpo.docstatus != 1:
			frappe.throw(
				_("Customer LPO {0} must be submitted before it can be amended.").format(self.customer_lpo)
			)
		if lpo.status == "Cancelled":
			frappe.throw(_("Cancelled Customer LPOs cannot be amended."))

	def validate_cancellation_safety(self):
		if self.docstatus not in {1, 2} or not self.customer_lpo:
			return
		from auto_service_management.auto_service_management.integration.customer_lpo_workflow import (
			get_lpo_invoice_amount,
		)

		lpo = frappe.get_doc("Customer LPO", self.customer_lpo)
		remaining_authority = lpo.get_effective_authorized_amount() - _to_decimal(self.amount_increase)
		invoiced = 0
		for invoice in frappe.get_all(
			"Sales Invoice",
			filters={"customer_lpo": lpo.name, "docstatus": 1},
			fields=["net_total", "grand_total", "rounded_total", "disable_rounded_total"],
			limit_page_length=0,
		):
			invoiced += get_lpo_invoice_amount(invoice, lpo.ceiling_basis)
		if invoiced > remaining_authority + Decimal("0.0001"):
			frappe.throw(
				_(
					"Amendment {0} cannot be cancelled because submitted invoices exceed the resulting LPO authority."
				).format(self.name)
			)

	def _refresh_lpo_status(self):
		if not self.customer_lpo:
			return
		lpo = frappe.get_doc("Customer LPO", self.customer_lpo)
		lpo.save(ignore_permissions=True)

	def validate_amount_or_expiry(self):
		amount = _to_decimal(self.amount_increase)
		if amount < 0:
			frappe.throw(_("Amount Increase cannot be negative."))
		if amount == 0 and not self.replacement_expiry:
			frappe.throw(_("An amendment must increase the amount or extend the expiry date."))

	def validate_dates(self):
		if self.issue_date and self.replacement_expiry:
			if getdate(self.replacement_expiry) <= getdate(self.issue_date):
				frappe.throw(_("Replacement Expiry must be after Issue Date."))

	def validate_replacement_expiry(self):
		if not self.replacement_expiry or not self.customer_lpo:
			return
		current_expiry = frappe.db.get_value("Customer LPO", self.customer_lpo, "expiry_date")
		if current_expiry and getdate(self.replacement_expiry) <= getdate(current_expiry):
			frappe.throw(_("Replacement Expiry must extend the current Customer LPO expiry date."))


def _to_decimal(value) -> Decimal:
	try:
		return Decimal(str(value or 0))
	except (InvalidOperation, TypeError, ValueError):
		frappe.throw(_("Amount Increase must be a valid number."))
		return Decimal("0")
