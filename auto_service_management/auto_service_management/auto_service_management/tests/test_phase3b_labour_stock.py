# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

"""Tests for labour summaries, double-billing prevention, requested/issued
quantity tracking, and duplicate stock guards.

Phase 3b: covers the two pending items in IMPLEMENTATION_PLAN.md.
"""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	COMPONENT_TABLE_BY_TYPE,
)
from auto_service_management.auto_service_management.tests.test_controllers_integration import (
	_append_service_component,
	_create_job_service,
	_create_test_vehicle,
	_ensure_erpnext_basics,
	_get_job_components,
	_get_or_create_customer,
)

TEST_ITEM_CODE = "TEST-BATTERY-001"

ADAPTER_PATCH_BASE = "auto_service_management.auto_service_management.integration.erpnext.adapters"

_MOCK_SETTINGS = frappe._dict(
	company="_Test Company",
	selling_price_list="_Test Selling Price List",
	price_list="_Test Selling Price List",
	source_warehouse="_Test Warehouse",
	default_currency="UGX",
)


def _ensure_test_item():
	if frappe.db.exists("Item", TEST_ITEM_CODE):
		return
	if not frappe.db.exists("UOM", "Nos"):
		frappe.get_doc({"doctype": "UOM", "uom_name": "Nos", "enabled": 1}).insert(ignore_permissions=True)
	if not frappe.db.exists("Item Group", "All Item Groups"):
		frappe.get_doc({"doctype": "Item Group", "item_group_name": "All Item Groups", "is_group": 1, "parent_item_group": ""}).insert(ignore_permissions=True)
	if not frappe.db.exists("Item Group", "Auto Service Parts"):
		frappe.get_doc({"doctype": "Item Group", "item_group_name": "Auto Service Parts", "is_group": 0, "parent_item_group": "All Item Groups"}).insert(ignore_permissions=True)
	frappe.get_doc({"doctype": "Item", "item_code": TEST_ITEM_CODE, "item_name": "Test Battery", "item_group": "Auto Service Parts", "stock_uom": "Nos"}).insert(ignore_permissions=True)


def _set_child_field(child_docname, fieldname, value):
	for definition in COMPONENT_TABLE_BY_TYPE.values():
		if frappe.db.exists(definition["doctype"], child_docname):
			frappe.db.set_value(definition["doctype"], child_docname, fieldname, value)
			return
	frappe.throw(f"Unknown repair service component row: {child_docname}")


def _set_parent_field(parent_docname, fieldname, value):
	frappe.db.set_value("Repair Job", parent_docname, fieldname, value)


def _create_repair_job(customer=None, vehicle=None):
	if not customer:
		customer = _get_or_create_customer()
	if not vehicle:
		vehicle = _create_test_vehicle(customer)
	doc = frappe.get_doc({"doctype": "Repair Job", "customer": customer, "customer_vehicle": vehicle, "odometer_in": 84521, "customer_concern": "Battery warning and brake noise", "priority": "Normal"})
	doc.insert(ignore_permissions=True)
	return doc.name


def _add_labour_line(job, description="Engine oil change", rate=120000, qty=1, technician=None):
	service = _create_job_service(job, description, status="Approved")
	line = _append_service_component(service, service_type="Labour", description=description, quantity=qty, rate=rate, assigned_to=technician, status="Approved")
	job.reload()
	return line.name


def _add_parts_line(job, description="Battery", item_code=TEST_ITEM_CODE, qty=1, rate=350000):
	service = _create_job_service(job, description, status="Approved")
	line = _append_service_component(service, service_type="Part", description=description, item_code=item_code, quantity=qty, rate=rate, status="Approved")
	job.reload()
	return line.name


def _add_subcontract_line(job, description="Engine rebuild", rate=500000):
	service = _create_job_service(job, description, status="Approved")
	line = _append_service_component(service, service_type="Subcontracted Service", description=description, quantity=1, rate=rate, status="Approved")
	job.reload()
	return line.name


class TestLabourSummary(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)
		_ensure_test_item()

	def tearDown(self):
		frappe.db.rollback()

	def test_labour_summary_empty(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		summary = job.get_labour_summary()
		self.assertEqual(summary["total_hours"], 0)
		self.assertEqual(summary["total_amount"], 0)
		self.assertEqual(summary["lines"], [])

	def test_labour_summary_single_line(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		_add_labour_line(job, description="Engine oil change", rate=120000, qty=2)
		job.reload()
		summary = job.get_labour_summary()
		self.assertEqual(summary["total_hours"], 2)
		self.assertEqual(summary["total_amount"], 240000)
		self.assertEqual(len(summary["lines"]), 1)
		self.assertEqual(summary["lines"][0]["description"], "Engine oil change")
		self.assertEqual(summary["lines"][0]["hours"], 2)
		self.assertEqual(summary["lines"][0]["amount"], 240000)

	def test_labour_summary_multiple_lines(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		_add_labour_line(job, description="Battery replacement", rate=150000, qty=1)
		_add_labour_line(job, description="Brake pad replacement", rate=100000, qty=2)
		job.reload()
		summary = job.get_labour_summary()
		self.assertEqual(summary["total_hours"], 3)
		self.assertEqual(summary["total_amount"], 350000)
		self.assertEqual(len(summary["lines"]), 2)

	def test_labour_summary_excludes_non_labour(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		_add_parts_line(job, description="Battery", qty=1, rate=350000)
		_add_labour_line(job, description="Labour only", rate=120000, qty=1)
		_add_subcontract_line(job, description="Engine rebuild", rate=500000)
		job.reload()
		summary = job.get_labour_summary()
		self.assertEqual(summary["total_hours"], 1)
		self.assertEqual(summary["total_amount"], 120000)
		self.assertEqual(len(summary["lines"]), 1)
		self.assertEqual(job.total_amount, 970000)


class TestRepairJobServiceTemplate(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)
		_ensure_test_item()

	def tearDown(self):
		frappe.db.rollback()

	def test_template_copies_components_into_job_service(self):
		template_name = "Test Battery Replacement Template"
		if frappe.db.exists("Repair Service Template", template_name):
			frappe.delete_doc("Repair Service Template", template_name, ignore_permissions=True)
		template = frappe.get_doc(
			{
				"doctype": "Repair Service Template",
				"template_name": template_name,
				"service_name": "Battery Replacement",
				"default_billable": 1,
				"parts": [
					{
						"description": "Battery",
						"item_code": TEST_ITEM_CODE,
						"quantity": 1,
						"rate": 350000,
					}
				],
				"consumables": [
					{
						"description": "Terminal grease",
						"item_code": TEST_ITEM_CODE,
						"quantity": 1,
						"rate": 10000,
					}
				],
				"labour": [
					{
						"description": "Battery fitment labour",
						"estimated_hours": 1,
						"rate": 120000,
					}
				],
			}
		)
		template.insert(ignore_permissions=True)

		job = frappe.get_doc("Repair Job", _create_repair_job(self.customer, self.vehicle))
		service = frappe.get_doc(
			{
				"doctype": "Repair Job Service",
				"repair_job": job.name,
				"repair_service_template": template.name,
				"service_name": "Battery Replacement",
			}
		)
		service.insert(ignore_permissions=True)

		self.assertEqual(len(service.parts), 1)
		self.assertEqual(len(service.consumables), 1)
		self.assertEqual(len(service.labour), 1)
		self.assertEqual(service.total_amount, 480000)


class TestDoubleBillingPrevention(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)
		_ensure_test_item()

	def tearDown(self):
		frappe.db.rollback()

	def test_create_sales_invoice_blocks_duplicate(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		line_name = _add_labour_line(job, description="Labour X", rate=100000, qty=1)
		_set_child_field(line_name, "status", "Completed")
		job.reload()
		_set_parent_field(job_name, "sales_invoice", "SI-MOCK-001")
		job.reload()
		with self.assertRaises(frappe.ValidationError):
			job.create_sales_invoice()

	def test_invoice_only_includes_completed_lines(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		completed_line = _add_labour_line(job, description="Completed labour", rate=100000, qty=1)
		_set_child_field(completed_line, "status", "Completed")
		_add_labour_line(job, description="Pending labour", rate=200000, qty=1)
		job.reload()
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_sales_invoice,
		)

		with patch(f"{ADAPTER_PATCH_BASE}.get_settings", return_value=_MOCK_SETTINGS):
			with patch(f"{ADAPTER_PATCH_BASE}._make_doc") as mock_make_doc:
				mock_si = frappe._dict(name="SI-TEST-001", insert=lambda **kw: None)
				mock_make_doc.return_value = mock_si
				with patch(f"{ADAPTER_PATCH_BASE}.frappe.db.set_value"):
					create_sales_invoice(job)
		self.assertTrue(mock_make_doc.called)
		doc_kwargs = mock_make_doc.call_args[0][0]
		items = doc_kwargs.get("items", [])
		item_names = [i.get("item_name") or i.get("description", "") for i in items]
		self.assertIn("Completed labour", item_names)
		self.assertNotIn("Pending labour", item_names)
		self.assertEqual(items[0]["repair_job"], job.name)
		self.assertEqual(items[0]["customer_vehicle"], job.customer_vehicle)
		self.assertTrue(items[0]["repair_job_service"])
		self.assertEqual(items[0]["repair_component_doctype"], "Repair Job Service Labour")
		self.assertEqual(items[0]["repair_component_row"], completed_line)
		self.assertEqual(items[0]["repair_service_line"], completed_line)

	def test_material_request_blocks_duplicate_for_active_line(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		_add_parts_line(job, description="Brake pads", qty=2, rate=50000)
		job.reload()
		line = _get_job_components(job_name)[0]
		_set_child_field(line.name, "stock_request_status", "Requested")
		_set_child_field(line.name, "requested_qty", 2)
		_set_child_field(line.name, "material_request", "MR-MOCK-001")
		job.reload()
		with self.assertRaises(frappe.ValidationError):
			job.create_material_request()


class TestRequestedIssuedQtyTracking(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)
		_ensure_test_item()

	def tearDown(self):
		frappe.db.rollback()

	def test_requested_qty_set_on_material_request_creation(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		_add_parts_line(job, description="Air filter", qty=3, rate=25000)
		job.reload()
		with patch(f"{ADAPTER_PATCH_BASE}.get_settings", return_value=_MOCK_SETTINGS):
			with patch(f"{ADAPTER_PATCH_BASE}._make_doc") as mock_make_doc:
				mock_mr = frappe._dict(name="MR-TEST-001", insert=lambda **kw: None)
				mock_make_doc.return_value = mock_mr
				with patch(f"{ADAPTER_PATCH_BASE}.frappe.db.set_value") as mock_set_value:
					from auto_service_management.auto_service_management.integration.erpnext.adapters import (
						create_material_request,
					)

					create_material_request(job)
					self.assertTrue(mock_set_value.called)
					call_args = mock_set_value.call_args
					self.assertEqual(call_args[0][0], "Repair Job Service Part")
					self.assertEqual(call_args[0][2]["requested_qty"], 3)
					self.assertEqual(call_args[0][2]["material_request"], "MR-TEST-001")
					self.assertEqual(call_args[0][2]["stock_request_status"], "Requested")

	def test_issued_qty_set_on_stock_entry_creation(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		_add_parts_line(job, description="Brake pads", qty=4, rate=80000)
		job.reload()
		line = _get_job_components(job_name)[0]
		_set_child_field(line.name, "stock_request_status", "Requested")
		_set_child_field(line.name, "requested_qty", 4)
		_set_child_field(line.name, "material_request", "MR-TEST-002")
		job.reload()
		with patch(f"{ADAPTER_PATCH_BASE}.get_settings", return_value=_MOCK_SETTINGS):
			with patch(f"{ADAPTER_PATCH_BASE}._make_doc") as mock_make_doc:
				mock_se = frappe._dict(name="SE-TEST-001", insert=lambda **kw: None)
				mock_make_doc.return_value = mock_se
				with patch(f"{ADAPTER_PATCH_BASE}.frappe.db.set_value") as mock_set_value:
					from auto_service_management.auto_service_management.integration.erpnext.adapters import (
						create_stock_entry_for_material_issue,
					)

					create_stock_entry_for_material_issue(job)
					self.assertTrue(mock_set_value.called)
					call_args = mock_set_value.call_args
					self.assertEqual(call_args[0][0], "Repair Job Service Part")
					self.assertEqual(call_args[0][2]["issued_qty"], 4)
					self.assertEqual(call_args[0][2]["stock_entry"], "SE-TEST-001")
					self.assertEqual(call_args[0][2]["stock_request_status"], "Fully Issued")

	def test_material_request_cancelled_allows_re_request(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		_add_parts_line(job, description="Oil filter", qty=1, rate=20000)
		job.reload()
		line = _get_job_components(job_name)[0]
		_set_child_field(line.name, "stock_request_status", "Cancelled")
		_set_child_field(line.name, "requested_qty", 1)
		_set_child_field(line.name, "material_request", "MR-CANCELLED-001")
		job.reload()
		with patch(f"{ADAPTER_PATCH_BASE}.get_settings", return_value=_MOCK_SETTINGS):
			with patch(f"{ADAPTER_PATCH_BASE}._make_doc") as mock_make_doc:
				mock_mr = frappe._dict(name="MR-NEW-001", insert=lambda **kw: None)
				mock_make_doc.return_value = mock_mr
				with patch(f"{ADAPTER_PATCH_BASE}.frappe.db.set_value"):
					from auto_service_management.auto_service_management.integration.erpnext.adapters import (
						create_material_request,
					)

					mr_name = create_material_request(job)
					self.assertEqual(mr_name, "MR-NEW-001")


class TestShortageAndStockGuard(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)
		_ensure_test_item()

	def tearDown(self):
		frappe.db.rollback()

	def test_shortage_detection_when_issued_lt_requested(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		_add_parts_line(job, description="Brake discs", qty=4, rate=80000)
		job.reload()
		line = _get_job_components(job_name)[0]
		_set_child_field(line.name, "stock_request_status", "Requested")
		_set_child_field(line.name, "requested_qty", 4)
		_set_child_field(line.name, "issued_qty", 2)
		_set_child_field(line.name, "material_request", "MR-PARTIAL-001")
		job.reload()
		shortages = job.get_shortage_report()
		self.assertEqual(len(shortages), 1)
		self.assertEqual(shortages[0]["shortage_qty"], 2)
		self.assertEqual(shortages[0]["needed_qty"], 4)
		self.assertEqual(shortages[0]["issued_qty"], 2)

	def test_stock_entry_only_covers_requested_lines(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		_add_parts_line(job, description="Requested part", qty=2, rate=50000)
		_add_parts_line(job, description="Not requested part", qty=1, rate=30000)
		job.reload()
		requested_line = _get_job_components(job_name)[0]
		_set_child_field(requested_line.name, "stock_request_status", "Requested")
		_set_child_field(requested_line.name, "requested_qty", 2)
		_set_child_field(requested_line.name, "material_request", "MR-TEST-003")
		job.reload()
		with patch(f"{ADAPTER_PATCH_BASE}.get_settings", return_value=_MOCK_SETTINGS):
			with patch(f"{ADAPTER_PATCH_BASE}._make_doc") as mock_make_doc:
				mock_se = frappe._dict(name="SE-TEST-002", insert=lambda **kw: None)
				mock_make_doc.return_value = mock_se
				with patch(f"{ADAPTER_PATCH_BASE}.frappe.db.set_value") as mock_set_value:
					from auto_service_management.auto_service_management.integration.erpnext.adapters import (
						create_stock_entry_for_material_issue,
					)

					create_stock_entry_for_material_issue(job)
					self.assertEqual(mock_set_value.call_count, 1)
					call_args = mock_set_value.call_args
					self.assertEqual(call_args[0][2]["stock_request_status"], "Fully Issued")

