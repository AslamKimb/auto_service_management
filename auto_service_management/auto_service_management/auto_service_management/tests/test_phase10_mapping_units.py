import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.repair_job import repair_job as repair_job_module
from auto_service_management.auto_service_management.doctype.repair_job.repair_job import RepairJob
from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	ServiceComponent,
	iter_repair_job_components,
)
from auto_service_management.auto_service_management.integration.erpnext import (
	adapters,
	component_mapping,
	document_sync,
)


class TestPhase10MappingUnits(UnitTestCase):
	def test_repair_job_release_uses_gate_pass_invoice_validator(self):
		job = RepairJob({"doctype": "Repair Job", "name": "RJ-1"})
		with (
			patch.object(job, "_require_write_permission"),
			patch.object(job, "_sync_invoice_state"),
			patch(
				"auto_service_management.auto_service_management.integration.erpnext.document_sync.validate_job_invoices_for_gate_pass",
				side_effect=frappe.ValidationError,
			),
		):
			with self.assertRaises(frappe.ValidationError):
				job.release()

	def test_repair_job_create_service_requires_target_create_permission(self):
		job = RepairJob({"doctype": "Repair Job", "name": "RJ-1"})
		with (
			patch.object(job, "_require_write_permission"),
			patch.object(repair_job_module.frappe, "has_permission", side_effect=frappe.PermissionError),
			patch.object(repair_job_module.frappe, "get_doc") as get_doc,
		):
			with self.assertRaises(frappe.PermissionError):
				job.create_service()

		get_doc.assert_not_called()

	def test_repair_job_create_gate_pass_requires_target_create_permission(self):
		job = RepairJob({"doctype": "Repair Job", "name": "RJ-1"})
		with (
			patch.object(job, "_require_write_permission"),
			patch.object(repair_job_module.frappe, "has_permission", side_effect=frappe.PermissionError),
			patch(
				"auto_service_management.auto_service_management.integration.erpnext.document_sync.validate_job_invoices_for_gate_pass"
			) as validator,
		):
			with self.assertRaises(frappe.PermissionError):
				job.create_gate_pass()

		validator.assert_not_called()

	def test_stock_entry_creation_requires_target_create_permission_before_document_insert(self):
		service = frappe._dict(name="RJS-1", service_name="Service")
		line = frappe._dict(
			row_doctype="Repair Job Service Part",
			name="PART-1",
			item_code="ITEM-1",
			stock_request_status="Requested",
			stock_entry=None,
			requested_qty=2,
			issued_qty=0,
			quantity=2,
			material_request="MR-1",
			uom="Nos",
			warehouse="WH-1",
			service_description="Part",
			legacy_repair_service_line=None,
		)
		job = frappe._dict(name="RJ-1", customer_vehicle="VEH-1")
		with (
			patch.object(adapters, "get_settings", return_value=frappe._dict(company="Company")),
			patch.object(adapters, "_eligible_components", return_value=[(service, line)]),
			patch.object(adapters.frappe.db, "get_value", return_value="Material Issue"),
			patch(
				"auto_service_management.auto_service_management.integration.erpnext.component_mapping.is_material_request_active",
				return_value=True,
			),
			patch.object(adapters.frappe, "has_permission", side_effect=frappe.PermissionError),
			patch.object(adapters, "_make_doc") as make_doc,
		):
			with self.assertRaises(frappe.PermissionError):
				adapters.create_stock_entry_for_material_issue(job)

		make_doc.assert_not_called()

	def test_erpnext_adapter_explicit_create_actions_check_target_create_permission(self):
		source = inspect.getsource(adapters)
		for doctype in ("Quotation", "Sales Order", "Stock Entry"):
			self.assertIn(f'_require_create_permission("{doctype}")', source)

	def test_invoice_component_state_distinguishes_draft_and_submitted_invoice(self):
		component = frappe._dict(billable=1, sales_invoice="SI-1")
		with patch.object(component_mapping.frappe.db, "get_value", return_value=0):
			self.assertEqual(component_mapping._component_invoice_state(component), "Reserved")
		with patch.object(component_mapping.frappe.db, "get_value", return_value=1):
			self.assertEqual(component_mapping._component_invoice_state(component), "Invoiced")

	def test_selected_invoice_components_must_be_billable_and_belong_to_job(self):
		service = frappe._dict(name="RJS-1", docstatus=0)
		component = frappe._dict(doctype="Repair Job Service Part", name="PART-1", billable=0)
		with patch.object(
			component_mapping,
			"iter_repair_job_components",
			return_value=[(service, ServiceComponent(service, component, "parts", "Part"))],
		):
			with self.assertRaises(frappe.ValidationError):
				component_mapping._validate_requested_component_refs(
					"RJ-1",
					{("Repair Job Service Part", "PART-1")},
					None,
				)

	def test_repair_job_is_non_submittable_and_uses_business_status(self):
		path = Path(__file__).resolve().parents[1] / "doctype" / "repair_job" / "repair_job.json"
		meta = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual(meta["is_submittable"], 0)
		for permission in meta["permissions"]:
			for action in ("submit", "cancel", "amend"):
				self.assertEqual(permission.get(action, 0), 0)
		self.assertNotIn(
			"before_submit",
			inspect.getsource(
				__import__(
					"auto_service_management.auto_service_management.doctype.repair_job.repair_job",
					fromlist=["RepairJob"],
				)
			),
		)

	def test_sales_invoice_component_scope_skips_service_status_gate(self):
		services = [frappe._dict(name="RJS-1", repair_job="RJ-1", status="Draft", service_name="Job service")]

		with patch.object(component_mapping.frappe, "get_all", return_value=services):
			component_mapping._validate_service_scope("RJ-1", {"RJS-1"}, None, document_label="Sales Invoice")

	def test_component_iterator_excludes_blank_status_when_statuses_are_required(self):
		service = frappe._dict(
			name="RJS-1",
			status=None,
			docstatus=0,
			parts=[
				frappe._dict(
					doctype="Repair Job Service Part",
					name="PART-1",
					billable=True,
				)
			],
		)

		with patch(
			"auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service.get_repair_job_services",
			return_value=[service],
		):
			self.assertEqual(
				list(iter_repair_job_components("RJ-1", service_statuses={"Approved"})),
				[],
			)

	def test_component_iterator_does_not_status_gate_when_service_doctype_has_no_status_field(self):
		service = frappe._dict(
			name="RJS-1",
			docstatus=0,
			meta=frappe._dict(has_field=lambda fieldname: False),
			parts=[
				frappe._dict(
					doctype="Repair Job Service Part",
					name="PART-1",
					billable=True,
				)
			],
		)

		with patch(
			"auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service.get_repair_job_services",
			return_value=[service],
		):
			self.assertEqual(
				[
					row.name
					for _service, row in iter_repair_job_components("RJ-1", service_statuses={"Approved"})
				],
				["PART-1"],
			)

	def test_component_summary_endpoints_and_desk_loaders_use_get(self):
		source = inspect.getsource(component_mapping)
		asset = (Path(__file__).resolve().parents[2] / "public" / "js" / "repair_job_billing.js").read_text(
			encoding="utf-8"
		)

		self.assertIn('@frappe.whitelist(methods=["GET"])\ndef get_sales_invoice_components', source)
		self.assertIn('@frappe.whitelist(methods=["GET"])\ndef get_material_request_components', source)
		self.assertGreaterEqual(asset.count('type: "GET"'), 2)

	def test_quotation_mapping_reuses_billable_invoice_values_without_reservation(self):
		class Target:
			doctype = "Quotation"
			docstatus = 0
			name = None

			def __init__(self):
				self.items = []
				self.values = {}

			def get(self, fieldname):
				return self.values.get(fieldname)

			def set(self, fieldname, value):
				self.values[fieldname] = value
				setattr(self, fieldname, value)

			def append(self, fieldname, value):
				self.items.append(value)

			def run_method(self, _method):
				return None

		job = frappe._dict(
			name="RJ-1",
			customer="CUST-1",
			customer_vehicle="VEH-1",
			project="PROJ-1",
		)
		service = frappe._dict(name="RJS-1", service_name="Brake Service")
		component = frappe._dict(row_doctype="Repair Job Service Part", name="PART-1")
		target = Target()

		with (
			patch.object(component_mapping, "_get_repair_job", return_value=job),
			patch.object(component_mapping, "_get_target_doc", return_value=target),
			patch.object(component_mapping, "_validate_target_job"),
			patch.object(component_mapping, "_validate_service_scope"),
			patch.object(component_mapping, "_validate_requested_component_refs"),
			patch.object(
				component_mapping, "iter_repair_job_components", return_value=[(service, component)]
			),
			patch.object(
				component_mapping, "_sales_invoice_item", return_value={"item_code": "PART-1", "qty": 2}
			),
			patch.object(component_mapping, "today", return_value="2026-08-02"),
			patch.object(
				component_mapping,
				"_get_settings",
				return_value=frappe._dict(company="Company", selling_price_list="Standard Selling"),
			),
		):
			result = component_mapping.map_quotation("RJ-1", service_names={"RJS-1"})

		self.assertIs(result, target)
		self.assertEqual(target.repair_job, "RJ-1")
		self.assertEqual(target.repair_job_service, "RJS-1")
		self.assertEqual(target.transaction_date, "2026-08-02")
		self.assertEqual(target.valid_till, "2026-09-02")
		self.assertEqual(target.items, [{"item_code": "PART-1", "qty": 2}])

	def test_sales_order_mapping_assigns_client_safe_name_for_new_target(self):
		class Target:
			doctype = "Sales Order"
			docstatus = 0
			name = None

			def __init__(self):
				self.items = []
				self.values = {}

			def is_new(self):
				return True

			def get(self, fieldname):
				return self.values.get(fieldname)

			def set(self, fieldname, value):
				self.values[fieldname] = value
				setattr(self, fieldname, value)

			def append(self, _fieldname, value):
				self.items.append(value)

			def run_method(self, _method):
				return None

		job = frappe._dict(name="RJ-1", customer="CUST-1", customer_vehicle="VEH-1", project="PROJ-1")
		service = frappe._dict(name="RJS-1", service_name="Brake Service")
		component = frappe._dict(row_doctype="Repair Job Service Part", name="PART-1")
		target = Target()

		with (
			patch.object(component_mapping, "_get_repair_job", return_value=job),
			patch.object(component_mapping, "_get_target_doc", return_value=target),
			patch.object(component_mapping, "_validate_target_job"),
			patch.object(component_mapping, "_validate_company"),
			patch.object(component_mapping, "_validate_service_scope"),
			patch.object(component_mapping, "_validate_requested_component_refs"),
			patch.object(
				component_mapping, "iter_repair_job_components", return_value=[(service, component)]
			),
			patch.object(
				component_mapping, "_sales_order_item", return_value={"item_code": "PART-1", "qty": 2}
			),
			patch.object(component_mapping, "_set_if_empty"),
			patch.object(component_mapping, "today", return_value="2026-08-02"),
			patch.object(component_mapping.frappe, "generate_hash", return_value="testhash"),
			patch.object(
				component_mapping,
				"_get_settings",
				return_value=frappe._dict(company="Company", selling_price_list="Standard Selling"),
			),
		):
			result = component_mapping.map_sales_order("RJ-1", service_names={"RJS-1"})

		self.assertIs(result, target)
		self.assertEqual(target.name, "new-sales-order-testhash")

	def test_quotation_and_count_mutations_have_explicit_http_methods(self):
		job_source = inspect.getsource(repair_job_module)
		service_source = inspect.getsource(
			__import__(
				"auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service",
				fromlist=["RepairJobService"],
			)
		)
		self.assertIn('@frappe.whitelist(methods=["GET"])\ndef get_quotation_summary', job_source)
		self.assertNotIn('@frappe.whitelist(methods=["POST"])\ndef make_quotation', service_source)

	def test_sales_invoice_draft_submission_validation_skips_service_status_gate(self):
		with (
			patch.object(
				document_sync,
				"_trace_items",
				return_value=[frappe._dict(repair_job_service="RJS-1")],
			),
			patch.object(document_sync.frappe, "get_all") as get_all,
		):
			document_sync._validate_invoice_service_submission(frappe._dict(docstatus=0))

		get_all.assert_not_called()

	def test_sales_invoice_submission_allows_invoiceable_service_status(self):
		with (
			patch.object(
				document_sync,
				"_trace_items",
				return_value=[frappe._dict(repair_job_service="RJS-1")],
			),
			patch.object(
				document_sync.frappe,
				"get_all",
				return_value=[frappe._dict(name="RJS-1", service_name="Approved service", docstatus=0)],
			),
		):
			document_sync._validate_invoice_service_submission(frappe._dict(docstatus=1))

	def test_sales_invoice_submission_rejects_cancelled_service(self):
		with (
			patch.object(
				document_sync,
				"_trace_items",
				return_value=[frappe._dict(repair_job_service="RJS-1")],
			),
			patch.object(
				document_sync.frappe,
				"get_all",
				return_value=[frappe._dict(name="RJS-1", service_name="Cancelled service", docstatus=2)],
			),
		):
			with self.assertRaises(frappe.ValidationError):
				document_sync._validate_invoice_service_submission(frappe._dict(docstatus=1))

	def test_repair_job_sales_invoices_returns_multiple_rows(self):
		class _Job:
			def get(self, field):
				if field == "sales_invoices":
					return [frappe._dict(sales_invoice="SI-1"), frappe._dict(sales_invoice="SI-2")]
				return None

		job = _Job()

		with (
			patch.object(document_sync.frappe, "get_doc", return_value=job),
			patch.object(document_sync.frappe.db, "exists", return_value=True),
		):
			self.assertEqual(
				document_sync.get_repair_job_sales_invoices("RJ-1"),
				["SI-1", "SI-2"],
			)

	def test_payment_entry_sync_is_immediate_and_notification_is_after_commit(self):
		class _AfterCommit:
			def __init__(self):
				self.callbacks = []

			def add(self, callback):
				self.callbacks.append(callback)

		fake_db = SimpleNamespace(after_commit=_AfterCommit(), get_value=lambda *args, **kwargs: None)
		doc = frappe._dict(
			references=[frappe._dict(reference_doctype="Sales Invoice", reference_name="SI-1")]
		)

		with (
			patch.object(document_sync.frappe, "db", fake_db),
			patch.object(document_sync, "_sync_payment_jobs") as sync_jobs,
			patch.object(document_sync.frappe.db, "get_value", return_value="RJ-1"),
			patch.object(document_sync.frappe, "publish_realtime") as publish_realtime,
		):
			document_sync.sync_payment_entry(doc)
			sync_jobs.assert_called_once_with(("RJ-1",))
			self.assertEqual(len(fake_db.after_commit.callbacks), 1)
			publish_realtime.assert_not_called()
			fake_db.after_commit.callbacks[0]()

		publish_realtime.assert_called_once()

	def test_payment_rows_skip_unsubmitted_payment_entries(self):
		with (
			patch.object(
				document_sync.frappe.db,
				"get_all",
				return_value=[
					frappe._dict(parent="PE-1", reference_name="SI-1", allocated_amount=50),
				],
			),
			patch.object(document_sync.frappe.db, "get_value", return_value=0),
		):
			self.assertEqual(document_sync._service_payment_total(frappe._dict(), []), 0)

	def test_gate_pass_full_payment_uses_invoice_outstanding_amount(self):
		def get_value(doctype, name, fields=None, as_dict=False):
			if fields == "docstatus":
				return 1
			if as_dict:
				return frappe._dict(grand_total=220000, rounded_total=220000, outstanding_amount=0)
			return None

		with (
			patch.object(document_sync, "get_repair_job_sales_invoices", return_value=["SI-1"]),
			patch.object(document_sync, "_all_billable_components_submitted", return_value=True),
			patch.object(
				document_sync,
				"_get_settings",
				return_value=frappe._dict(gate_pass_payment_policy="Full Payment Required"),
			),
			patch.object(document_sync.frappe.db, "exists", return_value=True),
			patch.object(document_sync.frappe.db, "get_value", side_effect=get_value),
		):
			self.assertEqual(document_sync.validate_job_invoices_for_gate_pass("RJ-1"), ["SI-1"])

	def test_gate_pass_validation_rejects_stale_invoice_link_clearly(self):
		with (
			patch.object(document_sync, "get_repair_job_sales_invoices", return_value=["SI-MISSING"]),
			patch.object(
				document_sync,
				"_get_settings",
				return_value=frappe._dict(gate_pass_payment_policy="Full Payment Required"),
			),
			patch.object(document_sync.frappe.db, "exists", return_value=False),
			patch.object(document_sync, "_all_billable_components_submitted") as coverage,
		):
			with self.assertRaisesRegex(frappe.ValidationError, "no longer exists"):
				document_sync.validate_job_invoices_for_gate_pass("RJ-1")

		coverage.assert_not_called()

	def test_gate_pass_payment_not_required_allows_uninvoiced_job(self):
		with (
			patch.object(document_sync, "get_repair_job_sales_invoices", return_value=[]),
			patch.object(
				document_sync,
				"_get_settings",
				return_value=frappe._dict(gate_pass_payment_policy="Payment Not Required"),
			),
			patch.object(document_sync, "_all_billable_components_submitted") as coverage,
		):
			self.assertEqual(document_sync.validate_job_invoices_for_gate_pass("RJ-1"), [])
			coverage.assert_not_called()

	def test_gate_pass_button_check_allows_payment_not_required_without_invoice(self):
		job = frappe._dict(gate_pass=None, sales_invoices=[])
		job.check_permission = lambda permission: None
		with (
			patch.object(repair_job_module.frappe, "get_doc", return_value=job),
			patch.object(
				repair_job_module,
				"_get_settings",
				return_value=frappe._dict(gate_pass_payment_policy="Payment Not Required"),
			),
		):
			self.assertTrue(repair_job_module.can_create_final_release_gate_pass("RJ-1"))

	def test_gate_pass_button_check_rejects_invoice_required_job_without_invoice(self):
		job = frappe._dict(gate_pass=None, sales_invoices=[])
		job.check_permission = lambda permission: None
		with (
			patch.object(repair_job_module.frappe, "get_doc", return_value=job),
			patch.object(
				repair_job_module,
				"_get_settings",
				return_value=frappe._dict(gate_pass_payment_policy="Full Payment Required"),
			),
		):
			self.assertFalse(repair_job_module.can_create_final_release_gate_pass("RJ-1"))

	def test_gate_pass_button_check_preserves_invoice_and_existing_pass_paths(self):
		for job in (
			frappe._dict(gate_pass="GP-1", sales_invoices=[]),
			frappe._dict(gate_pass=None, sales_invoices=[frappe._dict(sales_invoice="SI-1")]),
		):
			job.check_permission = lambda permission: None
			with (
				patch.object(repair_job_module.frappe, "get_doc", return_value=job),
				patch.object(repair_job_module, "_get_settings") as settings,
			):
				self.assertTrue(repair_job_module.can_create_final_release_gate_pass("RJ-1"))
				settings.assert_not_called()

	def test_gate_pass_invoice_coverage_includes_pending_approval_services(self):
		component = frappe._dict(sales_invoice="SI-1", billable=True)
		with (
			patch.object(
				document_sync,
				"iter_repair_job_components",
				return_value=[(frappe._dict(status="Pending Approval"), component)],
			) as components,
			patch.object(
				document_sync.frappe,
				"get_all",
				return_value=[frappe._dict(name="SI-1", docstatus=1)],
			) as invoices,
		):
			self.assertTrue(document_sync._all_billable_components_submitted("RJ-1"))
			self.assertEqual(components.call_args.kwargs, {"billable_only": True})
			invoices.assert_called_once_with(
				"Sales Invoice",
				filters={"name": ["in", ["SI-1"]]},
				fields=["name", "docstatus"],
				limit_page_length=1,
			)

	def test_gate_pass_full_payment_rejects_outstanding_invoice(self):
		def get_value(doctype, name, fields=None, as_dict=False):
			if fields == "docstatus":
				return 1
			return frappe._dict(grand_total=220000, rounded_total=220000, outstanding_amount=1)

		with (
			patch.object(document_sync, "get_repair_job_sales_invoices", return_value=["SI-1"]),
			patch.object(document_sync, "_all_billable_components_submitted", return_value=True),
			patch.object(
				document_sync,
				"_get_settings",
				return_value=frappe._dict(gate_pass_payment_policy="Full Payment Required"),
			),
			patch.object(
				document_sync.frappe.db,
				"get_value",
				side_effect=get_value,
			),
			patch.object(document_sync.frappe.db, "exists", return_value=True),
		):
			with self.assertRaises(frappe.ValidationError):
				document_sync.validate_job_invoices_for_gate_pass("RJ-1")

	def test_gate_pass_rejects_partial_component_invoice_coverage(self):
		def get_value(doctype, name, fields=None, as_dict=False):
			if fields == "docstatus":
				return 1
			return frappe._dict(grand_total=220000, rounded_total=220000, outstanding_amount=0)

		with (
			patch.object(document_sync, "get_repair_job_sales_invoices", return_value=["SI-1"]),
			patch.object(document_sync, "_all_billable_components_submitted", return_value=False),
			patch.object(
				document_sync,
				"_get_settings",
				return_value=frappe._dict(gate_pass_payment_policy="Full Payment Required"),
			),
			patch.object(
				document_sync.frappe.db,
				"get_value",
				side_effect=get_value,
			),
			patch.object(document_sync.frappe.db, "exists", return_value=True),
		):
			with self.assertRaises(frappe.ValidationError):
				document_sync.validate_job_invoices_for_gate_pass("RJ-1")

	def test_labour_invoice_item_uses_billing_fields(self):
		job = frappe._dict(name="RJ-1", customer_vehicle="VEH-1", project="PROJ-1")
		service = frappe._dict(name="RJS-1", service_name="Brake service")
		row = frappe._dict(
			doctype="Repair Job Service Labour",
			name="LAB-1",
			description="Brake labour",
			item_code="LABOUR-ITEM",
			hours=4,
			billing_hours=2.5,
			billing_rate=60000,
			billing_amount=150000,
			legacy_repair_service_line=None,
		)
		component = ServiceComponent(service, row, "labour", "Labour")

		with patch.object(component_mapping.frappe.db, "get_value", return_value="Hour"):
			item = component_mapping._sales_invoice_item(job, service, component)

		self.assertEqual(item["qty"], 2.5)
		self.assertEqual(item["rate"], 60000)
		self.assertEqual(item["uom"], "Hour")

	def test_itemless_labour_is_rejected_before_invoice_mapping(self):
		job = frappe._dict(name="RJ-1", customer_vehicle="VEH-1", project="PROJ-1")
		service = frappe._dict(name="RJS-1", service_name="Brake service")
		row = frappe._dict(
			doctype="Repair Job Service Labour",
			name="LAB-1",
			description="Brake labour",
			item_code=None,
			billing_hours=2.5,
			billing_rate=60000,
			billing_amount=150000,
			legacy_repair_service_line=None,
		)
		component = ServiceComponent(service, row, "labour", "Labour")

		with self.assertRaises(frappe.ValidationError):
			component_mapping._sales_invoice_item(job, service, component)

	def test_itemless_stock_component_uses_nos_uom(self):
		job = frappe._dict(name="RJ-1", customer_vehicle="VEH-1", project="PROJ-1")
		service = frappe._dict(name="RJS-1", service_name="Cleaning service")
		row = frappe._dict(
			doctype="Repair Job Service Consumable",
			name="CON-1",
			description="Cleaning material",
			item_code=None,
			quantity=1,
			rate=10000,
			discount_percentage=0,
			legacy_repair_service_line=None,
		)
		component = ServiceComponent(service, row, "consumables", "Consumable")

		item = component_mapping._sales_invoice_item(job, service, component)

		self.assertIsNone(item["item_code"])
		self.assertEqual(item["item_name"], "Cleaning material")
		self.assertEqual(item["uom"], "Nos")

	def test_current_target_is_not_treated_as_another_draft(self):
		component = frappe._dict(sales_invoice="SINV-DRAFT-1")

		self.assertFalse(
			component_mapping._has_active_link(
				component,
				"Sales Invoice",
				"sales_invoice",
				current_target_name="SINV-DRAFT-1",
			)
		)

	def test_material_request_item_removal_resets_request_trace(self):
		doc = frappe._dict(name="MAT-MR-1", items=[])

		def get_all(doctype, **kwargs):
			if doctype == "Repair Job Service Part":
				return ["PART-1"]
			return []

		with (
			patch.object(document_sync.frappe.db, "table_exists", return_value=True),
			patch.object(document_sync.frappe, "get_all", side_effect=get_all),
			patch.object(document_sync.frappe.db, "set_value") as set_value,
		):
			document_sync._reconcile_component_links(
				doc,
				linked_field="material_request",
				linked_item_field="material_request_item",
				release_values={"requested_qty": 0, "stock_request_status": "Not Requested"},
			)

		set_value.assert_any_call(
			"Repair Job Service Part",
			"PART-1",
			{
				"material_request": None,
				"material_request_item": None,
				"requested_qty": 0,
				"stock_request_status": "Not Requested",
			},
			update_modified=False,
		)

	def test_material_request_sync_skips_component_doctypes_without_trace_field(self):
		doc = frappe._dict(
			name="MAT-MR-2",
			items=[
				frappe._dict(
					name="MRI-1",
					repair_component_doctype="Repair Job Service Part",
					repair_component_row="PART-1",
					qty=1,
				)
			],
		)
		meta_by_doctype = {
			"Repair Job Service Part": frappe._dict(get_field=lambda field: field == "material_request"),
			"Repair Job Service Labour": frappe._dict(get_field=lambda field: False),
			"Repair Job Service Consumable": frappe._dict(
				get_field=lambda field: field == "material_request"
			),
			"Repair Job Service Subcontracted Service": frappe._dict(get_field=lambda field: False),
		}

		def get_all(doctype, **kwargs):
			if doctype in {"Repair Job Service Part", "Repair Job Service Consumable"}:
				return []
			raise AssertionError(f"unexpected get_all call for {doctype}")

		with (
			patch.object(document_sync.frappe.db, "table_exists", return_value=True),
			patch.object(
				document_sync.frappe, "get_meta", side_effect=lambda doctype: meta_by_doctype[doctype]
			),
			patch.object(document_sync.frappe, "get_all", side_effect=get_all),
			patch.object(document_sync.frappe.db, "set_value") as set_value,
		):
			document_sync.sync_material_request(doc)

		set_value.assert_any_call(
			"Repair Job Service Part",
			"PART-1",
			{
				"material_request": "MAT-MR-2",
				"material_request_item": "MRI-1",
				"requested_qty": 1.0,
				"stock_request_status": "Requested",
			},
			update_modified=False,
		)

	def test_invoice_completeness_requires_every_component_to_be_submitted(self):
		components = [
			(frappe._dict(), frappe._dict(sales_invoice="SINV-1")),
			(frappe._dict(), frappe._dict(sales_invoice=None)),
		]
		with (
			patch.object(document_sync, "iter_repair_job_components", return_value=components),
			patch.object(
				document_sync.frappe,
				"get_all",
				return_value=[frappe._dict(name="SINV-1", docstatus=1)],
			) as invoices,
		):
			self.assertFalse(document_sync._all_billable_components_submitted("RJ-1"))
			document_sync.iter_repair_job_components.assert_called_once_with(
				"RJ-1",
				billable_only=True,
			)
			invoices.assert_called_once_with(
				"Sales Invoice",
				filters={"name": ["in", ["SINV-1"]]},
				fields=["name", "docstatus"],
				limit_page_length=1,
			)

		components[1][1].sales_invoice = "SINV-2"
		with (
			patch.object(document_sync, "iter_repair_job_components", return_value=components),
			patch.object(
				document_sync.frappe,
				"get_all",
				return_value=[
					frappe._dict(name="SINV-1", docstatus=1),
					frappe._dict(name="SINV-2", docstatus=1),
				],
			) as invoices,
		):
			self.assertTrue(document_sync._all_billable_components_submitted("RJ-1"))
			invoices.assert_called_once_with(
				"Sales Invoice",
				filters={"name": ["in", ["SINV-1", "SINV-2"]]},
				fields=["name", "docstatus"],
				limit_page_length=2,
			)

	def test_labour_invoice_item_preserves_zero_billing_rate(self):
		job = frappe._dict(name="RJ-1", customer_vehicle="VEH-1", project="PROJ-1")
		service = frappe._dict(name="RJS-1", service_name="Brake service")
		row = frappe._dict(
			doctype="Repair Job Service Labour",
			name="LAB-1",
			description="Brake labour",
			item_code="LABOUR-ITEM",
			billing_hours=2.5,
			billing_rate=0,
			legacy_repair_service_line=None,
		)
		component = ServiceComponent(service, row, "labour", "Labour")

		item = component_mapping._sales_invoice_item(job, service, component)

		self.assertEqual(item["rate"], 0)
