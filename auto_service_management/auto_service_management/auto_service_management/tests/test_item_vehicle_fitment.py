# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase


class TestItemVehicleFitment(UnitTestCase):
	def test_vehicle_engine_master_contract(self):
		meta = frappe.get_meta("Vehicle Engine")

		self.assertEqual(meta.autoname, "field:engine_code")
		self.assertEqual(meta.title_field, "engine_code")
		self.assertEqual(meta.get_field("engine_code").fieldtype, "Data")
		self.assertTrue(meta.get_field("engine_code").reqd)
		self.assertTrue(meta.get_field("engine_code").unique)
		self.assertEqual(meta.get_field("engine_name").fieldtype, "Data")
		self.assertEqual(meta.get_field("technical_notes").fieldtype, "Small Text")

	def test_customer_vehicle_keeps_engine_serial_and_adds_engine_model(self):
		meta = frappe.get_meta("Customer Vehicle")

		self.assertEqual(meta.get_field("engine_number").fieldtype, "Data")
		self.assertEqual(meta.get_field("engine_model").fieldtype, "Link")
		self.assertEqual(meta.get_field("engine_model").options, "Vehicle Engine")

	def test_fitment_master_contract(self):
		meta = frappe.get_meta("Item Vehicle Fitment")

		self.assertEqual(meta.get_field("item").fieldtype, "Link")
		self.assertEqual(meta.get_field("item").options, "Item")
		self.assertTrue(meta.get_field("item").reqd)
		self.assertEqual(meta.get_field("vehicle_make").options, "Vehicle Make")
		self.assertEqual(meta.get_field("vehicle_model").options, "Vehicle Model")
		self.assertEqual(meta.get_field("vehicle_engine").options, "Vehicle Engine")
		self.assertEqual(meta.get_field("year_from").fieldtype, "Int")
		self.assertEqual(meta.get_field("year_to").fieldtype, "Int")
		self.assertEqual(meta.get_field("verification_status").fieldtype, "Select")
		self.assertEqual(meta.get_field("verification_status").default, "Provisional")
		self.assertEqual(
			meta.get_field("verification_status").options.splitlines(),
			["Provisional", "Verified"],
		)

	def test_fitment_lookup_fields_match_compatibility_contract(self):
		from auto_service_management.auto_service_management.item_fitment_compatibility import FITMENT_FIELDS

		self.assertEqual(
			FITMENT_FIELDS,
			[
				"name",
				"item",
				"vehicle_make",
				"vehicle_model",
				"vehicle_engine",
				"year_from",
				"year_to",
				"verification_status",
				"notes",
				"source",
			],
		)

	def test_model_without_make_is_rejected(self):
		doc = frappe.new_doc("Item Vehicle Fitment")
		doc.update({"item": "_Test Item", "vehicle_model": "Toyota - Hilux"})

		with self.assertRaises(frappe.ValidationError):
			doc.validate()

	def test_model_must_belong_to_make(self):
		doc = frappe.new_doc("Item Vehicle Fitment")
		doc.update(
			{
				"item": "_Test Item",
				"vehicle_make": "Toyota",
				"vehicle_model": "Toyota - Hilux",
			}
		)

		with patch.object(frappe.db, "get_value", return_value="Ford"):
			with self.assertRaises(frappe.ValidationError):
				doc.validate()

	def test_reversed_year_range_is_rejected(self):
		doc = frappe.new_doc("Item Vehicle Fitment")
		doc.update({"item": "_Test Item", "year_from": 2024, "year_to": 2020})

		with self.assertRaises(frappe.ValidationError):
			doc.validate()

	def test_duplicate_fitment_key_is_rejected(self):
		doc = frappe.new_doc("Item Vehicle Fitment")
		doc.update(
			{
				"item": "_Test Item",
				"vehicle_make": "Toyota",
				"vehicle_model": "Toyota - Hilux",
				"vehicle_engine": "YD25",
				"year_from": 2015,
				"year_to": 2020,
			}
		)

		with (
			patch.object(frappe.db, "get_value", return_value="Toyota"),
			patch.object(frappe.db, "exists", return_value="IVF-00001") as exists,
		):
			with self.assertRaises(frappe.ValidationError):
				doc.validate()

		exists.assert_called_once()
		self.assertEqual(exists.call_args.args[0], "Item Vehicle Fitment")
		self.assertEqual(exists.call_args.args[1]["item"], "_Test Item")
		self.assertEqual(exists.call_args.args[1]["vehicle_make"], "Toyota")
		self.assertEqual(exists.call_args.args[1]["vehicle_model"], "Toyota - Hilux")
		self.assertEqual(exists.call_args.args[1]["vehicle_engine"], "YD25")
		self.assertEqual(exists.call_args.args[1]["year_from"], 2015)
		self.assertEqual(exists.call_args.args[1]["year_to"], 2020)
