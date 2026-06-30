# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from auto_service_management.auto_service_management.doctype.repair_service_line.repair_service_line import (
	RepairServiceLine,
)


class TestRepairServiceLine(IntegrationTestCase):
	def test_amount_calculation(self):
		"""Amount must equal quantity * rate."""
		line = frappe.get_doc(
			{
				"doctype": "Repair Service Line",
				"service_type": "Labour",
				"service_description": "Engine oil change",
				"quantity": 2,
				"rate": 50000,
			}
		)
		line.calculate_amount()
		self.assertEqual(line.amount, 100000)

	def test_zero_quantity(self):
		line = frappe.get_doc(
			{
				"doctype": "Repair Service Line",
				"service_type": "Labour",
				"service_description": "Test",
				"quantity": 0,
				"rate": 50000,
			}
		)
		line.calculate_amount()
		self.assertEqual(line.amount, 0)

	def test_zero_rate(self):
		line = frappe.get_doc(
			{
				"doctype": "Repair Service Line",
				"service_type": "Labour",
				"service_description": "Test",
				"quantity": 5,
				"rate": 0,
			}
		)
		line.calculate_amount()
		self.assertEqual(line.amount, 0)
