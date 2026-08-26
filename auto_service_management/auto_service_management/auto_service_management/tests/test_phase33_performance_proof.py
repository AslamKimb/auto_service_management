from __future__ import annotations

import inspect
from dataclasses import dataclass
from time import perf_counter
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.integration import customer_lpo_workflow


@dataclass(frozen=True)
class Phase33PerformanceDataset:
	jobs: list
	services: list
	components: list


def seed_phase33_performance_dataset(job_count: int = 100) -> Phase33PerformanceDataset:
	"""Seed deterministic in-memory rows at the Phase 33 acceptance scale."""
	jobs = [
		frappe._dict(
			name=f"PERF-RJ-{index:03d}",
			job_status="In Repair",
			total_amount=100,
			customer_vehicle=f"PERF-VEH-{index:03d}",
		)
		for index in range(1, job_count + 1)
	]
	services = [
		frappe._dict(
			name=f"PERF-SVC-{index:03d}",
			repair_job=jobs[(index - 1) // 2].name,
		)
		for index in range(1, job_count * 2 + 1)
	]
	components = [
		frappe._dict(
			name=f"PERF-COMP-{index:04d}",
			repair_job_service=services[(index - 1) // 5].name,
			component_type="Part",
		)
		for index in range(1, job_count * 10 + 1)
	]
	return Phase33PerformanceDataset(jobs, services, components)


def _seed_lpo(dataset: Phase33PerformanceDataset) -> frappe._dict:
	return frappe._dict(
		name="PERF-LPO-100",
		status="Active",
		docstatus=1,
		ceiling_basis="Tax Inclusive",
		authorized_amount=100000,
		vehicle_rows=[
			frappe._dict(
				name=f"PERF-ROW-{index:03d}",
				registration_number=f"PERF{index:03d}",
				customer_vehicle=job.customer_vehicle,
				repair_job=job.name,
				status="Job Created",
			)
			for index, job in enumerate(dataset.jobs, start=1)
		],
	)


def _summary_with_seed(dataset: Phase33PerformanceDataset):
	"""Run the summary against seeded rows while counting storage calls."""
	invoices = [frappe._dict(name=f"PERF-SINV-{i:03d}", docstatus=1, grand_total=100) for i in range(1, 101)]
	orders = [frappe._dict(name=f"PERF-SO-{i:03d}", docstatus=1, grand_total=100) for i in range(1, 101)]
	rows_by_doctype = {
		"Repair Job": dataset.jobs,
		"Sales Invoice": invoices,
		"Sales Order": orders,
	}

	def get_list(doctype, **kwargs):
		page_size = kwargs.get("limit_page_length", kwargs.get("limit", 500))
		offset = kwargs.get("limit_start", 0)
		return rows_by_doctype[doctype][offset : offset + page_size]

	def exists(doctype, name=None):
		return doctype == "DocType" and name in {"Sales Invoice", "Sales Order"}

	with (
		patch.object(customer_lpo_workflow, "_get_lpo", return_value=_seed_lpo(dataset)),
		patch.object(customer_lpo_workflow.frappe, "has_permission", return_value=True),
		patch.object(customer_lpo_workflow.frappe.db, "exists", side_effect=exists),
		patch.object(customer_lpo_workflow.frappe, "get_list", side_effect=get_list) as get_list_mock,
	):
		started = perf_counter()
		result = customer_lpo_workflow.get_lpo_summary("PERF-LPO-100")
		elapsed = perf_counter() - started
	return result, get_list_mock, elapsed


class TestPhase33PerformanceProof(UnitTestCase):
	def test_seeded_acceptance_scale_has_required_shape(self):
		dataset = seed_phase33_performance_dataset()
		self.assertEqual(len(dataset.jobs), 100)
		self.assertEqual(len(dataset.services), 200)
		self.assertEqual(len(dataset.components), 1000)
		self.assertEqual(len({row.repair_job for row in dataset.services}), 100)

	def test_summary_query_count_is_constant_at_acceptance_scale(self):
		small_result, small_calls, small_elapsed = _summary_with_seed(seed_phase33_performance_dataset(1))
		large_result, large_calls, large_elapsed = _summary_with_seed(seed_phase33_performance_dataset())

		self.assertEqual(len(small_result["vehicles"]), 1)
		self.assertEqual(len(large_result["vehicles"]), 100)
		self.assertEqual(small_calls.call_count, 3)
		self.assertEqual(large_calls.call_count, 3)
		self.assertGreaterEqual(small_elapsed, 0)
		self.assertGreaterEqual(large_elapsed, 0)
		for call in large_calls.call_args_list:
			self.assertGreater(call.kwargs["limit_page_length"], 0)
			if call.args[0] in {"Sales Invoice", "Sales Order"}:
				self.assertIn("limit_start", call.kwargs)

	def test_lpo_workflow_has_no_unbounded_list_reads(self):
		source = inspect.getsource(customer_lpo_workflow)
		self.assertNotIn("limit_page_length=0", source)
		self.assertNotIn('"limit_page_length": 0', source)


if __name__ == "__main__":
	import unittest

	unittest.main()
