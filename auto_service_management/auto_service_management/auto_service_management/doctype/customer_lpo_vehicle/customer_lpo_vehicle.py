# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document


def normalize_registration_number(value: str | None) -> str:
	"""Return a stable registration key for duplicate and matching checks."""
	return re.sub(r"[^A-Za-z0-9]", "", str(value or "")).upper()


class CustomerLPOVehicle(Document):
	def validate(self):
		self.registration_number = normalize_registration_number(self.registration_number)
		if not self.registration_number:
			frappe.throw(_("Registration Number is required."))
