from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	RepairJobService,
)
from auto_service_management.auto_service_management.doctype.repair_job_service import (
	repair_job_service as repair_job_service_module,
)

MODULE_ROOT = Path(__file__).resolve().parents[1]


class TestPhase30ServiceSubmissionContract(unittest.TestCase):
	def test_repair_job_service_is_submittable(self):
		meta = json.loads((MODULE_ROOT / "doctype" / "repair_job_service" / "repair_job_service.json").read_text(encoding="utf-8"))
		self.assertEqual(1, meta["is_submittable"])

	def test_before_submit_defaults_workshop_bay_from_repair_job(self):
		service = RepairJobService.__new__(RepairJobService)
		service.repair_job = "RJ-1"
		service.workshop_bay = None
		service.sync_from_repair_job = lambda: None

		with patch.object(RepairJobService, "_get_submission_workshop_bay", return_value="BAY-1"):
			RepairJobService.before_submit(service)

		self.assertEqual("BAY-1", service.workshop_bay)

	def test_before_submit_blocks_without_any_workshop_bay(self):
		service = RepairJobService.__new__(RepairJobService)
		service.repair_job = "RJ-1"
		service.workshop_bay = None
		service.sync_from_repair_job = lambda: None

		fake_frappe = SimpleNamespace(throw=lambda message: (_ for _ in ()).throw(Exception(message)))
		with patch.object(RepairJobService, "_get_submission_workshop_bay", return_value=None), patch.object(
			repair_job_service_module, "frappe", fake_frappe
		), self.assertRaises(Exception) as ctx:
			RepairJobService.before_submit(service)

		self.assertIn("Workshop Bay is required", str(ctx.exception))
