# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import json
import unittest
from pathlib import Path

MODULE_ROOT = Path(__file__).parents[1]


def _doctype_fields(folder):
	path = MODULE_ROOT / "doctype" / folder / f"{folder}.json"
	doctype = json.loads(path.read_text(encoding="utf-8"))
	return {field["fieldname"]: field for field in doctype["fields"]}


class TestRepairWorkflowCharacterization(unittest.TestCase):
	def test_repair_job_status_contract_is_reduced_and_automatic(self):
		statuses = [value for value in _doctype_fields("repair_job")["job_status"]["options"].splitlines() if value]

		self.assertEqual(
			statuses,
			[
				"Draft",
				"Assessment",
				"Awaiting Approval",
				"In Repair",
				"Quality Check",
				"Billing",
				"Ready for Release",
				"Closed",
				"Cancelled",
			],
		)

	def test_repair_job_service_requires_workshop_and_no_status_field(self):
		fields = _doctype_fields("repair_job_service")

		self.assertNotIn("status", fields)
		self.assertTrue(any("workshop" in fieldname.lower() for fieldname in fields))

	def test_related_documents_use_tables_not_singular_links(self):
		fields = _doctype_fields("repair_job")

		for fieldname in ("repair_job_service", "sales_invoice", "road_test_report"):
			self.assertNotIn(fieldname, fields)

	def test_quality_check_owns_road_test_child_table(self):
		fields = _doctype_fields("quality_check")

		self.assertTrue(
			any(
				field["fieldtype"] == "Table" and "road test" in field.get("label", "").lower()
				for field in fields.values()
			)
		)
		self.assertFalse((MODULE_ROOT / "doctype" / "road_test_report").exists())

	def test_payment_status_is_derived_from_multiple_invoices_and_payment_entries(self):
		fields = _doctype_fields("repair_job")
		options = [value for value in fields["payment_status"]["options"].splitlines() if value]

		self.assertNotIn("sales_invoice", fields)
		self.assertEqual(options, ["Not Invoiced", "Unpaid", "Partially Paid", "Paid"])
