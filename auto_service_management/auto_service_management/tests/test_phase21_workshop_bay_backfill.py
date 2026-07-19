# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest.mock import patch
import unittest

from auto_service_management.patches.phase12_backfill_workshop_bays import (
	_backfill_workshop_bays,
)
from auto_service_management.auto_service_management.workflow_compatibility import (
	build_repair_job_service_workshop_bay_rows,
	_get_enabled_job_workshop_bay,
)


class _ServiceProbe:
	def __init__(self, name, status="Approved", workshop_bay=None, docstatus=0):
		self.name = name
		self.status = status
		self.workshop_bay = workshop_bay
		self.docstatus = docstatus


class TestPhase21WorkshopBayBackfill(unittest.TestCase):
	def test_build_repair_job_service_workshop_bay_rows_returns_rows_and_exceptions(self):
		services = [
			_ServiceProbe("SVC-1", docstatus=0),
			_ServiceProbe("SVC-2", workshop_bay="BAY-2"),
			_ServiceProbe("SVC-3", status="Cancelled", docstatus=2),
		]

		with (
			patch(
				"auto_service_management.auto_service_management.workflow_compatibility.get_repair_job_services",
				return_value=services,
			),
			patch(
				"auto_service_management.auto_service_management.workflow_compatibility._get_enabled_job_workshop_bay",
				return_value="BAY-1",
			),
		):
			rows, exceptions = build_repair_job_service_workshop_bay_rows("RJ-1")

		self.assertEqual(rows, [{"repair_job": "RJ-1", "repair_job_service": "SVC-1", "workshop_bay": "BAY-1"}])
		self.assertEqual(exceptions, [])

	def test_build_repair_job_service_workshop_bay_rows_flags_unassigned_active_services(self):
		services = [
			_ServiceProbe("SVC-1", docstatus=0),
			_ServiceProbe("SVC-2", status="Cancelled", docstatus=2),
		]

		with (
			patch(
				"auto_service_management.auto_service_management.workflow_compatibility.get_repair_job_services",
				return_value=services,
			),
			patch(
				"auto_service_management.auto_service_management.workflow_compatibility._get_enabled_job_workshop_bay",
				return_value=None,
			),
		):
			rows, exceptions = build_repair_job_service_workshop_bay_rows("RJ-1")

		self.assertEqual(rows, [])
		self.assertEqual(
			exceptions,
			[
				{
					"repair_job": "RJ-1",
					"repair_job_service": "SVC-1",
					"docstatus": 0,
					"reason": "Repair Job has no enabled Workshop Bay",
				}
			],
		)

	def test_enabled_job_workshop_bay_ignores_under_maintenance_bays(self):
		fake_frappe = SimpleNamespace(
			db=SimpleNamespace(
				exists=lambda doctype, name: doctype == "Repair Job" or doctype == "Workshop Bay",
				get_value=lambda doctype, name, field: "Under Maintenance" if field == "status" else "BAY-1",
			)
		)

		with patch("auto_service_management.auto_service_management.workflow_compatibility.frappe", fake_frappe):
			bay_name = _get_enabled_job_workshop_bay("RJ-1")

		self.assertIsNone(bay_name)

	def test_backfill_patch_updates_services_and_logs_exceptions(self):
		service = SimpleNamespace(name="SVC-1", workshop_bay=None, save=unittest.mock.Mock())
		logger = SimpleNamespace(warning=unittest.mock.Mock())
		fake_frappe = SimpleNamespace(
			db=SimpleNamespace(
				table_exists=lambda doctype: doctype in {"Repair Job", "Repair Job Service"},
				get_all=lambda *args, **kwargs: ["RJ-1"],
			),
			get_doc=lambda doctype, name: service,
			get_all=lambda *args, **kwargs: ["RJ-1"],
			logger=lambda name: logger,
		)

		with (
			patch(
				"auto_service_management.patches.phase12_backfill_workshop_bays.frappe",
				fake_frappe,
			),
			patch(
				"auto_service_management.patches.phase12_backfill_workshop_bays.build_repair_job_service_workshop_bay_rows",
				return_value=(
					[{"repair_job": "RJ-1", "repair_job_service": "SVC-1", "workshop_bay": "BAY-1"}],
					[{"repair_job": "RJ-1", "repair_job_service": "SVC-2", "docstatus": 0, "reason": "Repair Job has no enabled Workshop Bay"}],
				),
			),
		):
			_backfill_workshop_bays()

		self.assertEqual(service.workshop_bay, "BAY-1")
		service.save.assert_called_once_with(ignore_permissions=True)
		logger.warning.assert_called_once()
