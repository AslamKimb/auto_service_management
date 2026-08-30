from unittest.mock import MagicMock, patch

import frappe
from frappe.handler import is_valid_http_method
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management import custom_fields
from auto_service_management.auto_service_management.doctype.customer_lpo import customer_lpo
from auto_service_management.auto_service_management.integration import customer_lpo_workflow


class TestCustomerLPOWorkflow(UnitTestCase):
	def test_controller_methods_have_explicit_http_methods(self):
		methods = {
			customer_lpo.preview_vehicle_csv: "GET",
			customer_lpo.get_lpo_summary: "GET",
			customer_lpo.import_vehicle_csv: "POST",
			customer_lpo.create_campaign_and_repair_jobs: "POST",
			customer_lpo.make_sales_order: "POST",
			customer_lpo.make_sales_invoice: "POST",
			customer_lpo.close_lpo: "POST",
		}
		for method, allowed in methods.items():
			with self.subTest(method=method.__name__):
				self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[method], [allowed])

	def test_controller_methods_have_typed_public_inputs(self):
		from inspect import signature

		methods = (
			customer_lpo.preview_vehicle_csv,
			customer_lpo.import_vehicle_csv,
			customer_lpo.create_campaign_and_repair_jobs,
			customer_lpo.get_lpo_summary,
			customer_lpo.make_sales_order,
			customer_lpo.make_sales_invoice,
			customer_lpo.close_lpo,
		)
		for method in methods:
			with self.subTest(method=method.__name__):
				self.assertTrue(
					all(
						parameter.annotation is not parameter.empty
						for parameter in signature(method).parameters.values()
					)
				)

	def test_mutating_csv_import_rejects_get(self):
		original_request = getattr(frappe.local, "request", None)
		frappe.local.request = frappe._dict(method="GET")
		try:
			with self.assertRaises(frappe.PermissionError):
				is_valid_http_method(customer_lpo.import_vehicle_csv)
		finally:
			frappe.local.request = original_request

	def test_obsolete_registration_first_resolver_is_not_public(self):
		self.assertFalse(hasattr(customer_lpo, "resolve_vehicle_rows"))

	def test_unresolved_csv_import_is_atomic(self):
		lpo = MagicMock()
		lpo.name = "LPO-1"
		lpo.customer = "CUSTOMER-1"
		lpo.docstatus = 0
		lpo.get.return_value = []
		row = {
			"registration_number": "UBA482M",
			"customer_vehicle": None,
			"requested_work": "Brakes",
			"planned_date": None,
			"allocated_ceiling": 0,
			"remarks": None,
		}
		with (
			patch.object(customer_lpo_workflow, "_get_lpo", return_value=lpo),
			patch.object(customer_lpo_workflow, "_normalise_rows", return_value=[row]),
			patch.object(customer_lpo_workflow, "_resolve_vehicle", return_value=(None, "Not Found")),
			self.assertRaisesRegex(frappe.ValidationError, "Create the Customer Vehicle first"),
		):
			customer_lpo_workflow.import_vehicle_csv("LPO-1", rows=[row])

		lpo.append.assert_not_called()
		lpo.save.assert_not_called()

	def test_csv_header_and_registration_are_normalized(self):
		csv_text = "registration_number,customer_vehicle,requested_work,planned_date,allocated_ceiling,remarks\n uba-482m ,,,2026-09-01,100,Priority"
		rows = customer_lpo_workflow._rows_from_csv(csv_text)
		self.assertEqual(rows[0]["registration_number"], "UBA482M")
		self.assertEqual(rows[0]["planned_date"].isoformat(), "2026-09-01")
		self.assertEqual(rows[0]["allocated_ceiling"], 100)

	def test_csv_header_contract_rejects_missing_or_unknown_columns(self):
		with self.assertRaises(frappe.ValidationError):
			customer_lpo_workflow._rows_from_csv("registration_number,requested_work\nUBA482M,Brakes")
		with self.assertRaises(frappe.ValidationError):
			customer_lpo_workflow._rows_from_csv(
				"registration_number,customer_vehicle,requested_work,planned_date,allocated_ceiling,remarks,ocr_text\n"
				"UBA482M,,,,,,"
			)

	def test_ceiling_basis_uses_authoritative_erpnext_totals(self):
		invoice = frappe._dict(
			net_total=100,
			grand_total=118,
			rounded_total=120,
			disable_rounded_total=0,
		)
		self.assertEqual(customer_lpo_workflow._invoice_amount(invoice, "Tax Exclusive"), 100)
		self.assertEqual(customer_lpo_workflow._invoice_amount(invoice, "Tax Inclusive"), 120)
		invoice.disable_rounded_total = 1
		self.assertEqual(customer_lpo_workflow._invoice_amount(invoice, "Tax Inclusive"), 118)
		invoice.disable_rounded_total = 0
		invoice.rounded_total = 0
		self.assertEqual(customer_lpo_workflow._invoice_amount(invoice, "Tax Inclusive"), 0)

	def test_native_lpo_document_cannot_duplicate_active_document(self):
		with (
			patch.object(
				customer_lpo_workflow.frappe,
				"get_list",
				return_value=["SO-OLD"],
			),
			self.assertRaisesRegex(frappe.ValidationError, "already has an active"),
		):
			customer_lpo_workflow._assert_one_active_document("Sales Order", "LPO-1")

	def test_named_target_does_not_bypass_active_document_guard(self):
		with (
			patch.object(
				customer_lpo_workflow.frappe,
				"get_list",
				return_value=["SO-OTHER"],
			) as get_list,
			self.assertRaisesRegex(frappe.ValidationError, "already has an active"),
		):
			customer_lpo_workflow._assert_one_active_document("Sales Order", "LPO-1", "SO-TARGET")
		filters = get_list.call_args.kwargs["filters"]
		self.assertEqual(filters["name"], ["!=", "SO-TARGET"])

	def test_effective_authority_uses_permission_scoped_amendments(self):
		lpo = frappe._dict(name="LPO-1", authorized_amount=100)
		with (
			patch.object(customer_lpo_workflow.frappe.db, "exists", return_value=True),
			patch.object(
				customer_lpo_workflow.frappe,
				"get_list",
				return_value=[frappe._dict(amount_increase=25)],
			) as get_list,
		):
			self.assertEqual(customer_lpo_workflow._effective_authorized_amount(lpo), 125)
		get_list.assert_called_once_with(
			"Customer LPO Amendment",
			filters={"customer_lpo": "LPO-1", "docstatus": 1},
			fields=["amount_increase"],
			order_by="creation asc, name asc",
			limit_page_length=500,
			limit_start=0,
		)

	def test_lpo_invoice_uses_native_sales_order_mapper_when_order_is_submitted(self):
		lpo = frappe._dict(
			name="LPO-1",
			docstatus=1,
			status="Active",
			customer="CUST-1",
			company="Company",
			currency="UGX",
			fleet_service_campaign="FSC-1",
		)
		campaign = frappe._dict(name="FSC-1", customer="CUST-1")
		target = frappe._dict(doctype="Sales Invoice", customer_lpo=None)
		with (
			patch.object(customer_lpo_workflow, "_get_lpo", return_value=lpo),
			patch.object(customer_lpo_workflow, "_require_campaign", return_value=campaign),
			patch.object(customer_lpo_workflow.frappe, "has_permission", return_value=True),
			patch.object(customer_lpo_workflow, "_assert_one_active_document"),
			patch.object(
				customer_lpo_workflow.frappe,
				"get_list",
				side_effect=[[{"name": "SO-1"}]],
			),
			patch(
				"auto_service_management.auto_service_management.integration.sales_order_mapping.make_sales_invoice",
				return_value=target,
			) as native_mapper,
		):
			result = customer_lpo_workflow.make_sales_invoice("LPO-1")

		self.assertIs(result, target)
		self.assertEqual(result.customer_lpo, "LPO-1")
		native_mapper.assert_called_once_with("SO-1", target_doc=None)

	def test_cashier_billing_path_reads_lpo_and_only_requires_billing_create(self):
		lpo = frappe._dict(
			name="LPO-1",
			docstatus=1,
			status="Active",
			customer="CUST-1",
			company="Company",
			currency="UGX",
			fleet_service_campaign="FSC-1",
		)
		campaign = frappe._dict(name="FSC-1", customer="CUST-1")
		target = frappe._dict(doctype="Sales Invoice")
		with (
			patch.object(customer_lpo_workflow, "_get_lpo", return_value=lpo) as get_lpo,
			patch.object(customer_lpo_workflow, "_require_campaign", return_value=campaign),
			patch.object(customer_lpo_workflow.frappe, "has_permission", return_value=True) as has_permission,
			patch.object(customer_lpo_workflow, "_assert_one_active_document"),
			patch.object(customer_lpo_workflow.frappe, "get_list", return_value=[]),
			patch(
				"auto_service_management.auto_service_management.integration.erpnext.component_mapping.map_campaign_sales_invoice",
				return_value=target,
			) as mapper,
		):
			result = customer_lpo_workflow.make_sales_invoice("LPO-1")

		self.assertIs(result, target)
		get_lpo.assert_called_once_with("LPO-1", "read")
		has_permission.assert_called_once_with("Sales Invoice", "create", throw=True)
		mapper.assert_called_once_with("FSC-1", target_doc=None, component_refs=None, permission="read")

	def test_sales_document_lpo_trace_fields_are_app_owned(self):
		fields = custom_fields.get_trace_custom_fields()
		self.assertIn("customer_lpo", {row["fieldname"] for row in fields["Sales Order"]})
		self.assertIn("customer_lpo", {row["fieldname"] for row in fields["Sales Invoice"]})

	def test_over_ceiling_requires_amendment(self):
		lpo = frappe._dict(
			name="LPO-2026-00001",
			docstatus=1,
			status="Active",
			customer="CUST-1",
			company="Company",
			currency="UGX",
			ceiling_basis="Tax Inclusive",
			authorized_amount=100,
			fleet_service_campaign="FSC-1",
		)
		doc = frappe._dict(
			doctype="Sales Invoice",
			name=None,
			customer_lpo="LPO-2026-00001",
			customer="CUST-1",
			company="Company",
			currency="UGX",
			fleet_service_campaign="FSC-1",
			net_total=100,
			grand_total=120,
			rounded_total=120,
			disable_rounded_total=0,
		)
		with (
			patch.object(customer_lpo_workflow, "_get_lpo", return_value=lpo),
			patch.object(customer_lpo_workflow.frappe, "get_all", return_value=[]),
		):
			with self.assertRaisesRegex(frappe.ValidationError, "ceiling exceeded"):
				customer_lpo_workflow.validate_lpo_invoice_ceiling(doc)
