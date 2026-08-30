import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import frappe

from auto_service_management.auto_service_management.doctype.repair_job import repair_job
from auto_service_management.auto_service_management.integration.erpnext import component_mapping


ROOT = Path(__file__).resolve().parents[1]


def _doctype(folder):
	return json.loads((ROOT / "doctype" / folder / f"{folder}.json").read_text(encoding="utf-8"))


class TestFutureFeatureContracts(unittest.TestCase):
	def test_customer_vehicle_customer_is_optional_and_history_is_native(self):
		vehicle = _doctype("customer_vehicle")
		fields = {field["fieldname"]: field for field in vehicle["fields"]}
		self.assertNotEqual(fields["customer"].get("reqd"), 1)
		self.assertEqual(fields["customer_association_history"]["fieldtype"], "HTML")
		association = _doctype("customer_vehicle_customer_association")
		association_fields = {field["fieldname"]: field for field in association["fields"]}
		for fieldname in ("customer_vehicle", "customer", "valid_from", "valid_to", "source_doctype", "source_name"):
			self.assertIn(fieldname, association_fields)

	def test_repair_job_contact_and_check_in_contract(self):
		fields = {field["fieldname"]: field for field in _doctype("repair_job")["fields"]}
		self.assertEqual(fields["contact_person"]["options"], "Contact")
		self.assertEqual(fields["contact_person"].get("no_create"), 1)
		self.assertIn("contact_person_name_snapshot", fields)
		search_params = inspect.signature(repair_job.get_company_contacts).parameters
		for parameter in ("doctype", "txt", "searchfield", "start", "page_len", "filters"):
			self.assertIn(parameter, search_params)
		source = inspect.getsource(repair_job.RepairJob.check_in)
		self.assertIn("confirm_customer_association", source)
		self.assertIn("validate_company_contact", source)
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[repair_job.RepairJob.check_in], ["POST"])
		self.assertIn("create_company_contact", inspect.getsource(repair_job))
		self.assertEqual(
			frappe.allowed_http_methods_for_whitelisted_func[repair_job.create_company_contact],
			["POST"],
		)
		self.assertIn('"link_doctype": "Customer"', inspect.getsource(repair_job.create_company_contact))

	@patch("auto_service_management.auto_service_management.doctype.repair_job.repair_job.sync_repair_job_compatibility_views")
	def test_repair_job_load_rehydrates_service_summary(self, sync_views):
		job = type("RepairJob", (), {"name": "RJ-1", "is_new": lambda self: False})()

		repair_job.RepairJob.onload(job)

		sync_views.assert_called_once_with(job)

	@patch.object(repair_job.frappe, "has_permission")
	@patch.object(repair_job.frappe, "get_list")
	@patch.object(repair_job.frappe, "get_all")
	@patch.object(repair_job.frappe, "get_doc")
	def test_company_contact_query_returns_frappe_link_rows(
		self, get_doc, get_all, get_list, has_permission
	):
		get_doc.return_value = type("Customer", (), {"customer_type": "Company", "check_permission": lambda self, _: None})()
		get_all.return_value = ["CONTACT-1"]
		get_list.return_value = [
			{
				"name": "CONTACT-1",
				"first_name": "Jane",
				"last_name": "Doe",
				"phone": "0700000000",
				"mobile_no": "",
				"email_id": "jane@example.com",
			}
		]

		rows = repair_job.get_company_contacts(
			"Contact", "Jane", "name", 0, 10, {"customer": "Judicature"}
		)
		self.assertEqual(rows[0][0], "CONTACT-1")
		self.assertEqual(rows[0][1], "Jane Doe")

		dict_rows = repair_job.get_company_contacts(
			"Contact", "Jane", "name", 0, 10, {"customer": "Judicature"}, as_dict=True
		)
		self.assertIsInstance(dict_rows[0], dict)

	def test_sales_order_retrieval_supports_preview_and_submitted_boundary(self):
		source = inspect.getsource(component_mapping)
		self.assertIn("def get_items_from_repair_job(", source)
		self.assertIn("allow_submitted=True", source)
		self.assertIn("_validate_sales_order_update_target", source)
		self.assertEqual(
			frappe.allowed_http_methods_for_whitelisted_func[component_mapping.get_items_from_repair_job],
			["POST"],
		)
		self.assertIn('"Sales Order": "public/js/sales_order.js"', (ROOT.parent / "hooks.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
	unittest.main()
