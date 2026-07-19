# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest.mock import patch
import unittest

from auto_service_management.auto_service_management.workflow_compatibility import (
	bump_repair_job_scope_revision,
	build_quality_check_road_test_rows,
	build_repair_job_service_rows,
	recompute_repair_job_state,
	_derive_repair_job_status,
	sync_repair_job_compatibility_views,
)


class _FakeDoc:
	def __init__(self, doctype, name, **values):
		object.__setattr__(self, "doctype", doctype)
		object.__setattr__(self, "name", name)
		object.__setattr__(self, "flags", SimpleNamespace())
		object.__setattr__(self, "_values", values)

	def is_new(self):
		return False

	def precision(self, fieldname):
		return 2

	def get(self, fieldname, default=None):
		return self._values.get(fieldname, default)

	def set(self, fieldname, value):
		self._values[fieldname] = value

	def __getattr__(self, fieldname):
		try:
			return self._values[fieldname]
		except KeyError as exc:
			raise AttributeError(fieldname) from exc

	def __setattr__(self, fieldname, value):
		if fieldname in {"doctype", "name", "flags", "_values"}:
			object.__setattr__(self, fieldname, value)
			return
		self._values[fieldname] = value

	def save(self, ignore_permissions=False):
		self._values["save_called"] = True
		return self


class TestWorkflowCompatibility(unittest.TestCase):
	def test_sync_repair_job_compatibility_views_populates_mirror_tables(self):
		job = _FakeDoc("Repair Job", "RJ-1", job_status="Billing")

		with (
			patch(
				"auto_service_management.auto_service_management.workflow_compatibility.build_repair_job_service_rows",
				return_value=[
					{
						"repair_job": "RJ-1",
						"repair_job_service": "SVC-1",
						"service_name": "Diagnosis",
						"workshop_bay": "BAY-1",
						"total_amount": 125,
						"payment_status": "Partially Paid",
					}
				],
			),
			patch(
				"auto_service_management.auto_service_management.workflow_compatibility.build_repair_job_invoice_rows",
				return_value=[
					{
						"repair_job": "RJ-1",
						"sales_invoice": "INV-1",
						"posting_date": "2026-07-16",
						"grand_total": 125,
						"paid_amount": 75,
						"outstanding_amount": 50,
					}
				],
			),
			patch(
				"auto_service_management.auto_service_management.workflow_compatibility.build_repair_job_payment_rows",
				return_value=[
					{
						"repair_job": "RJ-1",
						"payment_entry": "PE-1",
						"reference_invoice": "INV-1",
						"posting_date": "2026-07-16",
						"allocated_amount": 75,
					}
				],
			),
		):
			sync_repair_job_compatibility_views(job)

		self.assertEqual(job.repair_job_services[0]["repair_job_service"], "SVC-1")
		self.assertEqual(job.sales_invoices[0]["sales_invoice"], "INV-1")
		self.assertEqual(job.payment_entries[0]["payment_entry"], "PE-1")
		self.assertEqual(job.scope_revision, 1)
		self.assertEqual(job.payment_total, 75)
		self.assertEqual(job.payment_status, "Partially Paid")

	def test_scope_revision_is_monotonic_across_compatibility_syncs(self):
		job = _FakeDoc("Repair Job", "RJ-1", scope_revision=5)

		with (
			patch(
				"auto_service_management.auto_service_management.workflow_compatibility.build_repair_job_service_rows",
				return_value=[
					{
						"repair_job": "RJ-1",
						"repair_job_service": "SVC-1",
						"service_name": "Diagnosis",
						"workshop_bay": "BAY-1",
						"total_amount": 125,
						"payment_status": "Unpaid",
					}
				],
			),
			patch(
				"auto_service_management.auto_service_management.workflow_compatibility.build_repair_job_invoice_rows",
				return_value=[],
			),
			patch(
				"auto_service_management.auto_service_management.workflow_compatibility.build_repair_job_payment_rows",
				return_value=[],
			),
		):
			sync_repair_job_compatibility_views(job)

		self.assertEqual(job.scope_revision, 5)

	def test_bump_repair_job_scope_revision_increments_parent_counter(self):
		class _FakeDB:
			def __init__(self):
				self.values = []

			def exists(self, doctype, name):
				return True

			def get_value(self, doctype, name, fieldname):
				return 7

			def set_value(self, doctype, name, fieldname, value, update_modified=False):
				self.values.append((doctype, name, fieldname, value, update_modified))

		fake_frappe = SimpleNamespace(db=_FakeDB())

		with patch("auto_service_management.auto_service_management.workflow_compatibility.frappe", fake_frappe):
			bump_repair_job_scope_revision("RJ-1")

		self.assertEqual(
			[("Repair Job", "RJ-1", "scope_revision", 8, False)],
			fake_frappe.db.values,
		)

	def test_derive_repair_job_status_prefers_ready_for_invoice_when_all_components_submitted(self):
		job = SimpleNamespace(name="RJ-1", job_status="Billing")

		with patch(
			"auto_service_management.auto_service_management.workflow_compatibility._all_billable_components_submitted",
			return_value=True,
		), patch(
			"auto_service_management.auto_service_management.workflow_compatibility._has_any_billable_invoice",
			return_value=True,
		), patch(
			"auto_service_management.auto_service_management.workflow_compatibility._get_linked_doc",
			return_value=None,
		):
			self.assertEqual("Ready for Invoice", _derive_repair_job_status(job))

	def test_derive_repair_job_status_uses_authorization_and_work_started_signals(self):
		job = SimpleNamespace(name="RJ-1", job_status="In Repair")
		authorization = SimpleNamespace(docstatus=1)

		with patch(
			"auto_service_management.auto_service_management.workflow_compatibility._all_billable_components_submitted",
			return_value=False,
		), patch(
			"auto_service_management.auto_service_management.workflow_compatibility._has_any_billable_invoice",
			return_value=False,
		), patch(
			"auto_service_management.auto_service_management.workflow_compatibility._has_work_started",
			return_value=True,
		), patch(
			"auto_service_management.auto_service_management.workflow_compatibility._get_linked_doc",
			side_effect=lambda repair_job_name, doctype: authorization if doctype == "Customer Authorization" else None,
		):
			self.assertEqual("In Repair", _derive_repair_job_status(job))

	def test_recompute_repair_job_state_saves_new_status(self):
		job = _FakeDoc("Repair Job", "RJ-1", job_status="Billing")

		class _FakeDB:
			def exists(self, doctype, name):
				return True

		fake_frappe = SimpleNamespace(
			db=_FakeDB(),
			get_doc=lambda doctype, name: job,
		)

		with patch(
			"auto_service_management.auto_service_management.workflow_compatibility.frappe",
			fake_frappe,
		), patch(
			"auto_service_management.auto_service_management.workflow_compatibility._derive_repair_job_status",
			return_value="Ready for Release",
		):
			recompute_repair_job_state("RJ-1")

		self.assertEqual("Ready for Release", job.job_status)

	def test_build_repair_job_service_rows_uses_service_summary(self):
		service = SimpleNamespace(
			name="SVC-1",
			service_name="Diagnosis",
			workshop_bay="BAY-1",
			total_amount=125,
		)

		with patch(
			"auto_service_management.auto_service_management.workflow_compatibility.get_repair_job_services",
			return_value=[service],
		), patch(
			"auto_service_management.auto_service_management.workflow_compatibility._service_payment_status",
			return_value="Paid",
		):
			rows = build_repair_job_service_rows("RJ-1")

		self.assertEqual(rows, [
			{
				"repair_job": "RJ-1",
				"repair_job_service": "SVC-1",
				"service_name": "Diagnosis",
				"workshop_bay": "BAY-1",
				"total_amount": 125,
				"payment_status": "Paid",
			}
		])

	def test_build_quality_check_road_test_rows_mirrors_legacy_report(self):
		quality_check = _FakeDoc(
			"Quality Check",
			"QC-1",
			repair_job="RJ-1",
			customer_vehicle="VEH-1",
		)
		self.assertEqual([], build_quality_check_road_test_rows(quality_check))
