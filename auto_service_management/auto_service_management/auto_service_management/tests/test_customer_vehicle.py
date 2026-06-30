# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase


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
