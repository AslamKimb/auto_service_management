from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from auto_service_management.auto_service_management.doctype.customer_authorization.customer_authorization import (
	CustomerAuthorization,
)
from auto_service_management.auto_service_management.doctype.customer_authorization import (
	customer_authorization as customer_authorization_module,
)
from auto_service_management.auto_service_management import workflow_compatibility as workflow_compatibility_module


class TestPhase31AuthorizationContract(unittest.TestCase):
	def test_validate_amount_blocks_partial_scope_authorizations(self):
		auth = CustomerAuthorization.__new__(CustomerAuthorization)
		auth.repair_job = "RJ-1"
		auth.approved_amount = 50

		fake_frappe = SimpleNamespace(
			db=SimpleNamespace(get_value=lambda doctype, name, fieldname: 100),
			throw=lambda message: (_ for _ in ()).throw(Exception(message)),
		)

		with patch.object(customer_authorization_module, "frappe", fake_frappe), self.assertRaises(Exception) as ctx:
			CustomerAuthorization.validate_amount(auth)

		self.assertIn("full Repair Job amount", str(ctx.exception))

	def test_check_expiry_marks_expired_authorizations(self):
		auth = CustomerAuthorization.__new__(CustomerAuthorization)
		auth.expiry_date = date.today() - timedelta(days=1)
		auth.docstatus = 1

		fake_frappe = SimpleNamespace(
			utils=SimpleNamespace(today=lambda: date.today()),
			throw=lambda message: (_ for _ in ()).throw(Exception(message)),
		)

		with patch.object(customer_authorization_module, "frappe", fake_frappe), self.assertRaises(Exception) as ctx:
			CustomerAuthorization.check_expiry(auth)

		self.assertIn("expired", str(ctx.exception).lower())

	def test_reject_requires_reason_in_notes(self):
		auth = CustomerAuthorization.__new__(CustomerAuthorization)
		auth.docstatus = 1
		auth.authorization_notes = ""
		auth._require_write_permission = lambda: None

		fake_frappe = SimpleNamespace(throw=lambda message: (_ for _ in ()).throw(Exception(message)))

		with patch.object(customer_authorization_module, "frappe", fake_frappe), self.assertRaises(Exception) as ctx:
			CustomerAuthorization.reject(auth)

		self.assertIn("rejection reason", str(ctx.exception))

	def test_scope_change_expires_stale_authorizations(self):
		updates = []

		class _FakeDB:
			def exists(self, doctype, name):
				return True

			def get_value(self, doctype, name, fieldname):
				return 2 if fieldname == "scope_revision" else 100

			def set_value(self, doctype, name, fieldname, value, update_modified=False):
				updates.append((doctype, name, fieldname, value, update_modified))

		fake_frappe = SimpleNamespace(
			db=_FakeDB(),
			get_all=lambda doctype, **kwargs: [
				SimpleNamespace(name="AUTH-1", scope_revision=2, scope_total_amount=100),
				SimpleNamespace(name="AUTH-2", scope_revision=1, scope_total_amount=80),
			],
		)

		with patch.object(workflow_compatibility_module, "frappe", fake_frappe):
			workflow_compatibility_module.invalidate_repair_job_authorizations("RJ-1")

		self.assertEqual([("Customer Authorization", "AUTH-2", "docstatus", 2, False)], updates)
