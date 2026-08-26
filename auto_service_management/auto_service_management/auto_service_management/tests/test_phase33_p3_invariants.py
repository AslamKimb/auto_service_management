"""Focused P3 tests for normalized identifiers and database race guards."""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from auto_service_management.auto_service_management.doctype.customer_lpo.customer_lpo import (
	CustomerLPO,
	build_lpo_uniqueness_key,
	normalize_lpo_number,
)
from auto_service_management.auto_service_management.doctype.customer_vehicle.customer_vehicle import (
	CustomerVehicle,
	normalize_vin_chassis_number,
)
from auto_service_management.patches.phase33_identifier_invariants import (
	_reconcile_customer_lpos,
	_reconcile_customer_vehicles,
	validate_legacy_identifier_safety,
)


class TestP3IdentifierNormalization(UnitTestCase):
	def test_vin_normalization_preserves_blank_semantics(self):
		self.assertEqual(normalize_vin_chassis_number("  jh4  ka8260mc00001 "), "JH4KA8260MC00001")
		self.assertIsNone(normalize_vin_chassis_number(None))
		self.assertIsNone(normalize_vin_chassis_number(" \t "))

	def test_lpo_number_normalization_and_scoped_key(self):
		self.assertEqual(normalize_lpo_number("  po-2026-0042 "), "PO-2026-0042")
		self.assertIsNone(normalize_lpo_number("  "))
		first = build_lpo_uniqueness_key("Acme Ltd", "Customer A", "PO-2026-0042")
		second = build_lpo_uniqueness_key(" acme ltd ", "customer a", "po-2026-0042")
		other_customer = build_lpo_uniqueness_key("Acme Ltd", "Customer B", "PO-2026-0042")
		self.assertEqual(first, second)
		self.assertNotEqual(first, other_customer)
		self.assertIsNone(build_lpo_uniqueness_key("Acme Ltd", "", "PO-2026-0042"))

	def test_lpo_preflight_uses_normalized_scoped_values(self):
		lpo = CustomerLPO(
			{
				"doctype": "Customer LPO",
				"name": "LPO-2026-00001",
				"company": "Acme Ltd",
				"customer": "Customer A",
				"lpo_number": " po-2026-0042 ",
			}
		)
		module = "auto_service_management.auto_service_management.doctype.customer_lpo.customer_lpo.frappe"
		with patch(f"{module}.db.exists", return_value="LPO-2026-00002") as exists:
			with self.assertRaises(frappe.ValidationError):
				lpo.validate_unique_lpo_number()
		exists.assert_called_once_with(
			"Customer LPO",
			{
				"company": "Acme Ltd",
				"customer": "Customer A",
				"lpo_number": "PO-2026-0042",
				"name": ["!=", "LPO-2026-00001"],
			},
		)
		self.assertEqual(lpo.lpo_number, "PO-2026-0042")
		self.assertTrue(lpo.lpo_uniqueness_key)

	def test_lpo_preflight_allows_same_number_for_other_customer(self):
		lpo = CustomerLPO(
			{
				"doctype": "Customer LPO",
				"company": "Acme Ltd",
				"customer": "Customer B",
				"lpo_number": "PO-2026-0042",
			}
		)
		module = "auto_service_management.auto_service_management.doctype.customer_lpo.customer_lpo.frappe"
		with patch(f"{module}.db.exists", return_value=None):
			lpo.validate_unique_lpo_number()
		self.assertTrue(lpo.lpo_uniqueness_key)

	def test_legacy_reconciliation_backfills_canonical_values(self):
		module = "auto_service_management.patches.phase33_identifier_invariants.frappe"
		vehicles = [frappe._dict(name="CV-P3-1", vin_chassis_number=" vin-1 ")]
		lpos = [
			frappe._dict(
				name="LPO-P3-1",
				company="Acme Ltd",
				customer="Customer A",
				lpo_number=" po-1 ",
				lpo_uniqueness_key=None,
			)
		]
		with patch(f"{module}.db.exists", return_value=True):
			with patch(f"{module}.get_all", side_effect=[vehicles, lpos]):
				with patch(f"{module}.db.set_value") as set_value:
					_reconcile_customer_vehicles()
					_reconcile_customer_lpos()
		set_value.assert_any_call(
			"Customer Vehicle", "CV-P3-1", "vin_chassis_number", "VIN-1", update_modified=False
		)
		set_value.assert_any_call(
			"Customer LPO",
			"LPO-P3-1",
			{
				"lpo_number": "PO-1",
				"lpo_uniqueness_key": build_lpo_uniqueness_key("Acme Ltd", "Customer A", "PO-1"),
			},
			update_modified=False,
		)

	def test_before_migrate_guard_rejects_normalized_legacy_collision(self):
		module = "auto_service_management.patches.phase33_identifier_invariants.frappe"
		vehicles = [
			frappe._dict(name="CV-P3-1", vin_chassis_number=" vin-1 "),
			frappe._dict(name="CV-P3-2", vin_chassis_number="VIN-1"),
		]
		lpos = []
		with patch(f"{module}.db.exists", return_value=True):
			with patch(f"{module}.db.has_column", return_value=True):
				with patch(f"{module}.get_all", side_effect=[vehicles, lpos]):
					with self.assertRaises(frappe.ValidationError):
						validate_legacy_identifier_safety()

	def test_before_migrate_guard_rejects_scoped_lpo_collision(self):
		module = "auto_service_management.patches.phase33_identifier_invariants.frappe"
		vehicles = []
		lpos = [
			frappe._dict(name="LPO-P3-1", company="Acme Ltd", customer="Customer A", lpo_number=" po-1 "),
			frappe._dict(name="LPO-P3-2", company=" acme ltd ", customer="customer a", lpo_number="PO-1"),
		]
		with patch(f"{module}.db.exists", return_value=True):
			with patch(f"{module}.db.has_column", return_value=True):
				with patch(f"{module}.get_all", side_effect=[vehicles, lpos]):
					with self.assertRaises(frappe.ValidationError):
						validate_legacy_identifier_safety()

	def test_reconciliation_is_idempotent_for_canonical_rows(self):
		module = "auto_service_management.patches.phase33_identifier_invariants.frappe"
		vehicles = [frappe._dict(name="CV-P3-1", vin_chassis_number="VIN-1")]
		key = build_lpo_uniqueness_key("Acme Ltd", "Customer A", "PO-1")
		lpos = [
			frappe._dict(
				name="LPO-P3-1",
				company="Acme Ltd",
				customer="Customer A",
				lpo_number="PO-1",
				lpo_uniqueness_key=key,
			)
		]
		with patch(f"{module}.db.exists", return_value=True):
			with patch(f"{module}.db.has_column", return_value=True):
				with patch(f"{module}.get_all", side_effect=[vehicles, lpos, vehicles, lpos]):
					with patch(f"{module}.db.set_value") as set_value:
						_reconcile_customer_vehicles()
						_reconcile_customer_lpos()
						_reconcile_customer_vehicles()
						_reconcile_customer_lpos()
		set_value.assert_not_called()

	def test_before_migrate_guard_is_registered(self):
		from auto_service_management import hooks

		self.assertIn(
			"auto_service_management.patches.phase33_identifier_invariants.validate_legacy_identifier_safety",
			hooks.before_migrate,
		)


class TestP3DatabaseGuards(IntegrationTestCase):
	def test_identifier_fields_are_database_unique_and_nullable(self):
		vehicle_meta = frappe.get_meta("Customer Vehicle")
		vin_field = vehicle_meta.get_field("vin_chassis_number")
		self.assertTrue(vin_field.unique)
		self.assertFalse(vin_field.reqd)

		lpo_meta = frappe.get_meta("Customer LPO")
		key_field = lpo_meta.get_field("lpo_uniqueness_key")
		self.assertTrue(key_field.unique)
		self.assertFalse(key_field.reqd)

	def test_customer_vehicle_duplicate_vin_is_rejected_after_preflight_bypass(self):
		vehicle = CustomerVehicle(
			{
				"doctype": "Customer Vehicle",
				"name": "CV-P3-EXISTING",
				"vin_chassis_number": "P3-RACE-VIN",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			vehicle.show_unique_validation_message(Exception("Duplicate entry for key 'vin_chassis_number'"))

	def test_multiple_blank_vins_are_allowed_by_nullable_unique_field(self):
		customer = frappe.db.get_value("Customer", {}, "name")
		if not customer:
			self.skipTest("No Customer fixture is available")
		suffix = frappe.generate_hash(length=8).upper()
		vehicles = []
		try:
			for index in (1, 2):
				vehicles.append(
					frappe.get_doc(
						{
							"doctype": "Customer Vehicle",
							"customer": customer,
							"registration_number": f"P3-BLANK-{suffix}-{index}",
							"vin_chassis_number": None,
						}
					).insert(ignore_permissions=True)
				)
			self.assertIsNone(vehicles[0].vin_chassis_number)
			self.assertIsNone(vehicles[1].vin_chassis_number)
		finally:
			for vehicle in vehicles:
				frappe.delete_doc("Customer Vehicle", vehicle.name, ignore_permissions=True)

	def test_database_unique_guard_runs_when_preflight_is_bypassed(self):
		customer = frappe.db.get_value("Customer", {}, "name")
		if not customer:
			self.skipTest("No Customer fixture is available")
		suffix = frappe.generate_hash(length=8).upper()
		first = frappe.get_doc(
			{
				"doctype": "Customer Vehicle",
				"customer": customer,
				"registration_number": f"P3-RACE-{suffix}-1",
				"vin_chassis_number": f"P3-RACE-VIN-{suffix}",
			}
		).insert(ignore_permissions=True)
		try:
			second = frappe.get_doc(
				{
					"doctype": "Customer Vehicle",
					"customer": customer,
					"registration_number": f"P3-RACE-{suffix}-2",
					"vin_chassis_number": f"P3-RACE-VIN-{suffix}",
				}
			)
			second.flags.ignore_validate = True
			with self.assertRaises(frappe.ValidationError):
				second.insert(ignore_permissions=True)
		finally:
			frappe.delete_doc("Customer Vehicle", first.name, ignore_permissions=True)

	def _new_lpo(self, *, lpo_number, uniqueness_key=None):
		company = frappe.db.get_value("Company", {}, "name")
		customer = frappe.db.get_value("Customer", {}, "name")
		currency = frappe.db.get_value("Company", company, "default_currency")
		if not company or not customer or not currency:
			self.skipTest("Company, Customer, and Currency fixtures are required")
		return frappe.get_doc(
			{
				"doctype": "Customer LPO",
				"company": company,
				"customer": customer,
				"lpo_number": lpo_number,
				"lpo_uniqueness_key": uniqueness_key,
				"issue_date": "2026-08-01",
				"expiry_date": "2026-12-31",
				"currency": currency,
				"ceiling_basis": "Tax Inclusive",
				"authorized_amount": 1000,
			}
		)

	def test_multiple_blank_lpo_keys_are_allowed_by_nullable_unique_field(self):
		suffix = frappe.generate_hash(length=8).upper()
		lpos = []
		try:
			for index in (1, 2):
				lpo = self._new_lpo(lpo_number=f"P3-BLANK-{suffix}-{index}")
				lpo.flags.ignore_validate = True
				lpo.insert(ignore_permissions=True, ignore_mandatory=True)
				lpos.append(lpo)
			self.assertIsNone(lpos[0].lpo_uniqueness_key)
			self.assertIsNone(lpos[1].lpo_uniqueness_key)
		finally:
			for lpo in lpos:
				frappe.delete_doc("Customer LPO", lpo.name, ignore_permissions=True)

	def test_database_lpo_unique_guard_runs_when_preflight_is_bypassed(self):
		suffix = frappe.generate_hash(length=8).upper()
		lpo_number = f"P3-RACE-LPO-{suffix}"
		company = frappe.db.get_value("Company", {}, "name")
		customer = frappe.db.get_value("Customer", {}, "name")
		key = build_lpo_uniqueness_key(company, customer, lpo_number)
		first = self._new_lpo(lpo_number=lpo_number, uniqueness_key=key)
		first.flags.ignore_validate = True
		first.insert(ignore_permissions=True, ignore_mandatory=True)
		try:
			second = self._new_lpo(lpo_number=lpo_number, uniqueness_key=key)
			second.flags.ignore_validate = True
			with self.assertRaises(frappe.ValidationError):
				second.insert(ignore_permissions=True, ignore_mandatory=True)
		finally:
			frappe.delete_doc("Customer LPO", first.name, ignore_permissions=True)
