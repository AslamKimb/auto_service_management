from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.customer_lpo_amendment.customer_lpo_amendment import (
	CustomerLPOAmendment,
)


class TestCustomerLPOAmendment(UnitTestCase):
	def test_amendment_requires_amount_increase_or_later_expiry(self):
		amendment = CustomerLPOAmendment(
			{
				"doctype": "Customer LPO Amendment",
				"customer_lpo": "LPO-2026-00001",
				"external_reference": "AM-001",
				"issue_date": "2026-08-25",
			}
		)
		with patch.object(CustomerLPOAmendment, "validate_lpo_state"):
			with self.assertRaises(frappe.ValidationError):
				amendment.validate()

	def test_amount_increase_must_be_positive(self):
		amendment = self._amendment(amount_increase=-1)
		with patch.object(CustomerLPOAmendment, "validate_lpo_state"):
			with self.assertRaises(frappe.ValidationError):
				amendment.validate()

	def test_valid_amount_increase_passes(self):
		amendment = self._amendment(amount_increase=500)
		with patch.object(CustomerLPOAmendment, "validate_lpo_state"):
			amendment.validate()

	def _amendment(self, amount_increase):
		return CustomerLPOAmendment(
			{
				"doctype": "Customer LPO Amendment",
				"customer_lpo": "LPO-2026-00001",
				"external_reference": "AM-001",
				"issue_date": "2026-08-25",
				"amount_increase": amount_increase,
				"reason": "Additional approved work",
			}
		)
