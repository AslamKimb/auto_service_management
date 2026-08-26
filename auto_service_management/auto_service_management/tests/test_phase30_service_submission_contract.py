from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from auto_service_management.auto_service_management.doctype.repair_job_service import (
	repair_job_service as repair_job_service_module,
)
from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	RepairJobService,
)

MODULE_ROOT = Path(__file__).resolve().parents[1] / "auto_service_management"


class TestPhase30ServiceSubmissionContract(unittest.TestCase):
	def test_repair_job_service_is_not_submittable(self):
		meta = json.loads(
			(MODULE_ROOT / "doctype" / "repair_job_service" / "repair_job_service.json").read_text(
				encoding="utf-8"
			)
		)
		self.assertEqual(0, meta["is_submittable"])

	def test_workshop_bay_is_required_on_save(self):
		service = RepairJobService.__new__(RepairJobService)
		service.repair_job = "RJ-1"
		service.workshop_bay = None
		service.validate_diagnosis_report = lambda: None
		service.calculate_totals = lambda: None

		fake_frappe = SimpleNamespace(throw=lambda message: (_ for _ in ()).throw(Exception(message)))
		with (
			patch.object(repair_job_service_module, "frappe", fake_frappe),
			self.assertRaises(Exception) as ctx,
		):
			RepairJobService.validate(service)

		self.assertIn("Workshop Bay is required", str(ctx.exception))
