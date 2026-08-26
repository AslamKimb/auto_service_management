# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from auto_service_management.auto_service_management.settings_cache import clear_settings_cache


class AutoServiceSettings(Document):
	def on_update(self):
		clear_settings_cache()

	def on_trash(self):
		clear_settings_cache()
