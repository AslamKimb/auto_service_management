import inspect
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.repair_job import repair_job
from auto_service_management.auto_service_management.doctype.repair_job_service import repair_job_service
from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	ServiceComponent,
)
from auto_service_management.auto_service_management.integration.erpnext import (
	adapters,
	component_mapping,
	document_sync,
)

MATERIAL_REQUEST_TYPES = (
	"Purchase",
	"Material Transfer",
	"Material Issue",
	"Manufacture",
	"Subcontracting",
	"Customer Provided",
)


class TestPhase16MaterialRequestContracts(UnitTestCase):
	def test_hooks_use_hashed_bundle_entry_for_repair_job_billing(self):
		from auto_service_management import hooks

		self.assertIn("repair_job_billing.bundle.js", hooks.app_include_js)
		self.assertNotIn("/assets/auto_service_management/js/repair_job_billing.js", hooks.app_include_js)

	def test_bundle_entry_imports_repair_job_billing_source(self):
		source = (
			Path(__file__).parents[2] / "public" / "js" / "repair_job_billing.bundle.js"
		).read_text(encoding="utf-8")
		self.assertEqual(source.strip(), 'import "./repair_job_billing";')

	def test_editable_setup_syncs_source_and_validates_hashed_bundle(self):
		source = (Path(__file__).parents[4] / "docker-compose.dev.yml").read_text(encoding="utf-8")
		self.assertIn("cp -r /app-source/. apps/auto_service_management/", source)
		self.assertIn('test -f "sites/assets/$$bundle_path"', source)

	def test_material_request_summary_uses_get(self):
		source = (
			Path(__file__).parents[2] / "public" / "js" / "repair_job_billing.js"
		).read_text(encoding="utf-8")
		self.assertIn(
			'get_material_request_components",\n\t\t\ttype: "GET",',
			source,
		)

	def test_mapping_endpoints_accept_component_refs_and_material_request_type(self):
		for method in (repair_job.make_material_request, repair_job_service.make_material_request):
			with self.subTest(method=method.__module__):
				parameters = inspect.signature(method).parameters
				self.assertIn("component_refs", parameters)
				self.assertIn("material_request_type", parameters)

	def test_material_request_types_come_from_erpnext_metadata(self):
		field = frappe._dict(options="\n".join(MATERIAL_REQUEST_TYPES))
		meta = frappe._dict(get_field=lambda fieldname: field)
		with patch.object(component_mapping.frappe, "get_meta", return_value=meta):
			self.assertEqual(component_mapping.get_material_request_types(), list(MATERIAL_REQUEST_TYPES))

	def test_repair_traces_accept_every_erpnext_material_request_type(self):
		with (
			patch.object(document_sync, "_has_repair_traces", return_value=True),
			patch.object(document_sync, "_validate_single_repair_job"),
			patch.object(document_sync, "_validate_component_links"),
			patch.object(document_sync, "_validate_component_quantities"),
		):
			for request_type in MATERIAL_REQUEST_TYPES:
				with self.subTest(request_type=request_type):
					document_sync.validate_material_request(
						frappe._dict(material_request_type=request_type)
					)

	def test_terminal_statuses_release_component_for_a_later_request(self):
		terminal = {
			"Purchase": "Received",
			"Material Transfer": "Transferred",
			"Material Issue": "Issued",
			"Manufacture": "Ordered",
			"Subcontracting": "Ordered",
			"Customer Provided": "Received",
		}
		for request_type, status in terminal.items():
			with self.subTest(request_type=request_type):
				self.assertFalse(
					component_mapping._material_request_values_are_active(1, request_type, status)
				)
		self.assertFalse(component_mapping._material_request_values_are_active(1, "Purchase", "Stopped"))
		self.assertFalse(component_mapping._material_request_values_are_active(2, "Purchase", "Cancelled"))
		self.assertTrue(component_mapping._material_request_values_are_active(1, "Purchase", "Pending"))

	def test_mapper_accepts_each_purpose_and_selected_component_subset(self):
		service = frappe._dict(name="RJS-1", service_name="Oil service")
		row = frappe._dict(
			doctype="Repair Job Service Part",
			name="PART-1",
			item_code="ITEM-1",
		)
		component = ServiceComponent(service, row, "parts", "Part")
		repair_job = frappe._dict(name="RJ-1", customer="CUSTOMER-1")
		settings = frappe._dict(company="COMPANY-1")

		for request_type in MATERIAL_REQUEST_TYPES:
			with self.subTest(request_type=request_type):
				target = frappe._dict(
					doctype="Material Request",
					name=None,
					docstatus=0,
					material_request_type=None,
					items=[],
				)
				target.is_new = lambda: True
				target.set = lambda fieldname, value: target.update({fieldname: value})
				target.append = lambda fieldname, value: target[fieldname].append(value)
				target.run_method = lambda method: None
				with (
					patch.object(component_mapping, "_get_repair_job", return_value=repair_job),
					patch.object(component_mapping, "_get_target_doc", return_value=target),
					patch.object(component_mapping, "_validate_target_job"),
					patch.object(component_mapping, "_validate_service_scope"),
					patch.object(component_mapping, "_validate_requested_component_refs"),
					patch.object(
						component_mapping,
						"_eligible_components",
						return_value=([(service, component)], {}),
					) as eligible,
					patch.object(component_mapping.frappe, "get_single", return_value=settings),
					patch.object(component_mapping, "_validate_company"),
					patch.object(
						component_mapping,
						"get_material_request_types",
						return_value=list(MATERIAL_REQUEST_TYPES),
					),
					patch.object(
						component_mapping,
						"_material_request_item",
						return_value={"item_code": "ITEM-1"},
					),
				):
					result = component_mapping.map_material_request(
						"RJ-1",
						component_refs=[
							{"doctype": "Repair Job Service Part", "name": "PART-1"}
						],
						material_request_type=request_type,
					)

				self.assertIs(result, target)
				self.assertEqual(target.material_request_type, request_type)
				self.assertEqual(target["items"], [{"item_code": "ITEM-1"}])
				self.assertEqual(
					eligible.call_args.kwargs["component_refs"],
					{("Repair Job Service Part", "PART-1")},
				)

	def test_existing_target_purpose_is_preserved(self):
		target = frappe._dict(
			doctype="Material Request",
			name=None,
			docstatus=0,
			material_request_type="Purchase",
			items=[],
		)
		target.is_new = lambda: True
		target.set = lambda fieldname, value: target.update({fieldname: value})
		target.append = lambda fieldname, value: target[fieldname].append(value)
		target.run_method = lambda method: None
		repair_job = frappe._dict(name="RJ-1", customer="CUSTOMER-1")
		service = frappe._dict(name="RJS-1")
		component = frappe._dict()
		with (
			patch.object(component_mapping, "_get_repair_job", return_value=repair_job),
			patch.object(component_mapping, "_get_target_doc", return_value=target),
			patch.object(component_mapping, "_validate_target_job"),
			patch.object(component_mapping, "_validate_service_scope"),
			patch.object(component_mapping, "_validate_requested_component_refs"),
			patch.object(
				component_mapping,
				"_eligible_components",
				return_value=([(service, component)], {}),
			),
			patch.object(
				component_mapping.frappe,
				"get_single",
				return_value=frappe._dict(company="COMPANY-1"),
			),
			patch.object(component_mapping, "_validate_company"),
			patch.object(
				component_mapping,
				"get_material_request_types",
				return_value=list(MATERIAL_REQUEST_TYPES),
			),
			patch.object(component_mapping, "_material_request_item", return_value={}),
		):
			component_mapping.map_material_request(
				"RJ-1",
				material_request_type="Material Issue",
			)
		self.assertEqual(target.material_request_type, "Purchase")

	def test_component_summary_includes_not_requested_and_history_rows(self):
		service = frappe._dict(
			name="RJS-1",
			service_name="Brake service",
			workshop_bay=None,
		)
		rows = [
			frappe._dict(
				doctype="Repair Job Service Part",
				name="PART-1",
				item_code="PAD",
				description="Brake pads",
				quantity=1,
				warehouse="Stores",
			),
			frappe._dict(
				doctype="Repair Job Service Consumable",
				name="CON-1",
				item_code="FLUID",
				description="Brake fluid",
				quantity=1,
				warehouse="Stores",
			),
		]
		components = [
			(service, ServiceComponent(service, rows[0], "parts", "Part")),
			(service, ServiceComponent(service, rows[1], "consumables", "Consumable")),
		]
		history = {
			("Repair Job Service Consumable", "CON-1"): [
				{
					"material_request": "MR-1",
					"material_request_type": "Purchase",
					"status": "Received",
					"is_active": False,
				}
			]
		}
		with (
			patch.object(
				component_mapping,
				"_get_repair_job",
				return_value=frappe._dict(name="RJ-1"),
			),
			patch.object(component_mapping, "_material_request_history", return_value=history),
			patch.object(component_mapping, "iter_repair_job_components", return_value=components),
			patch.object(
				component_mapping.frappe,
				"get_single",
				return_value=frappe._dict(default_warehouse="Stores"),
			),
			patch.object(component_mapping.frappe.db, "get_value", return_value=5),
			patch.object(
				component_mapping,
				"get_material_request_types",
				return_value=list(MATERIAL_REQUEST_TYPES),
			),
		):
			summary = component_mapping.get_material_request_components("RJ-1")

		self.assertEqual([row["request_state"] for row in summary["components"]], ["Not Requested", "Completed"])
		self.assertEqual(summary["components"][0]["history"], [])
		self.assertEqual(summary["components"][1]["history"][0]["material_request"], "MR-1")

	def test_stock_entry_rejects_non_material_issue_request(self):
		line = frappe._dict(
			item_code="ITEM-1",
			stock_request_status="Requested",
			material_request="MR-PURCHASE",
		)
		with (
			patch.object(adapters, "get_settings", return_value=frappe._dict()),
			patch.object(adapters, "_eligible_components", return_value=[(frappe._dict(), line)]),
			patch.object(component_mapping, "is_material_request_active", return_value=True),
			patch.object(adapters.frappe.db, "get_value", return_value="Purchase"),
			patch.object(adapters, "_make_doc") as make_doc,
		):
			with self.assertRaises(frappe.ValidationError):
				adapters.create_stock_entry_for_material_issue(frappe._dict(name="RJ-1"))
		make_doc.assert_not_called()


class TestPhase16PortalContracts(UnitTestCase):
	def test_hooks_publish_my_repairs_customer_portal_routes(self):
		from auto_service_management import hooks

		self.assertIn(
			{"title": "My Repairs", "route": "/my-repairs", "role": "Customer"},
			hooks.portal_menu_items,
		)
		self.assertIn(
			{"from_route": "/my-repairs", "to_route": "my_repairs"},
			hooks.website_route_rules,
		)
		self.assertTrue(
			any(
				rule["from_route"] == "/my-repairs/<path:name>"
				and rule["to_route"] == "my_repairs"
				for rule in hooks.website_route_rules
			)
		)

	def test_guest_is_denied_and_unmapped_user_gets_an_empty_list(self):
		from auto_service_management import portal

		with patch.dict(portal.frappe.session, {"user": "Guest"}):
			with self.assertRaises(frappe.PermissionError):
				portal.get_portal_repair_jobs()

		with (
			patch.dict(portal.frappe.session, {"user": "customer@example.com"}),
			patch.object(portal, "get_parents_for_user", return_value=[]),
		):
			self.assertEqual(portal.get_portal_repair_jobs()["jobs"], [])

	def test_cross_customer_detail_access_is_denied_before_loading_document(self):
		from auto_service_management import portal

		with (
			patch.dict(portal.frappe.session, {"user": "customer@example.com"}),
			patch.object(portal, "get_parents_for_user", return_value=["CUSTOMER-A"]),
			patch.object(portal.frappe.db, "exists", return_value=None),
			patch.object(portal.frappe, "get_doc") as get_doc,
		):
			with self.assertRaises(frappe.PermissionError):
				portal.get_portal_repair_job("RJ-CUSTOMER-B")
		get_doc.assert_not_called()

	def test_list_scope_uses_every_customer_linked_to_the_current_user(self):
		from auto_service_management import portal

		with (
			patch.dict(portal.frappe.session, {"user": "customer@example.com"}),
			patch.object(
				portal,
				"get_parents_for_user",
				return_value=["CUSTOMER-A", "CUSTOMER-B"],
			),
			patch.object(portal.frappe, "get_all", return_value=[]) as get_all,
			patch.object(portal.frappe.db, "count", return_value=0),
		):
			portal.get_portal_repair_jobs()

		self.assertEqual(
			get_all.call_args.kwargs["filters"]["customer"],
			["in", ["CUSTOMER-A", "CUSTOMER-B"]],
		)

	def test_portal_finance_filters_to_submitted_documents(self):
		from auto_service_management import portal

		job = frappe._dict(
			name="RJ-1",
			customer="CUSTOMER-A",
			customer_vehicle="VEH-1",
			registration_number="UAA 001A",
			vehicle_details="Toyota Hilux",
			creation="2026-07-23 08:00:00",
			job_status="Billing",
			total_amount=100,
			payment_status="Unpaid",
			currency="UGX",
		)
		calls = []

		def get_all(doctype, **kwargs):
			calls.append((doctype, kwargs.get("filters")))
			if doctype == "Sales Invoice":
				return [frappe._dict(name="SI-1")]
			return []

		with (
			patch.dict(portal.frappe.session, {"user": "customer@example.com"}),
			patch.object(portal, "get_parents_for_user", return_value=["CUSTOMER-A"]),
			patch.object(portal.frappe.db, "exists", return_value="RJ-1"),
			patch.object(portal.frappe, "get_doc", return_value=job),
			patch.object(portal.frappe, "get_all", side_effect=get_all),
		):
			portal.get_portal_repair_job("RJ-1")

		self.assertIn(("Sales Invoice", {"repair_job": "RJ-1", "docstatus": 1}), calls)
		self.assertTrue(
			any(
				doctype == "Payment Entry Reference"
				and filters["docstatus"] == 1
				for doctype, filters in calls
			)
		)
