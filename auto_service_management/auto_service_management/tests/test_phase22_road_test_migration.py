# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest

from auto_service_management.patches.phase13_migrate_road_tests import (
	_migrate_road_tests,
	_quality_check_road_test_exists,
)
from auto_service_management.auto_service_management.workflow_compatibility import (
	build_quality_check_road_test_row,
)


class TestPhase22RoadTestMigration(unittest.TestCase):
	def test_build_quality_check_road_test_row_maps_report_fields(self):
		road_test = SimpleNamespace(
			repair_job="RJ-1",
			customer_vehicle="VEH-1",
			test_date="2026-07-16 09:00:00",
			tested_by="tech@example.com",
			odometer_start=10,
			odometer_end=18,
			duration_minutes=30,
			route="Depot loop",
			braking_ok=1,
			steering_ok=1,
			engine_performance_ok=1,
			transmission_ok=1,
			no_warning_lights=1,
			test_notes="All good",
		)

		row = build_quality_check_road_test_row("QC-1", road_test, "RJ-1", "VEH-1")

		self.assertEqual(row["quality_check"], "QC-1")
		self.assertEqual(row["repair_job"], "RJ-1")
		self.assertEqual(row["customer_vehicle"], "VEH-1")
		self.assertEqual(row["odometer_end"], 18)
		self.assertEqual(row["test_notes"], "All good")

	def test_quality_check_road_test_exists_detects_exact_duplicate(self):
		fake_exists = Mock(return_value=True)
		fake_frappe = SimpleNamespace(db=SimpleNamespace(exists=fake_exists))
		row = {
			"quality_check": "QC-1",
			"repair_job": "RJ-1",
			"customer_vehicle": "VEH-1",
			"test_date": "2026-07-16 09:00:00",
			"tested_by": "tech@example.com",
			"odometer_start": 10,
			"odometer_end": 18,
			"duration_minutes": 30,
			"route": "Depot loop",
			"braking_ok": 1,
			"steering_ok": 1,
			"engine_performance_ok": 1,
			"transmission_ok": 1,
			"no_warning_lights": 1,
			"test_notes": "All good",
		}

		with patch("auto_service_management.patches.phase13_migrate_road_tests.frappe", fake_frappe):
			self.assertTrue(_quality_check_road_test_exists(row))

	def test_migrate_road_tests_creates_missing_quality_check_and_child_row(self):
		road_test = SimpleNamespace(
			name="RT-1",
			repair_job="RJ-1",
			customer_vehicle="VEH-1",
			test_date="2026-07-16 09:00:00",
			tested_by="tech@example.com",
			odometer_start=10,
			odometer_end=18,
			duration_minutes=30,
			route="Depot loop",
			braking_ok=1,
			steering_ok=1,
			engine_performance_ok=1,
			transmission_ok=1,
			no_warning_lights=1,
			test_notes="All good",
			owner="tester@example.com",
			creation="2026-07-16 08:00:00",
			modified="2026-07-16 09:00:00",
			modified_by="tester@example.com",
		)
		quality_check_doc = SimpleNamespace(
			doctype="Quality Check",
			repair_job=road_test.repair_job,
			customer_vehicle=road_test.customer_vehicle,
			qc_date=road_test.test_date,
			checked_by=road_test.tested_by,
			status="Pending",
			name=None,
		)
		sql_calls = []
		set_value = Mock()

		def fake_get_doc(doctype, name=None):
			if doctype == "Road Test Report":
				return road_test
			if isinstance(doctype, dict) and doctype.get("doctype") == "Quality Check":
				return quality_check_doc
			raise AssertionError((doctype, name))

		def fake_exists(*args, **kwargs):
			return False

		def fake_get_value(*args, **kwargs):
			return None

		def fake_sql(query, values):
			sql_calls.append((query, values))

		fake_frappe = SimpleNamespace(
			db=SimpleNamespace(
				table_exists=lambda doctype: True,
				exists=fake_exists,
				get_value=fake_get_value,
				count=lambda *args, **kwargs: 0,
				set_value=set_value,
				sql=fake_sql,
			),
			get_all=lambda *args, **kwargs: [SimpleNamespace(name="RT-1")],
			get_doc=fake_get_doc,
			generate_hash=lambda length=10: "HASH123456",
			session=SimpleNamespace(user="Administrator"),
		)

		with (
			patch("auto_service_management.patches.phase13_migrate_road_tests.frappe", fake_frappe),
			patch("auto_service_management.patches.phase13_migrate_road_tests.set_new_name", lambda doc: setattr(doc, "name", "QC-1")),
		):
			_migrate_road_tests()

		self.assertEqual(quality_check_doc.name, "QC-1")
		self.assertEqual(len(sql_calls), 2)
		self.assertTrue(sql_calls[0][0].startswith("INSERT INTO `tabQuality Check`"))
		self.assertTrue(sql_calls[1][0].startswith("INSERT INTO `tabQuality Check Road Test`"))
		set_value.assert_called_once_with("Repair Job", "RJ-1", "quality_check", "QC-1", update_modified=False)
