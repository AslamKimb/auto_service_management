import pathlib

content = '''# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

\"\"\"Tests for labour summaries, double-billing prevention, requested/issued
quantity tracking, and duplicate stock guards.

Phase 3b: covers the two pending items in IMPLEMENTATION_PLAN.md.
\"\"\"

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from auto_service_management.auto_service_management.tests.test_controllers_integration import (
\t_create_test_vehicle,
\t_ensure_erpnext_basics,
\t_get_or_create_customer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_repair_job(customer=None, vehicle=None):
\tif not customer:
\t\tcustomer = _get_or_create_customer()
\tif not vehicle:
\t\tvehicle = _create_test_vehicle(customer)
\tdoc = frappe.get_doc(
\t\t{
\t\t\t\"doctype\": \"Repair Job\",
\t\t\t\"customer\": customer,
\t\t\t\"customer_vehicle\": vehicle,
\t\t\t\"odometer_in\": 84521,
\t\t\t\"customer_concern\": \"Battery warning and brake noise\",
\t\t\t\"priority\": \"Normal\",
\t\t}
\t)
\tdoc.insert(ignore_permissions=True)
\treturn doc.name


def _add_labour_line(job, description=\"Engine oil change\", rate=120000, qty=1, technician=None):
\tjob.append(
\t\t\"service_lines\",
\t\t{
\t\t\t\"service_type\": \"Labour\",
\t\t\t\"service_description\": description,
\t\t\t\"quantity\": qty,
\t\t\t\"rate\": rate,
\t\t\t\"assigned_to\": technician,
\t\t\t\"status\": \"Approved\",
\t\t},
\t)
\tjob.save()
\tjob.reload()
\treturn job.service_lines[-1].name


def _add_parts_line(job, description=\"Battery\", item_code=\"TEST-BATTERY-001\", qty=1, rate=350000):
\tjob.append(
\t\t\"service_lines\",
\t\t{
\t\t\t\"service_type\": \"Parts\",
\t\t\t\"service_description\": description,
\t\t\t\"item_code\": item_code,
\t\t\t\"quantity\": qty,
\t\t\t\"rate\": rate,
\t\t\t\"status\": \"Approved\",
\t\t},
\t)
\tjob.save()
\tjob.reload()
\treturn job.service_lines[-1].name


def _add_subcontract_line(job, description=\"Engine rebuild\", rate=500000):
\tjob.append(
\t\t\"service_lines\",
\t\t{
\t\t\t\"service_type\": \"Subcontract\",
\t\t\t\"service_description\": description,
\t\t\t\"quantity\": 1,
\t\t\t\"rate\": rate,
\t\t\t\"status\": \"Approved\",
\t\t},
\t)
\tjob.save()
\tjob.reload()
\treturn job.service_lines[-1].name


# ---------------------------------------------------------------------------
# Labour Summary Tests
# ---------------------------------------------------------------------------


class TestLabourSummary(IntegrationTestCase):
\tdef setUp(self):
\t\tself.customer = _get_or_create_customer()
\t\tself.vehicle = _create_test_vehicle(self.customer)

\tdef tearDown(self):
\t\tfrappe.db.rollback()

\tdef test_labour_summary_empty(self):
\t\tjob_name = _create_repair_job(self.customer, self.vehicle)
\t\tjob = frappe.get_doc(\"Repair Job\", job_name)
\t\tsummary = job.get_labour_summary()
\t\tself.assertEqual(summary[\"total_hours\"], 0)
\t\tself.assertEqual(summary[\"total_amount\"], 0)
\t\tself.assertEqual(summary[\"lines\"], [])

\tdef test_labour_summary_single_line(self):
\t\tjob_name = _create_repair_job(self.customer, self.vehicle)
\t\tjob = frappe.get_doc(\"Repair Job\", job_name)
\t\t_add_labour_line(job, description=\"Engine oil change\", rate=120000, qty=2)
\t\tjob.reload()
\t\tsummary = job.get_labour_summary()
\t\tself.assertEqual(summary[\"total_hours\"], 2)
\t\tself.assertEqual(summary[\"total_amount\"], 240000)
\t\tself.assertEqual(len(summary[\"lines\"]), 1)
\t\tself.assertEqual(summary[\"lines\"][0][\"description\"], \"Engine oil change\")
\t\tself.assertEqual(summary[\"lines\"][0][\"hours\"], 2)
\t\tself.assertEqual(summary[\"lines\"][0][\"amount\"], 240000)

\tdef test_labour_summary_multiple_lines(self):
\t\tjob_name = _create_repair_job(self.customer, self.vehicle)
\t\tjob = frappe.get_doc(\"Repair Job\", job_name)
\t\t_add_labour_line(job, description=\"Battery replacement\", rate=150000, qty=1)
\t\t_add_labour_line(job, description=\"Brake pad replacement\", rate=100000, qty=2)
\t\tjob.reload()
\t\tsummary = job.get_labour_summary()
\t\tself.assertEqual(summary[\"total_hours\"], 3)
\t\tself.assertEqual(summary[\"total_amount\"], 350000)
\t\tself.assertEqual(len(summary[\"lines\"]), 2)

\tdef test_labour_summary_excludes_non_labour(self):
\t\tjob_name = _create_repair_job(self.customer, self.vehicle)
\t\tjob = frappe.get_doc(\"Repair Job\", job_name)
\t\t_add_parts_line(job, description=\"Battery\", qty=1, rate=350000)
\t\t_add_labour_line(job, description=\"Labour only\", rate=120000, qty=1)
\t\t_add_subcontract_line(job, description=\"Engine rebuild\", rate=500000)
\t\tjob.reload()
\t\tsummary = job.get_labour_summary()
\t\tself.assertEqual(summary[\"total_hours\"], 1)
\t\tself.assertEqual(summary[\"total_amount\"], 120000)
\t\tself.assertEqual(len(summary[\"lines\"]), 1)
\t\tself.assertEqual(job.total_amount, 970000)

\tdef test_cached_labour_totals_update_on_save(self):
\t\tjob_name = _create_repair_job(self.customer, self.vehicle)
\t\tjob = frappe.get_doc(\"Repair Job\", job_name)
\t\t_add_labour_line(job, description=\"Labour A\", rate=100000, qty=3)
\t\tjob.reload()
\t\tself.assertEqual(job.labour_total_hours, 3)
\t\tself.assertEqual(job.labour_total_amount, 300000)


# ---------------------------------------------------------------------------
# Double-Billing Prevention Tests
# ---------------------------------------------------------------------------


class TestDoubleBillingPrevention(IntegrationTestCase):
\tdef setUp(self):
\t\tself.customer = _get_or_create_customer()
\t\tself.vehicle = _create_test_vehicle(self.customer)

\tdef tearDown(self):
\t\tfrappe.db.rollback()

\tdef test_create_sales_invoice_blocks_duplicate(self):
\t\tjob_name = _create_repair_job(self.customer, self.vehicle)
\t\tjob = frappe.get_doc(\"Repair Job\", job_name)
\t\t_add_labour_line(job, description=\"Labour X\", rate=100000, qty=1)
\t\tjob.service_lines[0].status = \"Completed\"
\t\tjob.save()
\t\tjob.reload()
\t\tjob.sales_invoice = \"SI-MOCK-001\"
\t\tjob.save()
\t\tjob.reload()
\t\twith self.assertRaises(frappe.ValidationError):
\t\t\tjob.create_sales_invoice()

\tdef test_invoice_only_includes_completed_lines(self):
\t\tjob_name = _create_repair_job(self.customer, self.vehicle)
\t\tjob = frappe.get_doc(\"Repair Job\", job_name)
\t\t_add_labour_line(job, description=\"Completed labour\", rate=100000, qty=1)
\t\tjob.service_lines[0].status = \"Completed\"
\t\t_add_labour_line(job, description=\"Pending labour\", rate=200000, qty=1)
\t\tjob.save()
\t\tjob.reload()
\t\tfrom auto_service_management.auto_service_management.integration.erpnext.adapters import (
\t\t\tcreate_sales_invoice,
\t\t)
\t\twith patch(
\t\t\t\"auto_service_management.auto_service_management.integration.erpnext.adapters.frappe.get_doc\"
\t\t) as mock_get_doc:
\t\t\tmock_si = frappe._dict(name=\"SI-TEST-001\", insert=lambda **kw: None)
\t\t\tmock_get_doc.return_value = mock_si
\t\t\tcaptured_items = []
\t\t\tdef capture_insert(**kw):
\t\t\t\tcaptured_items.extend(kw.get(\"items\", []))
\t\t\tmock_si.insert = capture_insert
\t\t\twith patch(
\t\t\t\t\"auto_service_management.auto_service_management.integration.erpnext.adapters.frappe.db.set_value\"
\t\t\t):
\t\t\t\tcreate_sales_invoice(job)
\t\titem_names = [i.get(\"item_name\") or i.get(\"description\", \"\") for i in captured_items]
\t\tself.assertIn(\"Completed labour\", item_names)
\t\tself.assertNotIn(\"Pending labour\", item_names)

\tdef test_material_request_blocks_duplicate_for_active_line(self):
\t\tjob_name = _create_repair_job(self.customer, self.vehicle)
\t\tjob = frappe.get_doc(\"Repair Job\", job_name)
\t\t_add_parts_line(job, description=\"Brake pads\", qty=2, rate=50000)
\t\tjob.reload()
\t\tline = job.service_lines[0]
\t\tline.stock_request_status = \"Requested\"
\t\tline.requested_qty = 2
\t\tline.material_request = \"MR-MOCK-001\"
\t\tjob.save()
\t\tjob.reload()
\t\twith self.assertRaises(frappe.ValidationError):
\t\t\tjob.create_material_request()


# ---------------------------------------------------------------------------
# Requested/Issued Quantity Tracking Tests
# ---------------------------------------------------------------------------


class TestRequestedIssuedQtyTracking(IntegrationTestCase):
\tdef setUp(self):
\t\tself.customer = _get_or_create_customer()
\t\tself.vehicle = _create_test_vehicle(self.customer)

\tdef tearDown(self):
\t\tfrappe.db.rollback()

\tdef test_requested_qty_set_on_material_request_creation(self):
\t\tjob_name = _create_repair_job(self.customer, self.vehicle)
\t\tjob = frappe.get_doc(\"Repair Job\", job_name)
\t\t_add_parts_line(job, description=\"Air filter\", qty=3, rate=25000)
\t\tjob.reload()
\t\twith patch(
\t\t\t\"auto_service_management.auto_service_management.integration.erpnext.adapters.frappe.get_doc\"
\t\t) as mock_get_doc:
\t\t\tmock_mr = frappe._dict(name=\"MR-TEST-001\", insert=lambda **kw: None)
\t\t\tmock_get_doc.return_value = mock_mr
\t\t\twith patch(
\t\t\t\t\"auto_service_management.auto_service_management.integration.erpnext.adapters.frappe.db.set_value\"
\t\t\t) as mock_set_value:
\t\t\t\tfrom auto_service_management.auto_service_management.integration.erpnext.adapters import (
\t\t\t\t\tcreate_material_request,
\t\t\t\t)
\t\t\t\tcreate_material_request(job)
\t\t\t\tself.assertTrue(mock_set_value.called)
\t\t\t\tcall_args = mock_set_value.call_args
\t\t\t\tself.assertEqual(call_args[0][0], \"Repair Service Line\")
\t\t\t\tself.assertEqual(call_args[0][2][\"requested_qty\"], 3)
\t\t\t\tself.assertEqual(call_args[0][2][\"material_request\"], \"MR-TEST-001\")
\t\t\t\tself.assertEqual(call_args[0][2][\"stock_request_status\"], \"Requested\")

\tdef test_issued_qty_set_on_stock_entry_creation(self):
\t\tjob_name = _create_repair_job(self.customer, self.vehicle)
\t\tjob = frappe.get_doc(\"Repair Job\", job_name)
\t\t_add_parts_line(job, description=\"Spark plugs\", qty=4, rate=15000)
\t\tjob.reload()
\t\tline = job.service_lines[0]
\t\tline.stock_request_status = \"Requested\"
\t\tline.requested_qty = 4
\t\tline.material_request = \"MR-TEST-002\"
\t\tjob.save()
\t\tjob.reload()
\t\twith patch(
\t\t\t\"auto_service_management.auto_service_management.integration.erpnext.adapters.frappe.get_doc\"
\t\t) as mock_get_doc:
\t\t\tmock_se = frappe._dict(name=\"SE-TEST-001\", insert=lambda **kw: None)
\t\t\tmock_get_doc.return_value = mock_se
\t\t\twith patch(
\t\t\t\t\"auto_service_management.auto_service_management.integration.erpnext.adapters.frappe.db.set_value\"
\t\t\t) as mock_set_value:
\t\t\t\tfrom auto_service_management.auto_service_management.integration.erpnext.adapters import (
\t\t\t\t\tcreate_stock_entry_for_material_issue,
\t\t\t\t)
\t\t\t\tcreate_stock_entry_for_material_issue(job)
\t\t\t\tself.assertTrue(mock_set_value.called)
\t\t\t\tcall_args = mock_set_value.call_args
\t\t\t\tself.assertEqual(call_args[0][0], \"Repair Service Line\")
\t\t\t\tself.assertEqual(call_args[0][2][\"issued_qty\"], 4)
\t\t\t\tself.assertEqual(call_args[0][2][\"stock_entry\"], \"SE-TEST-001\")
\t\t\t\tself.assertEqual(call_args[0][2][\"stock_request_status\"], \"Fully Issued\")

\tdef test_material_request_cancelled_allows_re_request(self):
\t\tjob_name = _create_repair_job(self.customer, self.vehicle)
\t\tjob = frappe.get_doc(\"Repair Job\", job_name)
\t\t_add_parts_line(job, description=\"Oil filter\", qty=1, rate=20000)
\t\tjob.reload()
\t\tline = job.service_lines[0]
\t\tline.stock_request_status = \"Cancelled\"
\t\tline.requested_qty = 1
\t\tline.material_request = \"MR-CANCELLED-001\"
\t\tjob.save()
\t\tjob.reload()
\t\twith patch(
\t\t\t\"auto_service_management.auto_service_management.integration.erpnext.adapters.frappe.get_doc\"
\t\t) as mock_get_doc:
\t\t\tmock_mr = frappe._dict(name=\"MR-NEW-001\", insert=lambda **kw: None)
\t\t\tmock_get_doc.return_value = mock_mr
\t\t\twith patch(
\t\t\t\t\"auto_service_management.auto_service_management.integration.erpnext.adapters.frappe.db.set_value\"
\t\t\t):
\t\t\t\tfrom auto_service_management.auto_service_management.integration.erpnext.adapters import (
\t\t\t\t\tcreate_material_request,
\t\t\t\t)
\t\t\t\tmr_name = create_material_request(job)
\t\t\t\tself.assertEqual(mr_name, \"MR-NEW-001\")


# ---------------------------------------------------------------------------
# Shortage / Override Tests
# ---------------------------------------------------------------------------


class TestShortageAndStockGuard(IntegrationTestCase):
\tdef setUp(self):
\t\tself.customer = _get_or_create_customer()
\t\tself.vehicle = _create_test_vehicle(self.customer)

\tdef tearDown(self):
\t\tfrappe.db.rollback()

\tdef test_shortage_detection_when_issued_lt_requested(self):
\t\tjob_name = _create_repair_job(self.customer, self.vehicle)
\t\tjob = frappe.get_doc(\"Repair Job\", job_name)
\t\t_add_parts_line(job, description=\"Brake discs\", qty=4, rate=80000)
\t\tjob.reload()
\t\tline = job.service_lines[0]
\t\tline.stock_request_status = \"Requested\"
\t\tline.requested_qty = 4
\t\tline.issued_qty = 2
\t\tline.material_request = \"MR-PARTIAL-001\"
\t\tjob.save()
\t\tjob.reload()
\t\tshortages = job.get_shortage_report()
\t\tself.assertEqual(len(shortages), 1)
\t\tself.assertEqual(shortages[0][\"shortage_qty\"], 2)
\t\tself.assertEqual(shortages[0][\"needed_qty\"], 4)
\t\tself.assertEqual(shortages[0][\"issued_qty\"], 2)

\tdef test_stock_entry_only_covers_requested_lines(self):
\t\tjob_name = _create_repair_job(self.customer, self.vehicle)
\t\tjob = frappe.get_doc(\"Repair Job\", job_name)
\t\t_add_parts_line(job, description=\"Requested part\", qty=2, rate=50000)
\t\t_add_parts_line(job, description=\"Not requested part\", qty=1, rate=30000)
\t\tjob.reload()
\t\tjob.service_lines[0].stock_request_status = \"Requested\"
\t\tjob.service_lines[0].requested_qty = 2
\t\tjob.service_lines[0].material_request = \"MR-TEST-003\"
\t\tjob.save()
\t\tjob.reload()
\t\twith patch(
\t\t\t\"auto_service_management.auto_service_management.integration.erpnext.adapters.frappe.get_doc\"
\t\t) as mock_get_doc:
\t\t\tmock_se = frappe._dict(name=\"SE-TEST-002\", insert=lambda **kw: None)
\t\t\tmock_get_doc.return_value = mock_se
\t\t\twith patch(
\t\t\t\t\"auto_service_management.auto_service_management.integration.erpnext.adapters.frappe.db.set_value\"
\t\t\t) as mock_set_value:
\t\t\t\tfrom auto_service_management.auto_service_management.integration.erpnext.adapters import (
\t\t\t\t\tcreate_stock_entry_for_material_issue,
\t\t\t\t)
\t\t\t\tcreate_stock_entry_for_material_issue(job)
\t\t\t\tself.assertEqual(mock_set_value.call_count, 1)
\t\t\t\tcall_args = mock_set_value.call_args
\t\t\t\tself.assertEqual(call_args[0][2][\"stock_request_status\"], \"Fully Issued\")
'''

pathlib.Path(r'C:\Users\user\Documents\Coded\DMS\auto_service_management\auto_service_management\auto_service_management\tests\test_phase3b_labour_stock.py').write_text(content, encoding='utf-8')
print('Test file written')
