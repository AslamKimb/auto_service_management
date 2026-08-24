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
		self.validate_amount_or_expiry()
		self.validate_dates()
		self.validate_replacement_expiry()

	def before_submit(self):
		self.validate()
		if not self.source_attachment:
			frappe.throw(_("A source attachment is required before submitting a Customer LPO Amendment."))
		if not self.reason:
			frappe.throw(_("A reason is required before submitting a Customer LPO Amendment."))

	def validate_identity(self):
		missing = [
			field
			for field in ("customer_lpo", "external_reference", "issue_date")
			if not self.get(field)
		]
		if missing:
			frappe.throw(_("Customer LPO Amendment requires: {0}.").format(", ".join(missing)))

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
