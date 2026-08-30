from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.customer_lpo.customer_lpo import (
	CustomerLPO,
	normalize_registration_number,
)


class TestCustomerLPO(UnitTestCase):
	def test_registration_number_is_normalized(self):
		self.assertEqual(normalize_registration_number(" uba-482m "), "UBA482M")

	def test_effective_authorization_includes_submitted_amendments(self):
		lpo = CustomerLPO(
			{
				"doctype": "Customer LPO",
				"name": "LPO-2026-00001",
				"authorized_amount": 1_000,
			}
		)
		module = "auto_service_management.auto_service_management.doctype.customer_lpo.customer_lpo.frappe"
		with patch(
			f"{module}.get_all",
			return_value=[frappe._dict(amount_increase=150), frappe._dict(amount_increase=50)],
		):
			self.assertEqual(lpo.get_effective_authorized_amount(), 1_200)

	def test_effective_expiry_uses_latest_submitted_amendment(self):
		lpo = CustomerLPO(
			{
				"doctype": "Customer LPO",
				"name": "LPO-2026-00001",
				"expiry_date": "2026-03-31",
			}
		)
		module = "auto_service_management.auto_service_management.doctype.customer_lpo.customer_lpo.frappe"
		with patch(
			f"{module}.get_all",
			return_value=[
				frappe._dict(replacement_expiry="2026-04-30"),
				frappe._dict(replacement_expiry="2026-04-15"),
			],
		):
			self.assertEqual(lpo.get_effective_expiry_date(), date(2026, 4, 30))

	def test_duplicate_normalized_registrations_are_rejected(self):
		lpo = self._lpo(
			[
				{"registration_number": "UBA 482M"},
				{"registration_number": "UBA-482M"},
			]
		)
		with self.assertRaises(frappe.ValidationError):
			lpo.validate_vehicle_rows()

	def test_customer_vehicle_is_required_for_every_lpo_row(self):
		lpo = self._lpo([{}])
		with self.assertRaisesRegex(frappe.ValidationError, "Customer Vehicle"):
			lpo.validate_customer_vehicle_ownership()

	def test_customer_vehicle_cannot_appear_twice(self):
		lpo = self._lpo(
			[
				{"customer_vehicle": "CV-1"},
				{"customer_vehicle": "CV-1"},
			]
		)
		with self.assertRaisesRegex(frappe.ValidationError, "appears more than once"):
			lpo.validate_customer_vehicle_ownership()

	def test_registration_is_derived_from_the_selected_customer_vehicle(self):
		lpo = self._lpo([{"customer_vehicle": "CV-1"}])
		module = "auto_service_management.auto_service_management.doctype.customer_lpo.customer_lpo.frappe"
		with patch(
			f"{module}.get_all",
			return_value=[
				frappe._dict(
					name="CV-1",
					customer="Test Customer",
					registration_number=" uba-482m ",
				)
			],
		):
			lpo.validate_customer_vehicle_ownership()
		self.assertEqual(lpo.vehicle_rows[0].registration_number, "UBA482M")

	def test_customer_vehicle_requires_a_registration_snapshot(self):
		lpo = self._lpo([{"customer_vehicle": "CV-1"}])
		module = "auto_service_management.auto_service_management.doctype.customer_lpo.customer_lpo.frappe"
		with patch(
			f"{module}.get_all",
			return_value=[
				frappe._dict(name="CV-1", customer="Test Customer", registration_number=None)
			],
		):
			with self.assertRaisesRegex(frappe.ValidationError, "registration number"):
				lpo.validate_customer_vehicle_ownership()

	def test_customer_vehicle_must_belong_to_lpo_customer(self):
		lpo = self._lpo([{"customer_vehicle": "UBA-482M"}])
		module = "auto_service_management.auto_service_management.doctype.customer_lpo.customer_lpo.frappe"
		with patch(
			f"{module}.get_all",
			return_value=[
				frappe._dict(
					name="UBA-482M",
					customer="OTHER CUSTOMER",
					registration_number="UBA482M",
				)
			],
		):
			with self.assertRaises(frappe.ValidationError):
				lpo.validate_customer_vehicle_ownership()

	def test_allocated_ceilings_cannot_exceed_effective_authorization(self):
		lpo = self._lpo(
			[
				{"registration_number": "UBA 482M", "allocated_ceiling": 700},
				{"registration_number": "UBA 483M", "allocated_ceiling": 400},
			],
			authorized_amount=1_000,
		)
		with self.assertRaises(frappe.ValidationError):
			lpo.validate_allocated_ceilings()

	def test_status_is_derived_from_docstatus_expiry_and_balance(self):
		active = self._lpo([], authorized_amount=1_000)
		active.docstatus = 1
		active.expiry_date = "2099-12-31"
		self.assertEqual(active.calculate_status(as_of=date(2026, 8, 25)), "Active")

		expired = self._lpo([], authorized_amount=1_000)
		expired.docstatus = 1
		expired.expiry_date = "2026-01-01"
		self.assertEqual(expired.calculate_status(as_of=date(2026, 8, 25)), "Expired")

		cancelled = self._lpo([], authorized_amount=1_000)
		cancelled.docstatus = 2
		self.assertEqual(cancelled.calculate_status(as_of=date(2026, 8, 25)), "Cancelled")

	def test_submit_requires_source_lpo_and_vehicle_rows(self):
		lpo = self._lpo([])
		with self.assertRaises(frappe.ValidationError):
			lpo.before_submit()

	def _lpo(self, rows, authorized_amount=1_000):
		return CustomerLPO(
			{
				"doctype": "Customer LPO",
				"company": "Test Company",
				"customer": "Test Customer",
				"lpo_number": "CUSTOMER-LPO-001",
				"issue_date": "2026-08-25",
				"expiry_date": "2026-12-31",
				"currency": "UGX",
				"ceiling_basis": "Tax Inclusive",
				"authorized_amount": authorized_amount,
				"vehicle_rows": rows,
			}
		)
