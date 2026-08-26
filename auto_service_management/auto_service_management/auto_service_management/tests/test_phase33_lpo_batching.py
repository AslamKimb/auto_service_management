from unittest.mock import Mock, patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.integration import customer_lpo_workflow


class TestPhase33LPOBatching(UnitTestCase):
	def test_lpo_summary_batches_permission_scoped_job_lookup(self):
		lpo = frappe._dict(
			name="LPO-1",
			status="Submitted",
			docstatus=1,
			ceiling_basis="Tax Inclusive",
			authorized_amount=1000,
			vehicle_rows=[
				frappe._dict(
					name="ROW-1",
					registration_number="UBA482M",
					customer_vehicle="VEH-1",
					repair_job="JOB-1",
					status="Job Created",
				),
				frappe._dict(
					name="ROW-2",
					registration_number="UBA483M",
					customer_vehicle="VEH-2",
					repair_job="JOB-2",
					status="Job Created",
				),
			],
		)
		jobs = [
			frappe._dict(name="JOB-1", job_status="Closed", total_amount=100, customer_vehicle="VEH-1"),
			frappe._dict(name="JOB-2", job_status="In Repair", total_amount=200, customer_vehicle="VEH-2"),
		]

		def get_list(doctype, *args, **kwargs):
			return jobs if doctype == "Repair Job" else []

		with (
			patch.object(customer_lpo_workflow, "_get_lpo", return_value=lpo),
			patch.object(customer_lpo_workflow.frappe, "has_permission", return_value=True) as has_permission,
			patch.object(customer_lpo_workflow.frappe.db, "exists", return_value=False),
			patch.object(customer_lpo_workflow.frappe, "get_list", side_effect=get_list) as get_list_mock,
		):
			result = customer_lpo_workflow.get_lpo_summary("LPO-1")

		repair_job_calls = [call for call in get_list_mock.call_args_list if call.args[0] == "Repair Job"]
		self.assertEqual(len(repair_job_calls), 1)
		self.assertEqual(repair_job_calls[0].kwargs["filters"], {"name": ["in", ["JOB-1", "JOB-2"]]})
		self.assertEqual(repair_job_calls[0].kwargs["limit_page_length"], 2)
		has_permission.assert_any_call("Repair Job", "read", throw=False)
		self.assertEqual(result["vehicles"][0]["repair_job"]["job_status"], "Closed")
		self.assertEqual(result["vehicles"][1]["repair_job"]["job_status"], "In Repair")

	def test_close_lpo_batches_job_status_reads_and_requires_read_permission(self):
		lpo = frappe._dict(
			name="LPO-1",
			docstatus=1,
			vehicle_rows=[
				frappe._dict(registration_number="UBA482M", repair_job="JOB-1"),
				frappe._dict(registration_number="UBA483M", repair_job="JOB-2"),
			],
			save=Mock(),
		)

		with (
			patch.object(customer_lpo_workflow, "_get_lpo", return_value=lpo),
			patch.object(customer_lpo_workflow, "_require_submitted"),
			patch.object(customer_lpo_workflow.frappe, "has_permission", return_value=True) as has_permission,
			patch.object(
				customer_lpo_workflow.frappe,
				"get_list",
				return_value=[
					frappe._dict(name="JOB-1", job_status="Closed"),
					frappe._dict(name="JOB-2", job_status="Cancelled"),
				],
			) as get_list_mock,
			patch.object(customer_lpo_workflow.frappe.db, "get_value") as get_value,
		):
			result = customer_lpo_workflow.close_lpo("LPO-1")

		self.assertEqual(result, "LPO-1")
		self.assertEqual(len(get_list_mock.call_args_list), 1)
		self.assertEqual(get_list_mock.call_args.kwargs["filters"], {"name": ["in", ["JOB-1", "JOB-2"]]})
		has_permission.assert_called_once_with("Repair Job", "read", throw=True)
		get_value.assert_not_called()
		self.assertEqual(lpo.status, "Completed")
		lpo.save.assert_called_once_with()
