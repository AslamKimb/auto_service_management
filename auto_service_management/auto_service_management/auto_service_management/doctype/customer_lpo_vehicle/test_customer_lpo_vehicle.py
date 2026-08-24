import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.customer_lpo_vehicle.customer_lpo_vehicle import (
	CustomerLPOVehicle,
)


class TestCustomerLPOVehicle(UnitTestCase):
	def test_validate_normalizes_registration_number(self):
		row = CustomerLPOVehicle(
			{
				"doctype": "Customer LPO Vehicle",
				"registration_number": "uba 482m",
			}
		)
		row.validate()
		self.assertEqual(row.registration_number, "UBA482M")

	def test_validate_rejects_blank_registration_number(self):
		row = CustomerLPOVehicle({"doctype": "Customer LPO Vehicle"})
		with self.assertRaises(frappe.ValidationError):
			row.validate()
