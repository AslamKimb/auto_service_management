import inspect
import json
import unittest
from pathlib import Path

from auto_service_management.auto_service_management import custom_fields
from auto_service_management.auto_service_management.doctype.repair_job import repair_job
from auto_service_management.auto_service_management.doctype.repair_job_service import repair_job_service
from auto_service_management.auto_service_management.integration.erpnext import (
	component_mapping,
	document_sync,
)

ROOT = Path(__file__).resolve().parents[2]


class TestSalesOrderBackendContract(unittest.TestCase):
	def test_sales_order_mapping_and_get_contracts_are_explicit(self):
		mapping_source = inspect.getsource(component_mapping)
		job_source = inspect.getsource(repair_job)
		service_source = inspect.getsource(repair_job_service)
		self.assertIn("def map_sales_order(", mapping_source)
		self.assertIn('@frappe.whitelist(methods=["GET"])\ndef get_sales_order_components', mapping_source)
		self.assertIn('@frappe.whitelist(methods=["POST"])\ndef make_sales_order', job_source)
		self.assertIn('@frappe.whitelist(methods=["POST"])\ndef make_sales_order', service_source)
		self.assertNotIn("def create_quotation", job_source)
		self.assertNotIn("def create_quotation", service_source)
		self.assertNotIn('@frappe.whitelist(methods=["POST"])\ndef make_quotation', service_source)

	def test_sales_order_lifecycle_hooks_and_invoice_mapper_are_registered(self):
		hooks = (ROOT / "hooks.py").read_text(encoding="utf-8")
		self.assertIn('"erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice"', hooks)
		for method in ("validate_sales_order", "sync_sales_order", "cancel_sales_order", "trash_sales_order"):
			self.assertIn(method, hooks)
		self.assertIn("def _validate_sales_order_submission", inspect.getsource(document_sync))
		self.assertIn('doc.select_print_heading = "Proforma Invoice"', inspect.getsource(document_sync))
		mapper = (ROOT / "auto_service_management" / "integration" / "sales_order_mapping.py").read_text(encoding="utf-8")
		self.assertIn("items_by_source", mapper)
		self.assertIn('sales_order_item.get("name")', mapper)

	def test_trace_custom_fields_include_sales_order_parent_and_items(self):
		fields = custom_fields.get_trace_custom_fields()
		self.assertEqual(len(fields["Sales Order Item"]), len(custom_fields.TRACE_FIELDS))
		self.assertEqual(
			{row["fieldname"] for row in fields["Sales Order"]},
			{"repair_job", "repair_job_service", "fleet_service_campaign"},
		)

	def test_repair_job_has_related_sales_order_child_table(self):
		path = ROOT / "auto_service_management" / "doctype" / "repair_job" / "repair_job.json"
		doc = json.loads(path.read_text(encoding="utf-8"))
		field = next(row for row in doc["fields"] if row.get("fieldname") == "sales_orders")
		self.assertEqual(field["options"], "Repair Job Sales Order Row")


if __name__ == "__main__":
	unittest.main()
