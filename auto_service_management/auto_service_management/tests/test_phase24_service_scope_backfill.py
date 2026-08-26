from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from auto_service_management.patches.phase15_backfill_service_scope_revisions import (
	_backfill_service_scope_revisions,
)


class FakeDB:
	def __init__(self, existing_jobs=None, existing_auths=None):
		self.existing_jobs = set(existing_jobs or [])
		self.existing_auths = set(existing_auths or [])
		self.set_values = []

	def table_exists(self, doctype):
		return True

	def exists(self, doctype, name):
		if doctype == "Repair Job":
			return name in self.existing_jobs
		if doctype == "Customer Authorization":
			return name in self.existing_auths
		return False

	def set_value(self, doctype, name, values, update_modified=False):
		self.set_values.append((doctype, name, values, update_modified))


class FakeLogger:
	def __init__(self):
		self.messages = []

	def warning(self, message, payload):
		self.messages.append((message, payload))


class FakeFrappe:
	def __init__(self, jobs, authorizations, existing_jobs=None, existing_auths=None):
		self.jobs = jobs
		self.authorizations = authorizations
		self.db = FakeDB(existing_jobs=existing_jobs, existing_auths=existing_auths)
		self.logger_obj = FakeLogger()

	def get_all(self, doctype, **kwargs):
		if doctype == "Repair Job":
			if kwargs.get("pluck") == "name":
				return list(self.jobs)
			return [SimpleNamespace(name=name) for name in self.jobs]
		if doctype == "Customer Authorization":
			filters = kwargs.get("filters") or {}
			if filters.get("status") == "Approved":
				return list(self.authorizations)
		return []

	def logger(self, name):
		return self.logger_obj


class TestPhase24ServiceScopeBackfill(unittest.TestCase):
	def test_backfill_updates_job_and_authorization_scope_snapshots(self):
		fake_frappe = FakeFrappe(
			jobs=["RJ-1", "RJ-2"],
			authorizations=[
				SimpleNamespace(
					name="AUTH-1",
					repair_job="RJ-1",
					scope_revision=0,
					scope_total_amount=0,
					approved_amount=100,
					status="Approved",
				)
			],
			existing_jobs={"RJ-1", "RJ-2"},
			existing_auths={"AUTH-1"},
		)

		services = {
			"RJ-1": [
				SimpleNamespace(status="Approved", total_amount=100),
				SimpleNamespace(status="Rejected", total_amount=75),
			],
			"RJ-2": [
				SimpleNamespace(status="Approved", total_amount=250),
			],
		}

		with (
			patch(
				"auto_service_management.patches.phase15_backfill_service_scope_revisions.frappe",
				fake_frappe,
			),
			patch(
				"auto_service_management.patches.phase15_backfill_service_scope_revisions.get_repair_job_services",
				side_effect=lambda repair_job_name: services[repair_job_name],
			),
		):
			_backfill_service_scope_revisions()

		self.assertIn(
			("Repair Job", "RJ-1", {"scope_revision": 1, "total_amount": 100.0}, False),
			fake_frappe.db.set_values,
		)
		self.assertIn(
			("Repair Job", "RJ-2", {"scope_revision": 1, "total_amount": 250.0}, False),
			fake_frappe.db.set_values,
		)
		self.assertIn(
			("Customer Authorization", "AUTH-1", {"scope_revision": 1, "scope_total_amount": 100.0}, False),
			fake_frappe.db.set_values,
		)
		self.assertTrue(fake_frappe.logger_obj.messages)
		self.assertIn("stale and has been refreshed", fake_frappe.logger_obj.messages[0][1])

	def test_backfill_reports_missing_and_orphaned_approvals(self):
		fake_frappe = FakeFrappe(
			jobs=["RJ-1"],
			authorizations=[
				SimpleNamespace(
					name="AUTH-ORPHAN",
					repair_job="MISSING",
					scope_revision=2,
					scope_total_amount=200,
					approved_amount=200,
					status="Approved",
				),
			],
			existing_jobs={"RJ-1"},
			existing_auths={"AUTH-ORPHAN"},
		)

		with (
			patch(
				"auto_service_management.patches.phase15_backfill_service_scope_revisions.frappe",
				fake_frappe,
			),
			patch(
				"auto_service_management.patches.phase15_backfill_service_scope_revisions.get_repair_job_services",
				return_value=[SimpleNamespace(status="Approved", total_amount=80)],
			),
		):
			_backfill_service_scope_revisions()

		self.assertEqual(
			[
				("Repair Job", "RJ-1", {"scope_revision": 1, "total_amount": 80.0}, False),
			],
			[call for call in fake_frappe.db.set_values if call[0] == "Repair Job"],
		)
		self.assertTrue(
			any(
				"not linked to an existing Repair Job" in message
				for _, message in fake_frappe.logger_obj.messages
			)
		)

	def test_backfill_is_noop_when_tables_missing(self):
		fake_frappe = FakeFrappe(jobs=["RJ-1"], authorizations=[])
		fake_frappe.db.table_exists = lambda doctype: doctype != "Customer Authorization"

		with patch(
			"auto_service_management.patches.phase15_backfill_service_scope_revisions.frappe",
			fake_frappe,
		):
			_backfill_service_scope_revisions()

		self.assertEqual([], fake_frappe.db.set_values)
		self.assertEqual([], fake_frappe.logger_obj.messages)
