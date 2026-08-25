# Copyright (c) 2026, Aslam Kimbugwe and contributors

import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from auto_service_management.auto_service_management.item_fitment_compatibility import (
	_get_fitments,
	_vehicle_context,
	apply_fitment_snapshot,
	calculate_fitment_match,
	search_compatible_items,
)


def fitment(name, **values):
	return SimpleNamespace(name=name, **values)


class TestItemFitmentCompatibility(unittest.TestCase):
	def test_exact_verified_model_engine_year_match_wins(self):
		result = calculate_fitment_match(
			"Nissan",
			"Navara",
			"YD25",
			2021,
			[
				fitment("FIT-BROAD", vehicle_make="Nissan", vehicle_model="Navara"),
				fitment(
					"FIT-EXACT",
					vehicle_make="Nissan",
					vehicle_model="Navara",
					vehicle_engine="YD25",
					year_from=2020,
					year_to=2023,
					verification_status="Verified",
				),
			],
		)

		self.assertEqual("Exact Match", result["fitment_match_status"])
		self.assertEqual("FIT-EXACT", result["matched_fitment"])
		self.assertFalse(result["warning_required"])

	def test_provisional_exact_match_still_requires_override(self):
		result = calculate_fitment_match(
			"Toyota",
			"Hilux",
			"1KD",
			2020,
			[
				fitment(
					"FIT-PROVISIONAL",
					vehicle_make="Toyota",
					vehicle_model="Hilux",
					vehicle_engine="1KD",
					year_from=2018,
					year_to=2022,
					verification_status="Provisional",
				)
			],
		)

		self.assertEqual("Provisional Match", result["fitment_match_status"])
		self.assertTrue(result["warning_required"])

	def test_broad_make_model_match_is_ranked_before_universal(self):
		result = calculate_fitment_match(
			"Nissan",
			"Navara",
			"ZD30",
			None,
			[
				fitment("FIT-UNIVERSAL"),
				fitment("FIT-MODEL", vehicle_make="Nissan", vehicle_model="Navara"),
			],
		)

		self.assertEqual("Broad Match", result["fitment_match_status"])
		self.assertEqual("FIT-MODEL", result["matched_fitment"])

	def test_missing_fitment_and_mismatch_are_visible_warnings(self):
		missing = calculate_fitment_match("Nissan", "Navara", "YD25", 2021, [])
		mismatch = calculate_fitment_match(
			"Nissan", "Navara", "YD25", 2021,
			[fitment("FIT-TOYOTA", vehicle_make="Toyota", vehicle_model="Hilux")],
		)

		self.assertEqual("No Fitment Data", missing["fitment_match_status"])
		self.assertTrue(missing["warning_required"])
		self.assertEqual("Mismatch", mismatch["fitment_match_status"])
		self.assertTrue(mismatch["warning_required"])

	def test_apply_snapshot_requires_reason_for_warning_status(self):
		row = SimpleNamespace(
			item_code="ITEM-1",
			customer_vehicle="VEH-1",
			fitment_override_reason="",
		)

		with patch(
			"auto_service_management.auto_service_management.item_fitment_compatibility._doctype_exists",
			return_value=True,
		), patch(
			"auto_service_management.auto_service_management.item_fitment_compatibility._get_vehicle_context",
			return_value={
				"vehicle_make": "Nissan",
				"vehicle_model": "Navara",
				"vehicle_engine": "YD25",
				"vehicle_year": 2021,
			},
		), patch(
			"auto_service_management.auto_service_management.item_fitment_compatibility._get_fitments",
			return_value=[fitment("FIT-1", vehicle_make="Toyota", vehicle_model="Hilux")],
		):
			with self.assertRaisesRegex(Exception, "override reason"):
				apply_fitment_snapshot(row)

			self.assertEqual("Mismatch", row.fitment_match_status)

	def test_part_contract_has_snapshot_fields_and_get_lookup(self):
		root = Path(__file__).parents[1]
		part_json = json.loads(
			(root / "doctype" / "repair_job_service_part" / "repair_job_service_part.json").read_text()
		)
		fields = {field["fieldname"]: field for field in part_json["fields"]}
		self.assertIn("fitment_match_status", fields)
		self.assertIn("matched_fitment", fields)
		self.assertIn("fitment_override_reason", fields)

	def test_search_is_read_only_and_checks_permissions(self):
		fake_frappe = SimpleNamespace(
			request=SimpleNamespace(method="POST"),
			has_permission=lambda *args, **kwargs: True,
		)

		with patch(
			"auto_service_management.auto_service_management.item_fitment_compatibility.frappe",
			fake_frappe,
		):
			with self.assertRaises(Exception):
				search_compatible_items(item_search="filter")

	def test_fitment_lookup_uses_canonical_item_link(self):
		with patch(
			"auto_service_management.auto_service_management.item_fitment_compatibility._doctype_exists",
			return_value=True,
		), patch(
			"auto_service_management.auto_service_management.item_fitment_compatibility.frappe.get_all",
			return_value=[],
		) as get_all:
			_get_fitments("ITEM-1")

		get_all.assert_called_once()
		self.assertEqual({"item": "ITEM-1"}, get_all.call_args.kwargs["filters"])
		self.assertIn("item", get_all.call_args.kwargs["fields"])

	def test_vehicle_context_uses_engine_model_master_link(self):
		fake_vehicle = {
			"make": "Nissan",
			"model": "Navara",
			"engine_model": "YD25",
			"year_of_manufacture": 2021,
		}
		with patch(
			"auto_service_management.auto_service_management.item_fitment_compatibility.frappe.db.get_value",
			return_value=fake_vehicle,
		) as get_value:
			context = _vehicle_context("VEH-1", None, None, None, None)

		self.assertEqual("YD25", context["vehicle_engine"])
		self.assertIn("engine_model", get_value.call_args.args[2])


if __name__ == "__main__":
	unittest.main()
