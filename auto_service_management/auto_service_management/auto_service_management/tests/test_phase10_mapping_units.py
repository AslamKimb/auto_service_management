import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	ServiceComponent,
)
from auto_service_management.auto_service_management.doctype.repair_job.repair_job import RepairJob
from auto_service_management.auto_service_management.integration.erpnext import (
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
		self.assertNotIn("before_submit", inspect.getsource(__import__(
			"auto_service_management.auto_service_management.doctype.repair_job.repair_job",
			fromlist=["RepairJob"],
		)))

	def test_sales_invoice_draft_validation_skips_service_status_gate(self):
		services = [frappe._dict(name="RJS-1", repair_job="RJ-1", status="Draft", service_name="Job service")]

		with patch.object(component_mapping.frappe, "get_all", return_value=services):
			component_mapping._validate_service_scope("RJ-1", {"RJS-1"}, None, document_label="Sales Invoice")

	def test_sales_invoice_submission_does_not_require_submitted_services(self):
		with (
			patch.object(
				document_sync,
				"_trace_items",
				return_value=[frappe._dict(repair_job_service="RJS-1")],
			),
			patch.object(document_sync.frappe.db, "get_value", return_value=0),
		):
			document_sync._validate_invoice_service_submission(frappe._dict())

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
			patch.object(document_sync.frappe.db, "get_all", return_value=[
				frappe._dict(parent="PE-1", reference_name="SI-1", allocated_amount=50),
			]),
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
				document_sync.frappe,
				"get_single",
				return_value=frappe._dict(gate_pass_payment_policy="Full Payment Required"),
			),
			patch.object(document_sync.frappe.db, "get_value", side_effect=get_value),
		):
			self.assertEqual(document_sync.validate_job_invoices_for_gate_pass("RJ-1"), ["SI-1"])

	def test_gate_pass_full_payment_rejects_outstanding_invoice(self):
		with (
			patch.object(document_sync, "get_repair_job_sales_invoices", return_value=["SI-1"]),
			patch.object(document_sync, "_all_billable_components_submitted", return_value=True),
			patch.object(
				document_sync.frappe,
				"get_single",
				return_value=frappe._dict(gate_pass_payment_policy="Full Payment Required"),
			),
			patch.object(
				document_sync.frappe.db,
				"get_value",
				return_value=frappe._dict(grand_total=220000, rounded_total=220000, outstanding_amount=1),
			),
		):
			with self.assertRaises(frappe.ValidationError):
				document_sync.validate_job_invoices_for_gate_pass("RJ-1")

	def test_gate_pass_rejects_partial_component_invoice_coverage(self):
		with (
			patch.object(document_sync, "get_repair_job_sales_invoices", return_value=["SI-1"]),
			patch.object(document_sync, "_all_billable_components_submitted", return_value=False),
			patch.object(
				document_sync.frappe,
				"get_single",
				return_value=frappe._dict(gate_pass_payment_policy="Full Payment Required"),
			),
			patch.object(
				document_sync.frappe.db,
				"get_value",
				return_value=frappe._dict(grand_total=220000, rounded_total=220000, outstanding_amount=0),
			),
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
			patch.object(document_sync.frappe.db, "get_value", return_value=1),
		):
			self.assertFalse(document_sync._all_billable_components_submitted("RJ-1"))
			document_sync.iter_repair_job_components.assert_called_once_with(
				"RJ-1",
				service_statuses={"Approved", "Completed"},
				billable_only=True,
			)

		components[1][1].sales_invoice = "SINV-2"
		with (
			patch.object(document_sync, "iter_repair_job_components", return_value=components),
			patch.object(document_sync.frappe.db, "get_value", return_value=1),
		):
			self.assertTrue(document_sync._all_billable_components_submitted("RJ-1"))

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
