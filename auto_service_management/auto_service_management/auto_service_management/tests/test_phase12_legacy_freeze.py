# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from pathlib import Path
import unittest

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
