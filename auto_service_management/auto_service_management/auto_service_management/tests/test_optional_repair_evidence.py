# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from auto_service_management.auto_service_management.tests.test_controllers_integration import (
	_create_job_service,
	_create_repair_job,
	_create_test_vehicle,
	_get_or_create_customer,
)

OPTIONAL_STATUSES = (
	"Draft",
	"Assessment",
	"Awaiting Approval",
	"In Repair",
	"Quality Check",
	"Billing",
	"Ready for Release",
	"Closed",
	"Cancelled",
)


class TestOptionalRepairEvidence(IntegrationTestCase):
	"""Optional evidence remains link-valid across the complete job lifecycle."""

	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def _job_at(self, status):
		job_name = _create_repair_job(self.customer, self.vehicle)
		frappe.db.set_value("Repair Job", job_name, "job_status", status, update_modified=False)
		return job_name

	def _evidence(self, doctype, job_name):
		common = {"repair_job": job_name}
		if doctype == "Walkaround Inspection":
			common.update(
				{
					"customer_vehicle": self.vehicle,
					"inspection_date": frappe.utils.now_datetime(),
					"inspected_by": "Administrator",
				}
			)
		elif doctype == "Diagnosis Report":
			common.update(
				{
					"customer_vehicle": self.vehicle,
					"diagnosis_date": frappe.utils.now_datetime(),
					"diagnosed_by": "Administrator",
				}
			)
		elif doctype == "Customer Authorization":
			common.update(
				{
					"customer": self.customer,
					"authorization_date": frappe.utils.now_datetime(),
					"authorized_by_user": "Administrator",
					"approved_amount": 500000,
				}
			)
		elif doctype == "Quality Check":
			common.update(
				{
					"customer_vehicle": self.vehicle,
					"qc_date": frappe.utils.now_datetime(),
					"checked_by": "Administrator",
				}
			)
		return frappe.get_doc({"doctype": doctype, **common})

	def test_all_optional_evidence_types_can_be_created_at_every_status(self):
		for doctype in (
			"Walkaround Inspection",
			"Diagnosis Report",
			"Customer Authorization",
			"Quality Check",
		):
			for status in OPTIONAL_STATUSES:
				with self.subTest(doctype=doctype, status=status):
					job_name = self._job_at(status)
					doc = self._evidence(doctype, job_name)
					doc.insert(ignore_permissions=True)
					observed_status = frappe.db.get_value("Repair Job", job_name, "job_status")
					if doctype == "Walkaround Inspection" and status == "Draft":
						self.assertEqual("Assessment", observed_status)
					else:
						self.assertEqual(status, observed_status)

	def test_repair_can_reach_billing_without_optional_evidence(self):
		job = frappe.get_doc("Repair Job", _create_repair_job(self.customer, self.vehicle))
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_create_job_service(job, "Optional evidence is not a gate")
		job.reload()
		job.complete_diagnosis()
		self.assertEqual("Awaiting Approval", job.reload().job_status)
		job.start_work()
		job.mark_ready_for_invoice()
		self.assertEqual("Billing", job.reload().job_status)

	def test_failed_qc_requires_explicit_return_to_repair_and_never_auto_regresses(self):
		job = frappe.get_doc("Repair Job", self._job_at("Quality Check"))
		job.return_to_repair()
		self.assertEqual("In Repair", job.reload().job_status)
