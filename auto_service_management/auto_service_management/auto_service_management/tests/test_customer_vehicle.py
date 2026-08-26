# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from auto_service_management.patches.vehicle_make_model_catalog import (
	_resolve_legacy_values,
)
from auto_service_management.patches.vehicle_make_model_catalog import (
	execute as seed_vehicle_catalog,
)
from auto_service_management.vehicle_catalog import DEFAULT_VEHICLE_CATALOG


def _ensure_erpnext_basics():
	"""Create minimal ERPNext setup data if missing."""
	# Customer Group
	if not frappe.db.exists("Customer Group", {"is_group": 0, "name": "All Customer Groups"}):
		if not frappe.db.exists("Customer Group", "All Customer Groups"):
			frappe.get_doc(
				{
					"doctype": "Customer Group",
					"customer_group_name": "All Customer Groups",
					"is_group": 1,
					"parent_customer_group": "",
				}
			).insert(ignore_permissions=True)
	if not frappe.db.exists("Customer Group", {"is_group": 0, "name": "Commercial"}):
		frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": "Commercial",
				"is_group": 0,
				"parent_customer_group": "All Customer Groups",
			}
		).insert(ignore_permissions=True)

	# Territory
	if not frappe.db.exists("Territory", "All Territories"):
		frappe.get_doc(
			{
				"doctype": "Territory",
				"territory_name": "All Territories",
				"is_group": 1,
				"parent_territory": "",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Territory", {"is_group": 0, "name": "Uganda"}):
		frappe.get_doc(
			{
				"doctype": "Territory",
				"territory_name": "Uganda",
				"is_group": 0,
				"parent_territory": "All Territories",
			}
		).insert(ignore_permissions=True)


def _get_or_create_test_customer():
	"""Create or reuse a test Customer for vehicle tests."""
	_ensure_erpnext_basics()
	customer_name = frappe.db.get_value("Customer", {"customer_name": "Test Workshop Customer"}, "name")
	if not customer_name:
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "Test Workshop Customer",
				"customer_group": "Commercial",
				"territory": "Uganda",
			}
		)
		customer.insert(ignore_permissions=True)
		customer_name = customer.name
	return customer_name


class TestCustomerVehicle(IntegrationTestCase):
	def test_make_and_model_are_filtered_links(self):
		vehicle_meta = frappe.get_meta("Customer Vehicle")
		self.assertEqual(vehicle_meta.get_field("make").fieldtype, "Link")
		self.assertEqual(vehicle_meta.get_field("make").options, "Vehicle Make")
		self.assertEqual(vehicle_meta.get_field("model").fieldtype, "Link")
		self.assertEqual(vehicle_meta.get_field("model").options, "Vehicle Model")

		model_meta = frappe.get_meta("Vehicle Model")
		self.assertEqual(model_meta.get_field("vehicle_make").options, "Vehicle Make")
		self.assertEqual(model_meta.get_field("model_name").fieldtype, "Data")
		self.assertEqual(model_meta.title_field, "model_name")

	def test_catalog_is_unique_and_idempotent(self):
		pairs = [(make, model) for make, models in DEFAULT_VEHICLE_CATALOG.items() for model in models]
		self.assertEqual(len(pairs), len(set(pairs)))

		seed_vehicle_catalog()
		first_counts = (
			frappe.db.count("Vehicle Make"),
			frappe.db.count("Vehicle Model"),
		)
		seed_vehicle_catalog()
		self.assertEqual(
			first_counts,
			(frappe.db.count("Vehicle Make"), frappe.db.count("Vehicle Model")),
		)

	def test_same_model_name_can_belong_to_multiple_makes(self):
		seed_vehicle_catalog()
		ford_ranger = frappe.db.get_value("Vehicle Model", {"vehicle_make": "Ford", "model_name": "Ranger"})
		hino_ranger = frappe.db.get_value("Vehicle Model", {"vehicle_make": "Hino", "model_name": "Ranger"})
		self.assertNotEqual(ford_ranger, hino_ranger)
		self.assertEqual(_resolve_legacy_values("", "Ranger"), ("Unspecified", "Ranger"))
		self.assertEqual(_resolve_legacy_values("Toyota", "Toyota - Hilux"), ("Toyota", "Hilux"))

	def test_blank_make_and_model_are_preserved(self):
		customer = _get_or_create_test_customer()
		registration = "TEST-LINK-BLANK"
		frappe.db.delete("Customer Vehicle", {"registration_number": registration})
		vehicle = frappe.get_doc(
			{
				"doctype": "Customer Vehicle",
				"customer": customer,
				"registration_number": registration,
			}
		).insert(ignore_permissions=True)
		self.assertFalse(vehicle.make)
		self.assertFalse(vehicle.model)
		frappe.delete_doc("Customer Vehicle", vehicle.name, ignore_permissions=True)

	def test_model_must_belong_to_make(self):
		seed_vehicle_catalog()
		customer = _get_or_create_test_customer()
		valid_registration = "TEST-LINK-VALID"
		invalid_registration = "TEST-LINK-INVALID"
		frappe.db.delete(
			"Customer Vehicle", {"registration_number": ["in", [valid_registration, invalid_registration]]}
		)

		valid_vehicle = frappe.get_doc(
			{
				"doctype": "Customer Vehicle",
				"customer": customer,
				"registration_number": valid_registration,
				"make": "Toyota",
				"model": "Toyota - Hilux",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(valid_vehicle.model, "Toyota - Hilux")

		invalid_vehicle = frappe.get_doc(
			{
				"doctype": "Customer Vehicle",
				"customer": customer,
				"registration_number": invalid_registration,
				"make": "Toyota",
				"model": "Nissan - March",
			}
		)
		self.assertRaises(frappe.ValidationError, invalid_vehicle.insert)

		frappe.delete_doc("Customer Vehicle", valid_vehicle.name, ignore_permissions=True)

	def test_model_without_make_is_rejected(self):
		seed_vehicle_catalog()
		customer = _get_or_create_test_customer()
		registration = "TEST-LINK-NO-MAKE"
		frappe.db.delete("Customer Vehicle", {"registration_number": registration})
		vehicle = frappe.get_doc(
			{
				"doctype": "Customer Vehicle",
				"customer": customer,
				"registration_number": registration,
				"model": "Toyota - Hilux",
			}
		)
		self.assertRaises(frappe.ValidationError, vehicle.insert)

	def test_repair_job_vehicle_details_use_model_title(self):
		seed_vehicle_catalog()
		customer = _get_or_create_test_customer()
		registration = "TEST-LINK-DISPLAY"
		frappe.db.delete("Customer Vehicle", {"registration_number": registration})
		vehicle = frappe.get_doc(
			{
				"doctype": "Customer Vehicle",
				"customer": customer,
				"registration_number": registration,
				"make": "Toyota",
				"model": "Toyota - Hilux",
				"year_of_manufacture": 2020,
			}
		).insert(ignore_permissions=True)

		job = frappe.new_doc("Repair Job")
		job.customer_vehicle = vehicle.name
		job.fetch_vehicle_details()
		self.assertEqual(job.vehicle_details, "Toyota Hilux 2020")

		frappe.delete_doc("Customer Vehicle", vehicle.name, ignore_permissions=True)

	def test_duplicate_vin_blocked(self):
		"""Two vehicles with the same VIN should not coexist."""
		customer = _get_or_create_test_customer()

		if frappe.db.exists("Customer Vehicle", {"vin_chassis_number": "TESTVIN123"}):
			frappe.db.sql("DELETE FROM `tabCustomer Vehicle` WHERE vin_chassis_number='TESTVIN123'")

		v1 = frappe.get_doc(
			{
				"doctype": "Customer Vehicle",
				"customer": customer,
				"registration_number": "TEST-REG-001",
				"vin_chassis_number": "TESTVIN123",
			}
		)
		v1.insert(ignore_permissions=True)

		v2 = frappe.get_doc(
			{
				"doctype": "Customer Vehicle",
				"customer": customer,
				"registration_number": "TEST-REG-002",
				"vin_chassis_number": "TESTVIN123",
			}
		)
		self.assertRaises(frappe.ValidationError, v2.insert)

		# Cleanup
		frappe.db.sql("DELETE FROM `tabCustomer Vehicle` WHERE vin_chassis_number='TESTVIN123'")
