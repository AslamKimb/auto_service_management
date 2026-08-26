from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import frappe

from auto_service_management.auto_service_management.integration import customer_lpo_workflow


def _lpo(row_count: int):
	return frappe._dict(
		name="LPO-LARGE",
		vehicle_rows=[
			frappe._dict(
				idx=index,
				customer_vehicle=f"CV-{index}",
				repair_job=None,
			)
			for index in range(1, row_count + 1)
		],
	)


class TestPhase33FleetAsync(unittest.TestCase):
	def test_status_endpoint_is_typed_and_get_only(self):
		from inspect import signature

		self.assertEqual(
			frappe.allowed_http_methods_for_whitelisted_func[customer_lpo_workflow.get_fleet_creation_status],
			["GET"],
		)
		self.assertTrue(
			all(
				parameter.annotation is not parameter.empty
				for parameter in signature(
					customer_lpo_workflow.get_fleet_creation_status
				).parameters.values()
			)
		)

	def test_threshold_preserves_synchronous_path(self):
		lpo = _lpo(customer_lpo_workflow.FLEET_SYNC_MAX_VEHICLES)
		expected = {"lpo": lpo.name, "repair_jobs": []}
		with (
			patch.object(customer_lpo_workflow, "_get_lpo", return_value=lpo),
			patch.object(customer_lpo_workflow, "_require_submitted"),
			patch.object(
				customer_lpo_workflow, "_create_campaign_and_repair_jobs_sync", return_value=expected
			) as sync,
			patch.object(customer_lpo_workflow, "_enqueue_fleet_creation") as enqueue,
		):
			result = customer_lpo_workflow.create_campaign_and_repair_jobs(lpo.name)

		self.assertEqual(result, expected)
		sync.assert_called_once_with(lpo, rows=lpo.vehicle_rows)
		enqueue.assert_not_called()

	def test_large_fleet_returns_deterministic_queued_job(self):
		count = customer_lpo_workflow.FLEET_SYNC_MAX_VEHICLES + 1
		lpo = _lpo(count)
		expected = {"lpo": lpo.name, "job_id": "fleet-campaign:LPO-LARGE", "status": "Queued"}
		with (
			patch.object(customer_lpo_workflow, "_get_lpo", return_value=lpo),
			patch.object(customer_lpo_workflow, "_require_submitted"),
			patch.object(customer_lpo_workflow, "_enqueue_fleet_creation", return_value=expected) as enqueue,
			patch.object(customer_lpo_workflow, "_create_campaign_and_repair_jobs_sync") as sync,
		):
			result = customer_lpo_workflow.create_campaign_and_repair_jobs(lpo.name)

		self.assertEqual(result, expected)
		enqueue.assert_called_once_with(lpo.name, count)
		sync.assert_not_called()

	def test_enqueue_uses_deduplicated_long_job_and_stable_id(self):
		job = MagicMock(id="ignored-rq-id")
		with (
			patch.object(customer_lpo_workflow.frappe, "enqueue", return_value=job) as enqueue,
			patch.object(customer_lpo_workflow, "_set_fleet_progress") as progress,
		):
			result = customer_lpo_workflow._enqueue_fleet_creation("LPO-1", 21)

		self.assertEqual(result, {"lpo": "LPO-1", "job_id": "fleet-campaign:LPO-1", "status": "Queued"})
		kwargs = enqueue.call_args.kwargs
		self.assertEqual(kwargs["queue"], "long")
		self.assertEqual(kwargs["job_id"], "fleet-campaign:LPO-1")
		self.assertTrue(kwargs["deduplicate"])
		self.assertFalse(kwargs["enqueue_after_commit"])
		progress.assert_called_once_with("fleet-campaign:LPO-1", status="queued", completed=0, total=21)

	def test_worker_marks_progress_and_status_is_permission_scoped(self):
		lpo = _lpo(21)
		result = {"lpo": lpo.name, "fleet_service_campaign": "FSC-1", "repair_jobs": []}
		progress_calls = []
		with (
			patch.object(customer_lpo_workflow, "_get_lpo", return_value=lpo),
			patch.object(
				customer_lpo_workflow, "_create_campaign_and_repair_jobs_sync", return_value=result
			) as sync,
			patch.object(
				customer_lpo_workflow,
				"_set_fleet_progress",
				side_effect=lambda *args, **kwargs: progress_calls.append((args, kwargs)),
			),
		):
			self.assertEqual(customer_lpo_workflow.run_fleet_creation_job(lpo.name), result)

		sync.assert_called_once()
		self.assertEqual(progress_calls[0][1], {"status": "running", "completed": 0, "total": 21})
		self.assertEqual(progress_calls[-1][1], {"status": "completed", "completed": 21, "total": 21})

	def test_status_rejects_a_job_id_for_another_lpo(self):
		lpo = _lpo(21)
		with (
			patch.object(customer_lpo_workflow, "_get_lpo", return_value=lpo),
			self.assertRaisesRegex(frappe.ValidationError, "does not belong"),
		):
			customer_lpo_workflow.get_fleet_creation_status(lpo.name, "fleet-campaign:OTHER")


if __name__ == "__main__":
	unittest.main()
