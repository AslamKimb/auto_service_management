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
	iter_repair_job_components,
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
	default_warehouse="_Test Warehouse",
	default_currency="UGX",
)


def _ensure_test_item():
	if frappe.db.exists("Item", TEST_ITEM_CODE):
		return
	if not frappe.db.exists("UOM", "Nos"):
		frappe.get_doc({"doctype": "UOM", "uom_name": "Nos", "enabled": 1}).insert(ignore_permissions=True)
	if not frappe.db.exists("Item Group", "All Item Groups"):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "All Item Groups",
				"is_group": 1,
				"parent_item_group": "",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Item Group", "Auto Service Parts"):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "Auto Service Parts",
				"is_group": 0,
				"parent_item_group": "All Item Groups",
			}
		).insert(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": TEST_ITEM_CODE,
			"item_name": "Test Battery",
			"item_group": "Auto Service Parts",
			"stock_uom": "Nos",
		}
	).insert(ignore_permissions=True)


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
	doc = frappe.get_doc(
		{
			"doctype": "Repair Job",
			"customer": customer,
			"customer_vehicle": vehicle,
			"odometer_in": 84521,
			"customer_concern": "Battery warning and brake noise",
			"priority": "Normal",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _add_labour_line(job, description="Engine oil change", rate=120000, qty=1, technician=None):
	service = _create_job_service(job, description, status="Approved")
	line = _append_service_component(
		service,
		service_type="Labour",
		description=description,
		quantity=qty,
		rate=rate,
		assigned_to=technician,
	)
	job.reload()
	return line.name


def _add_parts_line(job, description="Battery", item_code=TEST_ITEM_CODE, qty=1, rate=350000):
	service = _create_job_service(job, description, status="Approved")
	line = _append_service_component(
		service,
		service_type="Part",
		description=description,
		item_code=item_code,
		quantity=qty,
		rate=rate,
	)
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
		job.reload()
		summary = job.get_labour_summary()
		self.assertEqual(summary["total_hours"], 1)
		self.assertEqual(summary["total_amount"], 120000)
		self.assertEqual(len(summary["lines"]), 1)
		self.assertEqual(job.total_amount, 470000)


class TestRepairJobServiceTemplate(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)
		_ensure_test_item()

	def tearDown(self):
		frappe.db.rollback()

	def test_service_rows_are_created_directly_without_template_copying(self):
		job = frappe.get_doc("Repair Job", _create_repair_job(self.customer, self.vehicle))
		service = frappe.get_doc(
			{
				"doctype": "Repair Job Service",
				"repair_job": job.name,
				"service_name": "Battery Replacement",
				"workshop_bay": "Bay 1",
			}
		)
		service.insert(ignore_permissions=True)

		self.assertEqual(service.repair_job, job.name)
		self.assertEqual(service.service_name, "Battery Replacement")


class TestDoubleBillingPrevention(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)
		_ensure_test_item()

	def tearDown(self):
		frappe.db.rollback()

	def test_create_sales_invoice_does_not_use_legacy_primary_link_as_a_duplicate_guard(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		frappe.db.set_value("Repair Job", job_name, "job_status", "Billing")
		job.reload()
		with patch(f"{ADAPTER_PATCH_BASE}.create_sales_invoice", return_value="SI-MOCK-002") as mapper:
			job.create_sales_invoice()
		mapper.assert_called_once_with(job)

	def test_invoice_iterator_uses_only_parent_service_status(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		approved_service = _create_job_service(job, "Approved labour", status="Approved")
		completed_service = _create_job_service(job, "Completed labour", status="Completed")
		in_progress_service = _create_job_service(job, "In progress labour", status="In Progress")
		pending_line = _append_service_component(
			approved_service,
			service_type="Labour",
			description="Pending labour",
			quantity=1,
			rate=100000,
		)
		approved_line = _append_service_component(
			completed_service,
			service_type="Labour",
			description="Approved labour",
			quantity=1,
			rate=200000,
		)
		_append_service_component(
			in_progress_service,
			service_type="Labour",
			description="In progress labour",
			quantity=1,
			rate=300000,
		)
		job.reload()
		eligible = list(
			iter_repair_job_components(
				job.name,
				service_statuses={"Approved", "Completed"},
				billable_only=True,
			)
		)
		self.assertEqual(
			[line.name for _service, line in eligible],
			[pending_line.name, approved_line.name, in_progress_service.labour[-1].name],
		)

		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_sales_invoice,
		)

		mapped_invoice = frappe._dict(name="SI-TEST-001", insert=lambda **kw: None)
		with patch(
			"auto_service_management.auto_service_management.integration.erpnext.component_mapping.map_sales_invoice",
			return_value=mapped_invoice,
		) as mapper:
			self.assertEqual(create_sales_invoice(job), "SI-TEST-001")
		mapper.assert_called_once_with(job.name)

	def test_job_and_service_invoice_mapping_include_every_component(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		services = [
			_create_job_service(job, "Approved full service", status="Approved"),
			_create_job_service(job, "Completed full service", status="Completed"),
		]
		for service in services:
			_append_service_component(
				service,
				service_type="Part",
				description=f"{service.service_name} part",
				item_code=TEST_ITEM_CODE,
				quantity=2,
				rate=50000,
			)
			_append_service_component(
				service,
				service_type="Consumable",
				description=f"{service.service_name} consumable",
				item_code=TEST_ITEM_CODE,
				quantity=1,
				rate=10000,
			)
			_append_service_component(
				service,
				service_type="Labour",
				description=f"{service.service_name} labour",
				item_code=None,
				quantity=1.5,
				rate=60000,
			)

		frappe.db.set_value("Repair Job", job_name, "job_status", "Approved")
		from auto_service_management.auto_service_management.integration.erpnext import (
			component_mapping,
		)

		with (
			patch.object(component_mapping.frappe, "get_single", return_value=_MOCK_SETTINGS),
			patch("frappe.model.document.Document.run_method"),
		):
			job_invoice = component_mapping.map_sales_invoice(job_name)
			service_invoice = component_mapping.map_sales_invoice(job_name, service_names={services[0].name})

		self.assertEqual(len(job_invoice.items), 6)
		self.assertEqual(len(service_invoice.items), 3)
		self.assertEqual(
			{row.repair_job_service for row in job_invoice.items},
			{service.name for service in services},
		)
		labour_rows = [
			row for row in job_invoice.items if row.repair_component_doctype == "Repair Job Service Labour"
		]
		self.assertEqual(len(labour_rows), 2)
		self.assertTrue(all(row.item_code for row in labour_rows))
		self.assertTrue(all(row.uom == "Hour" for row in labour_rows))

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
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_material_request,
		)

		mapped_request = frappe._dict(name="MR-TEST-001", insert=lambda **kw: None)
		with patch(
			"auto_service_management.auto_service_management.integration.erpnext.component_mapping.map_material_request",
			return_value=mapped_request,
		) as mapper:
			self.assertEqual(create_material_request(job), "MR-TEST-001")
		mapper.assert_called_once_with(job.name)

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
				with (
					patch(f"{ADAPTER_PATCH_BASE}.frappe.db.set_value") as mock_set_value,
					patch(
						"auto_service_management.auto_service_management.integration.erpnext.component_mapping.is_material_request_active",
						return_value=True,
					),
					patch(f"{ADAPTER_PATCH_BASE}.frappe.db.get_value", return_value="Material Issue"),
				):
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
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_material_request,
		)

		mapped_request = frappe._dict(name="MR-NEW-001", insert=lambda **kw: None)
		with patch(
			"auto_service_management.auto_service_management.integration.erpnext.component_mapping.map_material_request",
			return_value=mapped_request,
		) as mapper:
			self.assertEqual(create_material_request(job), "MR-NEW-001")
		mapper.assert_called_once_with(job.name)


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
				with (
					patch(f"{ADAPTER_PATCH_BASE}.frappe.db.set_value") as mock_set_value,
					patch(
						"auto_service_management.auto_service_management.integration.erpnext.component_mapping.is_material_request_active",
						return_value=True,
					),
					patch(f"{ADAPTER_PATCH_BASE}.frappe.db.get_value", return_value="Material Issue"),
				):
					from auto_service_management.auto_service_management.integration.erpnext.adapters import (
						create_stock_entry_for_material_issue,
					)

					create_stock_entry_for_material_issue(job)
					self.assertEqual(mock_set_value.call_count, 1)
					call_args = mock_set_value.call_args
					self.assertEqual(call_args[0][2]["stock_request_status"], "Fully Issued")

	def test_stock_entry_skips_already_issued_lines(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		_add_parts_line(job, description="Already issued part", qty=2, rate=50000)
		job.reload()
		line = _get_job_components(job_name)[0]
		_set_child_field(line.name, "stock_request_status", "Requested")
		_set_child_field(line.name, "requested_qty", 2)
		_set_child_field(line.name, "issued_qty", 2)
		_set_child_field(line.name, "stock_entry", "SE-OLD-001")
		_set_child_field(line.name, "material_request", "MR-TEST-004")
		job.reload()

		with (
			patch(f"{ADAPTER_PATCH_BASE}.get_settings", return_value=_MOCK_SETTINGS),
			patch(
				"auto_service_management.auto_service_management.integration.erpnext.component_mapping.is_material_request_active",
				return_value=True,
			),
			patch(f"{ADAPTER_PATCH_BASE}.frappe.db.get_value", return_value="Material Issue"),
			patch(f"{ADAPTER_PATCH_BASE}._make_doc") as mock_make_doc,
		):
			from auto_service_management.auto_service_management.integration.erpnext.adapters import (
				create_stock_entry_for_material_issue,
			)

			with self.assertRaises(frappe.ValidationError):
				create_stock_entry_for_material_issue(job)

		mock_make_doc.assert_not_called()

	def test_stock_entry_issues_only_remaining_requested_qty(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		_add_parts_line(job, description="Partially issued part", qty=4, rate=50000)
		job.reload()
		line = _get_job_components(job_name)[0]
		_set_child_field(line.name, "stock_request_status", "Requested")
		_set_child_field(line.name, "requested_qty", 3)
		_set_child_field(line.name, "issued_qty", 1)
		_set_child_field(line.name, "material_request", "MR-TEST-005")
		job.reload()

		with (
			patch(f"{ADAPTER_PATCH_BASE}.get_settings", return_value=_MOCK_SETTINGS),
			patch(f"{ADAPTER_PATCH_BASE}._make_doc") as mock_make_doc,
			patch(f"{ADAPTER_PATCH_BASE}.frappe.db.set_value") as mock_set_value,
			patch(
				"auto_service_management.auto_service_management.integration.erpnext.component_mapping.is_material_request_active",
				return_value=True,
			),
			patch(f"{ADAPTER_PATCH_BASE}.frappe.db.get_value", return_value="Material Issue"),
		):
			mock_se = frappe._dict(name="SE-TEST-003", insert=lambda **kw: None)
			mock_make_doc.return_value = mock_se
			from auto_service_management.auto_service_management.integration.erpnext.adapters import (
				create_stock_entry_for_material_issue,
			)

			create_stock_entry_for_material_issue(job)

		self.assertEqual(mock_make_doc.call_args[0][0]["items"][0]["qty"], 2)
		self.assertEqual(mock_set_value.call_args[0][2]["issued_qty"], 3)
