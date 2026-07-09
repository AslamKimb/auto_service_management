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

	def test_legacy_component_type_aliases_are_normalized(self):
		line = frappe.get_doc(
			{
				"doctype": "Repair Service Line",
				"service_type": "Parts",
				"service_description": "Battery",
				"quantity": 1,
				"rate": 250000,
			}
		)
		line.normalize_component()

		self.assertEqual(line.service_type, "Part")

	def test_cost_and_margin_are_calculated(self):
		line = frappe.get_doc(
			{
				"doctype": "Repair Service Line",
				"service_type": "Part",
				"service_description": "Battery",
				"quantity": 2,
				"rate": 150000,
				"cost_rate": 100000,
				"discount_percentage": 10,
			}
		)
		line.calculate_amount()

		self.assertEqual(line.amount, 270000)
		self.assertEqual(line.cost_amount, 200000)
		self.assertEqual(line.margin_amount, 70000)
