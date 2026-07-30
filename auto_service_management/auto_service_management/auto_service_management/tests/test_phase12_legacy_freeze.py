# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import unittest
from pathlib import Path

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	RepairJobService,
)

MODULE_ROOT = Path(__file__).parents[1]


class _FreezeProbe:
	def __init__(self, *, is_new):
		self._is_new = is_new

	def is_new(self):
		return self._is_new

	def has_value_changed(self, fieldname):
		return False


class TestLegacyFreeze(unittest.TestCase):
	def test_repair_job_ui_no_longer_creates_road_test_reports(self):
		js_path = MODULE_ROOT / "doctype" / "repair_job" / "repair_job.js"
		source = js_path.read_text(encoding="utf-8")

		self.assertNotIn("Create Road Test Report", source)
		self.assertNotIn('new_doc("Road Test Report"', source)
		self.assertNotIn("road_test_report", source.split("add_related_document_button(frm, {")[1])

	def test_repair_job_ui_asks_backend_before_hiding_uninvoiced_gate_pass_button(self):
		js_path = MODULE_ROOT / "doctype" / "repair_job" / "repair_job.js"
		source = js_path.read_text(encoding="utf-8")

		self.assertIn("setup_final_release_gate_pass_button(frm);", source)
		self.assertIn("can_create_final_release_gate_pass", source)
		self.assertIn('type: "GET"', source)

	def test_repair_job_realtime_handlers_are_guarded_against_duplicate_setup(self):
		js_path = MODULE_ROOT / "doctype" / "repair_job" / "repair_job.js"
		source = js_path.read_text(encoding="utf-8")

		self.assertIn("setup_realtime_handlers(frm);", source)
		self.assertIn("frm.__auto_service_realtime_handlers_setup", source)
		self.assertEqual(source.count("frappe.realtime.on("), 2)

	def test_repair_job_optional_widgets_do_not_use_bare_globals(self):
		js_path = MODULE_ROOT / "doctype" / "repair_job" / "repair_job.js"
		source = js_path.read_text(encoding="utf-8")

		self.assertIn('setup_optional_widget("auto_service_billing"', source)
		self.assertIn('setup_optional_widget("auto_service_material_requests"', source)
		self.assertIn("const widget = window[globalName];", source)
		self.assertNotIn("auto_service_billing.setup", source)
		self.assertNotIn("auto_service_material_requests.setup", source)
