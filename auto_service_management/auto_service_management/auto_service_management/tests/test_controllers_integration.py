# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

"""Integration tests for Phase 2-5 DocType controllers.

These tests exercise the server-side validation, workflow transitions,
and ERPNext integration adapters with mocked external calls.
"""

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_erpnext_basics():
	"""Create minimal ERPNext setup data if missing."""
	if not frappe.db.exists("Customer Group", "All Customer Groups"):
		frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": "All Customer Groups",
				"is_group": 1,
				"parent_customer_group": "",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Customer Group", {"is_group": 0, "name": "Commercial"}):
		frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": "Commercial",
				"is_group": 0,
				"parent_customer_group": "All Customer Groups",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Territory", "All Territories"):
		frappe.get_doc(
			{
				"doctype": "Territory",
				"territory_name": "All Territories",
				"is_group": 1,
				"parent_territory": "",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Territory", {"is_group": 0, "name": "Uganda"}):
		frappe.get_doc(
			{
				"doctype": "Territory",
				"territory_name": "Uganda",
				"is_group": 0,
				"parent_territory": "All Territories",
			}
		).insert(ignore_permissions=True)


def _get_or_create_customer():
	_ensure_erpnext_basics()
	name = frappe.db.get_value("Customer", {"customer_name": "Test Workshop Customer"}, "name")
	if not name:
		doc = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "Test Workshop Customer",
				"customer_group": "Commercial",
				"territory": "Uganda",
			}
		)
		doc.insert(ignore_permissions=True)
		name = doc.name
	return name


def _create_test_vehicle(customer=None):
	"""Create or reuse a test Customer Vehicle."""
	if not customer:
		customer = _get_or_create_customer()
	existing = frappe.db.get_value("Customer Vehicle", {"vin_chassis_number": "TESTVIN-PH7"}, "name")
	if existing:
		return existing
	doc = frappe.get_doc(
		{
			"doctype": "Customer Vehicle",
			"customer": customer,
			"registration_number": "TEST-PH7-001",
			"vin_chassis_number": "TESTVIN-PH7",
			"engine_number": "ENG-PH7-001",
			"make": "Toyota",
			"model": "Hilux",
			"year_of_manufacture": 2022,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _create_repair_job(customer=None, vehicle=None, fuel_level="1/2"):
	"""Create a Draft Repair Job."""
	if not vehicle:
		if not customer:
			customer = _get_or_create_customer()
		vehicle = _create_test_vehicle(customer)
	if not customer:
		customer = frappe.db.get_value("Customer Vehicle", vehicle, "customer")
	doc = frappe.get_doc(
		{
			"doctype": "Repair Job",
			"customer": customer,
			"customer_vehicle": vehicle,
			"odometer_in": 84521,
			"fuel_level": fuel_level,
			"customer_concern": "Battery warning and brake noise",
			"priority": "Normal",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _append_pending_labour_line(job, description="Workshop labour", rate=120000):
	job.append(
		"service_lines",
		{
			"service_type": "Labour",
			"service_description": description,
			"quantity": 1,
			"rate": rate,
			"status": "Pending Approval",
		},
	)
	job.save()
	job.reload()
	return job.service_lines[-1].name


def _insert_walkaround(job_name, vehicle, fuel_level="1/2"):
	return frappe.get_doc(
		{
			"doctype": "Walkaround Inspection",
			"repair_job": job_name,
			"customer_vehicle": vehicle,
			"inspection_date": frappe.utils.now_datetime(),
			"inspected_by": "Administrator",
			"fuel_level": fuel_level,
		}
	).insert(ignore_permissions=True)


def _insert_diagnosis(job_name, vehicle, complaint="Battery warning and brake noise", road_test_required=0):
	return frappe.get_doc(
		{
			"doctype": "Diagnosis Report",
			"repair_job": job_name,
			"customer_vehicle": vehicle,
			"diagnosis_date": frappe.utils.now_datetime(),
			"diagnosed_by": "Administrator",
			"customer_complaint": complaint,
			"findings": "Electrical fault isolated",
			"recommendations": "Replace faulty component",
			"road_test_required": road_test_required,
			"status": "Submitted",
		}
	).insert(ignore_permissions=True)


def _insert_authorization(job_name, amount=500000):
	return frappe.get_doc(
		{
			"doctype": "Customer Authorization",
			"repair_job": job_name,
			"approved_amount": amount,
			"authorized_by_user": "Administrator",
			"authorization_date": frappe.utils.now_datetime(),
		}
	).insert(ignore_permissions=True)


def _insert_quality_check(job_name, vehicle, status="Passed"):
	return frappe.get_doc(
		{
			"doctype": "Quality Check",
			"repair_job": job_name,
			"customer_vehicle": vehicle,
			"qc_date": frappe.utils.now_datetime(),
			"checked_by": "Administrator",
			"completion_check": 1,
			"fitment_check": 1,
			"fluid_levels_check": 1,
			"warning_lights_clear": 1,
			"cleanliness_check": 1,
			"road_test_check": 1,
			"status": status,
		}
	).insert(ignore_permissions=True)


def _insert_road_test(job_name, vehicle, status="Passed", odometer_start=84521, odometer_end=84531):
	return frappe.get_doc(
		{
			"doctype": "Road Test Report",
			"repair_job": job_name,
			"customer_vehicle": vehicle,
			"test_date": frappe.utils.now_datetime(),
			"tested_by": "Administrator",
			"odometer_start": odometer_start,
			"odometer_end": odometer_end,
			"braking_ok": 1,
			"steering_ok": 1,
			"engine_performance_ok": 1,
			"transmission_ok": 1,
			"no_warning_lights": 1,
			"status": status,
		}
	).insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Repair Job Workflow Integration Tests
# ---------------------------------------------------------------------------


class TestRepairJobWorkflowIntegration(IntegrationTestCase):
	"""Test actual Repair Job document transitions."""

	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def test_check_in_creates_log(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		self.assertEqual(job.job_status, "Checked In")
		logs = frappe.get_all(
			"Repair Job Log",
			filters={"repair_job": job_name, "event_type": "check_in"},
			pluck="name",
		)
		self.assertTrue(logs)

	def test_invalid_transition_blocked(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.job_status = "In Repair"  # Skip intermediate states
		self.assertRaises(frappe.ValidationError, job.save)

	def test_repair_job_requires_odometer_and_reason_for_visit(self):
		doc = frappe.get_doc(
			{
				"doctype": "Repair Job",
				"customer": self.customer,
				"customer_vehicle": self.vehicle,
				"priority": "Normal",
			}
		)

		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_repair_job_persists_fuel_level(self):
		job_name = _create_repair_job(self.customer, self.vehicle, fuel_level="3/4")
		job = frappe.get_doc("Repair Job", job_name)

		self.assertEqual(job.fuel_level, "3/4")

	def test_repair_job_autofills_customer_from_vehicle_selection(self):
		doc = frappe.get_doc(
			{
				"doctype": "Repair Job",
				"customer_vehicle": self.vehicle,
				"odometer_in": 84521,
				"fuel_level": "1/2",
				"customer_concern": "Battery warning and brake noise",
				"priority": "Normal",
			}
		)
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.customer, self.customer)

	def test_parts_line_amount_contributes_to_total(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.append(
			"service_lines",
			{
				"service_type": "Parts",
				"service_description": "Battery replacement",
				"quantity": 2,
				"rate": 150000,
				"status": "Pending Approval",
			},
		)
		job.save()
		job.reload()

		self.assertEqual(job.service_lines[0].amount, 300000)
		self.assertEqual(job.total_amount, 300000)

	def test_full_lifecycle_to_closed(self):
		"""Walk a Repair Job through the entire happy path."""
		job_name = _create_repair_job(self.customer, self.vehicle)

		# Check In
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		self.assertEqual(job.job_status, "Checked In")

		# Walkaround Inspection
		walkaround = _insert_walkaround(job_name, self.vehicle)
		self.assertTrue(walkaround.name)
		job.reload()
		self.assertEqual(job.job_status, "Walkaround Inspection")
		self.assertEqual(job.walkaround_inspection, walkaround.name)

		# Start Diagnosis
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		self.assertEqual(job.job_status, "Diagnosis")
		diagnosis = _insert_diagnosis(job_name, self.vehicle)
		job.reload()
		self.assertEqual(job.diagnosis_report, diagnosis.name)

		_append_pending_labour_line(job, "Approved repair labour")

		# Prepare Estimate -> Waiting for approval
		job = frappe.get_doc("Repair Job", job_name)
		job.request_authorization()
		self.assertEqual(job.job_status, "Waiting for Customer Approval")

		# Authorize
		authorization = _insert_authorization(job_name)
		authorization.approve()
		job.reload()
		self.assertEqual(job.customer_authorization, authorization.name)
		self.assertEqual(job.job_status, "Approved")

		# Start Work
		job = frappe.get_doc("Repair Job", job_name)
		job.start_work()
		self.assertEqual(job.job_status, "In Repair")

		job.complete_service_lines()

		# Quality Check
		job = frappe.get_doc("Repair Job", job_name)
		job.hold_for_qc()
		self.assertEqual(job.job_status, "Quality Check")
		quality_check = _insert_quality_check(job_name, self.vehicle)
		job.reload()
		self.assertEqual(job.quality_check, quality_check.name)
		self.assertFalse(job.road_test_report)

		# Ready for Invoice
		job = frappe.get_doc("Repair Job", job_name)
		job.pass_qc()
		self.assertEqual(job.job_status, "Ready for Invoice")

		# Invoiced
		job = frappe.get_doc("Repair Job", job_name)
		with patch(
			"auto_service_management.auto_service_management.integration.erpnext.adapters.create_sales_invoice",
			return_value="ACC-SINV-TEST-0001",
		):
			job.create_sales_invoice()
		job.reload()
		self.assertEqual(job.job_status, "Invoiced")

		# Gate Pass Issued
		job = frappe.get_doc("Repair Job", job_name)
		frappe.db.set_value(
			"Repair Job",
			job.name,
			{"sales_invoice": "ACC-SINV-TEST-0001"},
			update_modified=False,
		)
		gate_pass = frappe.get_doc(
			{
				"doctype": "Gate Pass",
				"repair_job": job.name,
				"customer_vehicle": self.vehicle,
				"sales_invoice": "ACC-SINV-TEST-0001",
				"recipient_name": "Test Recipient",
				"status": "Pending",
			}
		)
		gate_pass.flags.ignore_links = True
		with patch.object(type(gate_pass), "validate_invoice_submitted"):
			gate_pass.insert(ignore_permissions=True)
		with (
			patch.object(type(gate_pass), "validate_invoice_submitted"),
			patch("frappe.model.document.Document._validate_links", return_value=None),
		):
			gate_pass.issue()
		job = frappe.get_doc("Repair Job", job_name)
		self.assertEqual(job.job_status, "Gate Pass Issued")

		# Close
		frappe.db.set_value("Repair Job", job_name, "sales_invoice", None, update_modified=False)
		job = frappe.get_doc("Repair Job", job_name)
		job.close()

		final = frappe.get_doc("Repair Job", job_name)
		self.assertEqual(final.job_status, "Closed")

	def test_create_sales_invoice_handles_adapter_side_effect_updates(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		_insert_diagnosis(job_name, self.vehicle)
		_append_pending_labour_line(job, "Invoiceable labour")
		job = frappe.get_doc("Repair Job", job_name)
		job.request_authorization()
		_insert_authorization(job_name).approve()
		job = frappe.get_doc("Repair Job", job_name)
		job.start_work()
		job.complete_service_lines()
		job = frappe.get_doc("Repair Job", job_name)
		job.hold_for_qc()
		_insert_quality_check(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.pass_qc()

		def adapter_side_effect(repair_job):
			frappe.db.set_value("Repair Job", repair_job.name, "priority", "High", update_modified=True)
			return "ACC-SINV-RACE-0001"

		job = frappe.get_doc("Repair Job", job_name)
		with patch(
			"auto_service_management.auto_service_management.integration.erpnext.adapters.create_sales_invoice",
			side_effect=adapter_side_effect,
		):
			job.create_sales_invoice()

		job.reload()
		self.assertEqual(job.job_status, "Invoiced")

	def test_pass_qc_requires_passed_road_test_when_diagnosis_marks_it_required(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		_insert_diagnosis(job_name, self.vehicle, road_test_required=1)
		_append_pending_labour_line(job, "Road test labour")
		job = frappe.get_doc("Repair Job", job_name)
		job.request_authorization()
		_insert_authorization(job_name).approve()
		job = frappe.get_doc("Repair Job", job_name)
		job.start_work()
		job.complete_service_lines()
		job.hold_for_qc()
		_insert_quality_check(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)

		with self.assertRaises(frappe.ValidationError):
			job.pass_qc()

		road_test = _insert_road_test(job_name, self.vehicle)
		job.reload()
		self.assertEqual(job.road_test_report, road_test.name)
		job.pass_qc()
		self.assertEqual(job.job_status, "Ready for Invoice")

	def test_cancellation_from_checked_in(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()

		job = frappe.get_doc("Repair Job", job_name)
		job.cancel()

		final = frappe.get_doc("Repair Job", job_name)
		self.assertEqual(final.job_status, "Cancelled")

	def test_diagnosis_only_workflow_can_close_after_gate_pass(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		_insert_diagnosis(job_name, self.vehicle, complaint="Diagnosis only")
		job = frappe.get_doc("Repair Job", job_name)
		job.append(
			"service_lines",
			{
				"service_type": "Labour",
				"service_description": "Diagnosis fee",
				"quantity": 1,
				"rate": 50000,
				"status": "Completed",
			},
		)
		job.save()
		job.mark_ready_for_invoice()

		def invoice_side_effect(repair_job):
			frappe.db.set_value("Repair Job", repair_job.name, {"sales_invoice": "ACC-SINV-DIAG-0001"})
			return "ACC-SINV-DIAG-0001"

		job = frappe.get_doc("Repair Job", job_name)
		with (
			patch(
				"auto_service_management.auto_service_management.integration.erpnext.adapters.create_sales_invoice",
				side_effect=invoice_side_effect,
			),
			patch("frappe.model.document.Document._validate_links", return_value=None),
		):
			job.create_sales_invoice()
		job.reload()
		self.assertEqual(job.job_status, "Invoiced")

		gate_pass = frappe.get_doc(
			{
				"doctype": "Gate Pass",
				"repair_job": job.name,
				"customer_vehicle": self.vehicle,
				"sales_invoice": "ACC-SINV-DIAG-0001",
				"recipient_name": "Diagnosis Only Customer",
				"status": "Pending",
			}
		)
		gate_pass.flags.ignore_links = True
		with patch.object(type(gate_pass), "validate_invoice_submitted"):
			gate_pass.insert(ignore_permissions=True)
		with (
			patch.object(type(gate_pass), "validate_invoice_submitted"),
			patch("frappe.model.document.Document._validate_links", return_value=None),
		):
			gate_pass.issue()

		job.reload()
		with patch("frappe.model.document.Document._validate_links", return_value=None):
			job.close_as_diagnosis_only()
		job.reload()
		self.assertEqual(job.job_status, "Closed - Diagnosis Only")

	def test_partial_line_approval_supports_selective_repair(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		_insert_diagnosis(job_name, self.vehicle)
		for description in ("Replace battery", "Replace brake pads", "Replace shock absorbers", "Engine oil"):
			job.append(
				"service_lines",
				{
					"service_type": "Labour" if description == "Engine oil" else "Parts",
					"service_description": description,
					"quantity": 1,
					"rate": 100000,
					"status": "Pending Approval",
				},
			)
		job.save()
		job.request_authorization()
		job.reload()
		self.assertEqual(job.job_status, "Waiting for Customer Approval")

		battery, brakes, shocks, oil = [line.name for line in job.service_lines]
		job.approve_service_lines([battery, brakes, oil])
		job = frappe.get_doc("Repair Job", job_name)
		job.reject_service_lines([shocks])
		job = frappe.get_doc("Repair Job", job_name)
		status_by_description = {line.service_description: line.status for line in job.service_lines}
		self.assertEqual(status_by_description["Replace battery"], "Approved")
		self.assertEqual(status_by_description["Replace brake pads"], "Approved")
		self.assertEqual(status_by_description["Replace shock absorbers"], "Rejected")
		self.assertEqual(status_by_description["Engine oil"], "Approved")

		_insert_authorization(job_name).approve()
		job.reload()
		self.assertEqual(job.job_status, "Approved")
		job.start_work()
		job.reload()
		self.assertEqual(job.job_status, "In Repair")


# ---------------------------------------------------------------------------
# Fleet Service Campaign Tests
# ---------------------------------------------------------------------------


class TestFleetServiceCampaign(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def test_duplicate_repair_job_blocked(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		campaign = frappe.get_doc(
			{
				"doctype": "Fleet Service Campaign",
				"customer": self.customer,
				"campaign_name": "Test Campaign",
				"fleet_jobs": [
					{"repair_job": job_name},
					{"repair_job": job_name},
				],
			}
		)
		self.assertRaises(frappe.ValidationError, campaign.insert)

	def test_wrong_customer_repair_job_blocked(self):
		other_customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "Other Customer Fleet",
				"customer_group": "Commercial",
				"territory": "Uganda",
			}
		)
		other_customer.insert(ignore_permissions=True)
		other_vehicle = frappe.get_doc(
			{
				"doctype": "Customer Vehicle",
				"customer": other_customer.name,
				"registration_number": "OTHER-REG",
				"vin_chassis_number": "OTHERVIN",
			}
		)
		other_vehicle.insert(ignore_permissions=True)
		other_job = _create_repair_job(other_customer.name, other_vehicle.name)

		campaign = frappe.get_doc(
			{
				"doctype": "Fleet Service Campaign",
				"customer": self.customer,
				"campaign_name": "Mismatch Campaign",
				"fleet_jobs": [{"repair_job": other_job}],
			}
		)
		self.assertRaises(frappe.ValidationError, campaign.insert)


# ---------------------------------------------------------------------------
# Gate Pass Tests
# ---------------------------------------------------------------------------


class TestGatePass(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def test_gate_pass_requires_invoice(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		gp = frappe.get_doc(
			{
				"doctype": "Gate Pass",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"recipient_name": "Test Recipient",
			}
		)
		self.assertRaises(frappe.ValidationError, gp.insert)

	def test_issue_and_use_workflow(self):
		"""Gate Pass issue → use lifecycle."""
		job_name = _create_repair_job(self.customer, self.vehicle)
		frappe.db.set_value(
			"Repair Job",
			job_name,
			{"job_status": "Invoiced", "sales_invoice": "SI-TEST-001"},
			update_modified=False,
		)
		gp = frappe.get_doc(
			{
				"doctype": "Gate Pass",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"sales_invoice": "SI-TEST-001",
				"recipient_name": "Test Recipient",
				"status": "Pending",
			}
		)
		gp.flags.ignore_links = True
		# Mock the invoice validation since we don't have a real invoice
		with patch.object(gp, "validate_invoice_submitted"):
			gp.insert(ignore_permissions=True)

		with (
			patch.object(type(gp), "validate_invoice_submitted"),
			patch("frappe.model.document.Document._validate_links", return_value=None),
		):
			gp.issue()
		self.assertEqual(gp.status, "Issued")
		job = frappe.get_doc("Repair Job", job_name)
		self.assertEqual(job.gate_pass, gp.name)

		with patch.object(type(gp), "validate_invoice_submitted"):
			gp.use_gate_pass()
		self.assertEqual(gp.status, "Used")

	def test_gate_pass_duplicate_for_same_job_is_blocked(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		frappe.db.set_value(
			"Repair Job",
			job_name,
			{"job_status": "Invoiced", "sales_invoice": "SI-TEST-DUP-001"},
			update_modified=False,
		)
		first = frappe.get_doc(
			{
				"doctype": "Gate Pass",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"sales_invoice": "SI-TEST-DUP-001",
				"recipient_name": "First Recipient",
				"status": "Pending",
			}
		)
		first.flags.ignore_links = True
		with patch.object(type(first), "validate_invoice_submitted"):
			first.insert(ignore_permissions=True)

		duplicate = frappe.get_doc(
			{
				"doctype": "Gate Pass",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"sales_invoice": "SI-TEST-DUP-001",
				"recipient_name": "Second Recipient",
				"status": "Pending",
			}
		)
		with patch.object(type(duplicate), "validate_invoice_submitted"):
			self.assertRaises(frappe.ValidationError, duplicate.insert)


# ---------------------------------------------------------------------------
# Quality Check Tests
# ---------------------------------------------------------------------------


class TestQualityCheck(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def test_qc_requires_active_job(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		# Job is in Draft — QC should be blocked
		qc = frappe.get_doc(
			{
				"doctype": "Quality Check",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"qc_date": frappe.utils.now_datetime(),
				"checked_by": "Administrator",
			}
		)
		self.assertRaises(frappe.ValidationError, qc.insert)

	def test_quality_check_links_back_to_job(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		_insert_diagnosis(job_name, self.vehicle)
		_append_pending_labour_line(job, "QC labour")
		job = frappe.get_doc("Repair Job", job_name)
		job.request_authorization()
		_insert_authorization(job_name).approve()
		job = frappe.get_doc("Repair Job", job_name)
		job.start_work()
		job.complete_service_lines()
		job.hold_for_qc()

		qc = _insert_quality_check(job_name, self.vehicle)

		job.reload()
		self.assertEqual(job.quality_check, qc.name)

	def test_quality_check_duplicate_for_same_job_is_blocked(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		_insert_diagnosis(job_name, self.vehicle)
		_append_pending_labour_line(job, "QC labour")
		job = frappe.get_doc("Repair Job", job_name)
		job.request_authorization()
		_insert_authorization(job_name).approve()
		job = frappe.get_doc("Repair Job", job_name)
		job.start_work()
		job.complete_service_lines()
		job.hold_for_qc()
		_insert_quality_check(job_name, self.vehicle)

		duplicate = frappe.get_doc(
			{
				"doctype": "Quality Check",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"qc_date": frappe.utils.now_datetime(),
				"checked_by": "Administrator",
			}
		)
		self.assertRaises(frappe.ValidationError, duplicate.insert)


# ---------------------------------------------------------------------------
# Road Test Report Tests
# ---------------------------------------------------------------------------


class TestRoadTestReport(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def test_road_test_links_back_to_job(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		_insert_diagnosis(job_name, self.vehicle, road_test_required=1)
		_append_pending_labour_line(job, "Road test labour")
		job = frappe.get_doc("Repair Job", job_name)
		job.request_authorization()
		_insert_authorization(job_name).approve()
		job = frappe.get_doc("Repair Job", job_name)
		job.start_work()
		job.complete_service_lines()
		job.hold_for_qc()
		_insert_quality_check(job_name, self.vehicle)

		report = _insert_road_test(job_name, self.vehicle)

		job.reload()
		self.assertEqual(job.road_test_report, report.name)
		self.assertEqual(job.odometer_out, report.odometer_end)

	def test_road_test_duplicate_for_same_job_is_blocked(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		_insert_diagnosis(job_name, self.vehicle, road_test_required=1)
		_append_pending_labour_line(job, "Road test labour")
		job = frappe.get_doc("Repair Job", job_name)
		job.request_authorization()
		_insert_authorization(job_name).approve()
		job = frappe.get_doc("Repair Job", job_name)
		job.start_work()
		job.complete_service_lines()
		job.hold_for_qc()
		_insert_quality_check(job_name, self.vehicle)
		_insert_road_test(job_name, self.vehicle)

		duplicate = frappe.get_doc(
			{
				"doctype": "Road Test Report",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"test_date": frappe.utils.now_datetime(),
				"tested_by": "Administrator",
			}
		)
		self.assertRaises(frappe.ValidationError, duplicate.insert)


# ---------------------------------------------------------------------------
# Walkaround Inspection Tests
# ---------------------------------------------------------------------------


class TestWalkaroundInspection(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def test_walkaround_requires_checked_in_or_diagnosis(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		# Job is in Draft — walkaround should be blocked
		wi = frappe.get_doc(
			{
				"doctype": "Walkaround Inspection",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"inspection_date": frappe.utils.now_datetime(),
				"inspected_by": "Administrator",
			}
		)
		self.assertRaises(frappe.ValidationError, wi.insert)

	def test_walkaround_allowed_after_check_in(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()

		wi = frappe.get_doc(
			{
				"doctype": "Walkaround Inspection",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"inspection_date": frappe.utils.now_datetime(),
				"inspected_by": "Administrator",
			}
		)
		wi.insert(ignore_permissions=True)
		self.assertTrue(wi.name)
		job.reload()
		self.assertEqual(job.job_status, "Walkaround Inspection")
		self.assertEqual(job.walkaround_inspection, wi.name)

	def test_walkaround_duplicate_for_same_job_is_blocked(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)

		duplicate = frappe.get_doc(
			{
				"doctype": "Walkaround Inspection",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"inspection_date": frappe.utils.now_datetime(),
				"inspected_by": "Administrator",
			}
		)
		self.assertRaises(frappe.ValidationError, duplicate.insert)


# ---------------------------------------------------------------------------
# Customer Authorization Tests
# ---------------------------------------------------------------------------


class TestCustomerAuthorization(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def test_authorization_requires_estimate_prepared_state(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		auth = frappe.get_doc(
			{
				"doctype": "Customer Authorization",
				"repair_job": job_name,
				"approved_amount": 500000,
				"authorized_by_user": "Administrator",
				"authorization_date": frappe.utils.now_datetime(),
			}
		)
		self.assertRaises(frappe.ValidationError, auth.insert)

	def test_authorization_approve_updates_job(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		# Walk to Waiting for Customer Approval state
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		_insert_diagnosis(job_name, self.vehicle)
		_append_pending_labour_line(job, "Authorized labour")
		job = frappe.get_doc("Repair Job", job_name)
		job.request_authorization()

		auth = _insert_authorization(job_name)
		auth.approve()

		job = frappe.get_doc("Repair Job", job_name)
		self.assertEqual(job.customer_authorization, auth.name)
		self.assertEqual(job.job_status, "Approved")

	def test_authorization_duplicate_for_same_job_is_blocked(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		_insert_diagnosis(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.request_authorization()
		_insert_authorization(job_name)

		duplicate = frappe.get_doc(
			{
				"doctype": "Customer Authorization",
				"repair_job": job_name,
				"approved_amount": 600000,
				"authorized_by_user": "Administrator",
				"authorization_date": frappe.utils.now_datetime(),
			}
		)
		self.assertRaises(frappe.ValidationError, duplicate.insert)


class TestDiagnosisReport(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def test_diagnosis_links_back_to_job(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()

		report = _insert_diagnosis(job_name, self.vehicle)
		job.reload()
		self.assertEqual(job.diagnosis_report, report.name)

	def test_diagnosis_duplicate_for_same_job_is_blocked(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		_insert_diagnosis(job_name, self.vehicle)

		duplicate = frappe.get_doc(
			{
				"doctype": "Diagnosis Report",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"diagnosis_date": frappe.utils.now_datetime(),
				"diagnosed_by": "Administrator",
			}
		)
		self.assertRaises(frappe.ValidationError, duplicate.insert)


# ---------------------------------------------------------------------------
# Repair Job Override Tests
# ---------------------------------------------------------------------------


class TestRepairJobOverride(IntegrationTestCase):
	def test_approved_override_requires_approver(self):
		override = frappe.get_doc(
			{
				"doctype": "Repair Job Override",
				"override_type": "Credit Release",
				"status": "Approved",
			}
		)
		self.assertRaises(frappe.ValidationError, override.insert)


# ---------------------------------------------------------------------------
# Workshop Bay Tests
# ---------------------------------------------------------------------------


class TestWorkshopBay(IntegrationTestCase):
	def test_bay_maintenance_blocks_when_occupied(self):
		bay = frappe.get_doc(
			{
				"doctype": "Workshop Bay",
				"bay_name": "Test Bay",
				"status": "Available",
			}
		)
		bay.insert(ignore_permissions=True)
		# Mock occupied_count to return > 0
		with patch.object(type(bay), "occupied_count", return_value=2):
			bay.status = "Under Maintenance"
			self.assertRaises(frappe.ValidationError, bay.save)


# ---------------------------------------------------------------------------
# ERPNext Adapter Tests (mocked)
# ---------------------------------------------------------------------------


class TestERPNextAdapters(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def test_get_item_price_returns_zero_for_missing(self):
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			get_item_price,
		)

		with patch(
			"auto_service_management.auto_service_management.integration.erpnext.adapters.frappe"
		) as mock_frappe:
			mock_frappe.get_single.return_value = MagicMock(
				selling_price_list="Standard Selling", price_list="Standard Selling"
			)
			mock_frappe.get_all.return_value = []
			price = get_item_price("NONEXISTENT-ITEM")
			self.assertEqual(price, 0)

	def test_create_quotation_rejects_empty_lines(self):
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_quotation,
		)

		job = frappe.get_doc("Repair Job", _create_repair_job(self.customer, self.vehicle))
		job.service_lines = []
		with self.assertRaises(frappe.ValidationError):
			create_quotation(job)

	def test_create_material_request_rejects_no_parts(self):
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_material_request,
		)

		job = frappe.get_doc("Repair Job", _create_repair_job(self.customer, self.vehicle))
		# No Parts lines
		job.service_lines = []
		with self.assertRaises(frappe.ValidationError):
			create_material_request(job)


class TestPhase7HardeningIntegration(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def _build_renderable_job_bundle(self):
		job = frappe.get_doc("Repair Job", _create_repair_job(self.customer, self.vehicle))

		with patch.object(type(job), "_ensure_project"):
			job.check_in()

		walkaround = _insert_walkaround(job.name, self.vehicle)

		job.reload()
		job.start_diagnosis()
		job.reload()
		_insert_diagnosis(job.name, self.vehicle)
		_append_pending_labour_line(job, "Renderable labour")
		job.request_authorization()

		authorization = _insert_authorization(job.name, amount=250000)
		authorization.approve()

		job.reload()
		job.start_work()
		job.reload()
		job.hold_for_qc()
		job.reload()
		quality_check = _insert_quality_check(job.name, self.vehicle)
		job.reload()
		job.pass_qc()
		frappe.db.set_value(
			"Repair Job",
			job.name,
			{"sales_invoice": "SI-PH7-PRINT-001", "job_status": "Invoiced"},
			update_modified=False,
		)
		job.reload()

		gate_pass = frappe.get_doc(
			{
				"doctype": "Gate Pass",
				"repair_job": job.name,
				"customer_vehicle": self.vehicle,
				"sales_invoice": "SI-PH7-PRINT-001",
				"recipient_name": "Print Test Recipient",
				"status": "Pending",
			}
		)
		gate_pass.flags.ignore_links = True
		with patch.object(type(gate_pass), "validate_invoice_submitted"):
			gate_pass.insert(ignore_permissions=True)

		return job.name, walkaround.name, authorization.name, quality_check.name, gate_pass.name

	def _render_pdf(self, doctype, name, print_format_name):
		from frappe.utils.pdf import get_pdf
		from frappe.www.printview import get_rendered_template

		doc = frappe.get_doc(doctype, name)
		print_format = frappe.get_doc("Print Format", print_format_name)
		frappe.flags.ignore_print_permissions = True
		try:
			html = get_rendered_template(doc, print_format=print_format, meta=frappe.get_meta(doctype))
			pdf = get_pdf(
				html, options={"load-error-handling": "ignore", "load-media-error-handling": "ignore"}
			)
		finally:
			frappe.flags.ignore_print_permissions = False
		self.assertTrue(pdf.startswith(b"%PDF"))
		return pdf

	def test_all_phase6_print_formats_render_to_pdf(self):
		job_name, walkaround_name, authorization_name, _quality_check_name, gate_pass_name = (
			self._build_renderable_job_bundle()
		)
		documents = [
			("Repair Job", job_name, "Job Card"),
			("Walkaround Inspection", walkaround_name, "Walkaround Inspection"),
			("Customer Authorization", authorization_name, "Customer Authorization"),
			("Repair Job", job_name, "Estimate Summary"),
			("Gate Pass", gate_pass_name, "Gate Pass"),
			("Repair Job", job_name, "Repair Summary"),
		]

		for doctype, name, print_format_name in documents:
			with self.subTest(print_format=print_format_name):
				pdf = self._render_pdf(doctype, name, print_format_name)
				self.assertGreater(len(pdf), 100)

	def test_workflow_actions_require_write_permission(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)

		with patch.object(type(job), "check_permission", side_effect=frappe.PermissionError):
			with self.assertRaises(frappe.PermissionError):
				job.check_in()

	def test_gate_pass_issue_requires_write_permission(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		gate_pass = frappe.get_doc(
			{
				"doctype": "Gate Pass",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"sales_invoice": "SI-PERM-001",
				"recipient_name": "Restricted User",
				"status": "Pending",
			}
		)
		gate_pass.flags.ignore_links = True
		with patch.object(type(gate_pass), "validate_invoice_submitted"):
			gate_pass.insert(ignore_permissions=True)

		with patch.object(type(gate_pass), "check_permission", side_effect=frappe.PermissionError):
			with self.assertRaises(frappe.PermissionError):
				gate_pass.issue()

	def test_customer_authorization_approve_requires_write_permission(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job.name, self.vehicle)
		job.reload()
		job.start_diagnosis()
		job.reload()
		_insert_diagnosis(job.name, self.vehicle)
		_append_pending_labour_line(job, "Authorization labour")
		job.request_authorization()

		authorization = _insert_authorization(job.name)

		with patch.object(type(authorization), "check_permission", side_effect=frappe.PermissionError):
			with self.assertRaises(frappe.PermissionError):
				authorization.approve()

	def test_desktop_icon_exists_and_is_visible(self):
		"""App-type Desktop Icon for Auto Service Management must exist and not be hidden."""
		icon = frappe.db.get_value(
			"Desktop Icon",
			{"icon_type": "App", "app": "auto_service_management"},
			["name", "hidden", "link_type", "link_to", "standard"],
			as_dict=True,
		)
		self.assertTrue(icon, "Desktop Icon record must exist for auto_service_management")
		self.assertEqual(icon.name, "Auto Service Management")
		self.assertFalse(icon.hidden, "Desktop Icon must not be hidden")
		self.assertEqual(icon.link_type, "Workspace Sidebar")
		self.assertEqual(icon.link_to, "Workshop Management")
		self.assertTrue(icon.standard, "Desktop Icon must be standard")

	def test_desktop_icon_permission_check(self):
		"""ensure_permission must deny Guest and allow authenticated users."""
		from auto_service_management.auto_service_management.desktop import ensure_permission

		original_user = frappe.session.user
		try:
			frappe.session.user = "Guest"
			self.assertFalse(ensure_permission())
			frappe.session.user = "Administrator"
			self.assertTrue(ensure_permission())
		finally:
			frappe.session.user = original_user

	def test_workspace_sidebar_is_grouped_for_auto_service_management(self):
		from auto_service_management.auto_service_management.desktop import setup_desktop

		if frappe.db.exists("Workspace Sidebar", "Workshop Management"):
			frappe.delete_doc("Workspace Sidebar", "Workshop Management", ignore_permissions=True)

		setup_desktop()

		sidebar = frappe.get_doc("Workspace Sidebar", "Workshop Management")
		self.assertGreater(len(sidebar.items), 6)

		home_item = sidebar.items[0]
		self.assertEqual(home_item.label, "Home")
		self.assertEqual(home_item.type, "Link")
		self.assertEqual(home_item.link_type, "Workspace")
		self.assertEqual(home_item.link_to, "Workshop Management")

		section_labels = [item.label for item in sidebar.items if item.type == "Section Break"]
		self.assertEqual(
			section_labels,
			[
				"Intake & Setup",
				"Workshop Execution",
				"QC, Release & History",
				"Fleet & Exceptions",
				"Reports",
			],
		)

		link_labels = {item.label for item in sidebar.items if item.type == "Link"}
		self.assertIn("Customer Vehicle", link_labels)
		self.assertIn("Repair Job", link_labels)
		self.assertIn("Gate Pass", link_labels)
		self.assertIn("Jobs by Status", link_labels)
