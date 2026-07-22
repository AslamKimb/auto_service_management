from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
import unittest

from auto_service_management.patches.phase17_pre_model_sync_safety import (
	_collect_release_a_safety_issues,
	_patch_log_issue,
)


class _FakeFrappe:
	def __init__(self, *, jobs=None, road_tests=None):
		self.db = SimpleNamespace(table_exists=lambda doctype: True, exists=lambda doctype, name: True)
		self.jobs = list(jobs or [])
		self.road_tests = list(road_tests or [])

	def get_all(self, doctype, **kwargs):
		if doctype == "Repair Job":
			return list(self.jobs)
		if doctype == "Repair Job Service":
			if not self.jobs:
				return []
			return [
				SimpleNamespace(
					name="SVC-1",
					repair_job=self.jobs[0],
					repair_service_template="RST-1",
				)
			]
		if doctype == "Road Test Report":
			return list(self.road_tests)
		return []

	def get_doc(self, doctype, name):
		return SimpleNamespace(name=name, total_amount=100, payment_total=50, payment_status="Unpaid")


class TestPhase40PreModelSyncSafety(unittest.TestCase):
	def test_patch_log_issue_detects_missing_release_a_entry(self):
		with patch(
			"auto_service_management.patches.phase17_pre_model_sync_safety.Path.read_text",
			return_value="[pre_model_sync]\n",
		):
			issue = _patch_log_issue()

		self.assertIsNotNone(issue)
		self.assertEqual(issue["check"], "patch_log")

	def test_collect_release_a_safety_issues_reports_legacy_data(self):
		fake_frappe = _FakeFrappe(jobs=["RJ-1"], road_tests=["RT-1"])

		with (
			patch("auto_service_management.patches.phase17_pre_model_sync_safety.frappe", fake_frappe),
			patch(
				"auto_service_management.patches.phase17_pre_model_sync_safety.Path.read_text",
				return_value="[pre_model_sync]\nauto_service_management.patches.phase11_materialize_template_services\n",
			),
			patch(
				"auto_service_management.patches.phase17_pre_model_sync_safety.build_repair_job_service_workshop_bay_rows",
				return_value=([], [{"repair_job": "RJ-1", "repair_job_service": "SVC-1", "reason": "Repair Job has no enabled Workshop Bay"}]),
			),
			patch(
				"auto_service_management.patches.phase17_pre_model_sync_safety._active_service_total",
				return_value=80,
			),
			patch(
				"auto_service_management.patches.phase17_pre_model_sync_safety.build_repair_job_invoice_rows",
				return_value=[{"grand_total": 100}],
			),
			patch(
				"auto_service_management.patches.phase17_pre_model_sync_safety.build_repair_job_payment_rows",
				return_value=[{"allocated_amount": 40}],
			),
		):
			issues = _collect_release_a_safety_issues()

		self.assertTrue(any(issue["check"] == "road_test_reports" for issue in issues))
		self.assertTrue(any(issue["check"] == "template_references" for issue in issues))
		self.assertTrue(any(issue.get("check") == "service_totals" for issue in issues))
		self.assertTrue(any(issue.get("check") == "payment_totals" for issue in issues))
		self.assertTrue(any(issue.get("check") == "payment_status" for issue in issues))

	def test_collect_release_a_safety_issues_is_empty_when_reconciled(self):
		fake_frappe = _FakeFrappe()

		with (
			patch("auto_service_management.patches.phase17_pre_model_sync_safety.frappe", fake_frappe),
			patch(
				"auto_service_management.patches.phase17_pre_model_sync_safety.Path.read_text",
				return_value="[pre_model_sync]\nauto_service_management.patches.phase11_materialize_template_services\n",
			),
			patch(
				"auto_service_management.patches.phase17_pre_model_sync_safety.build_repair_job_service_workshop_bay_rows",
				return_value=([], []),
			),
			patch(
				"auto_service_management.patches.phase17_pre_model_sync_safety._active_service_total",
				return_value=100,
			),
			patch(
				"auto_service_management.patches.phase17_pre_model_sync_safety.build_repair_job_invoice_rows",
				return_value=[{"grand_total": 100}],
			),
			patch(
				"auto_service_management.patches.phase17_pre_model_sync_safety.build_repair_job_payment_rows",
				return_value=[{"allocated_amount": 50}],
			),
		):
			issues = _collect_release_a_safety_issues()

		self.assertEqual([], issues)
