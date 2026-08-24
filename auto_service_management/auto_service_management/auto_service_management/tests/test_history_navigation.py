import json
from pathlib import Path

from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.dashboard_overrides import (
	get_customer_dashboard,
)
from auto_service_management.auto_service_management.doctype.customer_vehicle.customer_vehicle_dashboard import (
	get_data as get_customer_vehicle_dashboard,
)
from auto_service_management.auto_service_management.workspace_dashboard import WORKSPACE_SIDEBAR_SECTIONS


class TestHistoryNavigationContracts(UnitTestCase):
	def test_customer_dashboard_preserves_erpnext_groups_and_adds_workshop_history(self):
		data = {
			"transactions": [
				{"label": "Orders", "items": ["Sales Order", "Sales Invoice"]},
			],
		}

		result = get_customer_dashboard(data)

		self.assertIs(result, data)
		self.assertIn("Orders", [group["label"] for group in result["transactions"]])
		workshop_groups = [group for group in result["transactions"] if group["label"] == "Workshop History"]
		self.assertEqual(len(workshop_groups), 1)
		self.assertEqual(workshop_groups[0]["items"], ["Customer Vehicle", "Repair Job"])

		# Re-applying the hook must not duplicate dashboard entries.
		result = get_customer_dashboard(result)
		workshop_groups = [group for group in result["transactions"] if group["label"] == "Workshop History"]
		self.assertEqual(len(workshop_groups), 1)
		self.assertEqual(workshop_groups[0]["items"], ["Customer Vehicle", "Repair Job"])

	def test_customer_vehicle_dashboard_contains_complete_workshop_history(self):
		data = get_customer_vehicle_dashboard()

		self.assertEqual(data["fieldname"], "customer_vehicle")
		self.assertEqual(
			data["transactions"],
			[
				{
					"label": "Workshop History",
					"items": ["Repair Job", "Repair Job Service", "Service History"],
				}
			],
		)

	def test_workspace_exposes_find_vehicle_and_customers(self):
		intake = WORKSPACE_SIDEBAR_SECTIONS["Intake"]
		self.assertIn(
			{
				"label": "Find Vehicle",
				"link_type": "DocType",
				"link_to": "Customer Vehicle",
				"icon": "car-front",
			},
			intake,
		)
		self.assertIn(
			{"label": "Customers", "link_type": "DocType", "link_to": "Customer", "icon": "users"},
			intake,
		)

		path = Path(__file__).parents[1] / "workspace" / "customer_intake" / "customer_intake.json"
		workspace = json.loads(path.read_text(encoding="utf-8"))
		self.assertIn(
			{"label": "Find Vehicle", "link_to": "Customer Vehicle", "type": "DocType"},
			[
				{"label": row["label"], "link_to": row.get("link_to"), "type": row["type"]}
				for row in workspace["shortcuts"]
			],
		)
		self.assertIn(
			{"label": "Customers", "link_to": "Customer", "type": "Link"},
			[
				{"label": row["label"], "link_to": row.get("link_to"), "type": row["type"]}
				for row in workspace["links"]
				if row["type"] == "Link"
			],
		)

	def test_vehicle_search_contract_covers_identifiers_and_history_context(self):
		path = Path(__file__).parents[1] / "doctype" / "customer_vehicle" / "customer_vehicle.json"
		vehicle = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual(
			vehicle["search_fields"].split(","),
			["registration_number", "vin_chassis_number", "engine_number", "customer", "make", "model"],
		)
		fields = {field["fieldname"]: field for field in vehicle["fields"]}
		for fieldname in (
			"customer",
			"registration_number",
			"vin_chassis_number",
			"engine_number",
			"make",
			"model",
			"current_odometer",
			"last_service_date",
		):
			with self.subTest(fieldname=fieldname):
				self.assertEqual(fields[fieldname].get("in_list_view"), 1)
