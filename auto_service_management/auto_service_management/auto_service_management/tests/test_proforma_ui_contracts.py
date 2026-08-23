import json
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
REPAIR_JOB_JS = APP_ROOT / "auto_service_management" / "doctype" / "repair_job" / "repair_job.js"
REPAIR_JOB_SERVICE_JS = APP_ROOT / "auto_service_management" / "doctype" / "repair_job_service" / "repair_job_service.js"
BILLING_JS = APP_ROOT / "public" / "js" / "repair_job_billing.js"
PRINTING_PY = APP_ROOT / "auto_service_management" / "printing.py"
PROFORMA_TEMPLATE = APP_ROOT / "templates" / "includes" / "auto_service_print" / "proforma_invoice.html"
PROFORMA_FORMAT = APP_ROOT / "auto_service_management" / "print_format" / "proforma_invoice" / "proforma_invoice.json"


class TestProformaUIContracts(unittest.TestCase):
	def test_repair_job_surfaces_sales_orders_without_quotation_actions(self):
		job = REPAIR_JOB_JS.read_text(encoding="utf-8")
		service = REPAIR_JOB_SERVICE_JS.read_text(encoding="utf-8")
		for path in (
			APP_ROOT / "auto_service_management" / "doctype" / "repair_job" / "repair_job.json",
			APP_ROOT / "auto_service_management" / "doctype" / "repair_job_service" / "repair_job_service.json",
		):
			fields = json.loads(path.read_text(encoding="utf-8"))["fields"]
			self.assertTrue(any(field.get("fieldname") == "sales_orders_html" for field in fields))
		self.assertNotIn("Create Quotation", job + service)
		self.assertNotIn("get_quotation_summary", job)
		self.assertIn("auto_service_sales_orders", job + service)
		self.assertIn('set_route("List", "Sales Order"', job)

	def test_sales_order_picker_uses_get_and_post_mapping_contract(self):
		source = BILLING_JS.read_text(encoding="utf-8")
		self.assertIn("get_sales_order_components", source)
		self.assertIn("Create Draft Sales Order", source)
		self.assertIn("component_refs: JSON.stringify", source)
		self.assertIn("sales-order-component-choice", source)
		self.assertIn("Loading Proforma Invoice components", source)
		self.assertIn("Unable to load Sales Order component status", source)

	def test_sales_order_print_format_is_a_proforma_invoice(self):
		printing = PRINTING_PY.read_text(encoding="utf-8")
		template = PROFORMA_TEMPLATE.read_text(encoding="utf-8")
		fmt = json.loads(PROFORMA_FORMAT.read_text(encoding="utf-8"))
		self.assertIn('(\"Proforma Invoice\", \"Sales Order\")', printing)
		self.assertIn('print_title = "Proforma Invoice"', template)
		self.assertEqual(fmt["name"], "Proforma Invoice")
		self.assertEqual(fmt["doc_type"], "Sales Order")
		self.assertIn("proforma_invoice.html", fmt["html"])


if __name__ == "__main__":
	unittest.main()
