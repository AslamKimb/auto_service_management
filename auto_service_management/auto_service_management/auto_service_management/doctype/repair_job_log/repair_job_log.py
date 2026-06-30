# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class RepairJobLog(Document):
	"""Immutable audit log. No writes or deletes allowed after insert."""

	def validate(self):
		# Prevent modifications to existing log entries
		if not self.is_new():
			frappe.throw(_("Repair Job Log entries are immutable and cannot be modified."))

	def on_trash(self):
		frappe.throw(_("Repair Job Log entries are immutable and cannot be deleted."))
