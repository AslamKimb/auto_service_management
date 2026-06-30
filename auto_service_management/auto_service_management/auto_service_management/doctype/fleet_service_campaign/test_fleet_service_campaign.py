from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.fleet_service_campaign.fleet_service_campaign import (
	FleetServiceCampaign,
)


class TestFleetServiceCampaign(UnitTestCase):
	def test_duplicate_repair_job_is_rejected(self):
		campaign = self._campaign("CUST-0001", "RJ-0001", "RJ-0001")
		lookup = (
			"auto_service_management.auto_service_management.doctype."
			"fleet_service_campaign.fleet_service_campaign.frappe.db.get_value"
		)
		with patch(lookup, return_value="CUST-0001"):
			self.assertRaises(frappe.ValidationError, campaign.validate)

	def test_repair_job_for_another_customer_is_rejected(self):
		campaign = self._campaign("CUST-0001", "RJ-0001")
		lookup = (
			"auto_service_management.auto_service_management.doctype."
			"fleet_service_campaign.fleet_service_campaign.frappe.db.get_value"
		)
		with patch(lookup, return_value="CUST-OTHER"):
			self.assertRaises(frappe.ValidationError, campaign.validate)

	def test_campaign_link_is_synchronized_to_repair_jobs(self):
		campaign = self._campaign("CUST-0001", "RJ-NEW")
		campaign.name = "FSC-2026-00001"
		module = (
			"auto_service_management.auto_service_management.doctype."
			"fleet_service_campaign.fleet_service_campaign.frappe"
		)
		with (
			patch(f"{module}.get_all", return_value=["RJ-OLD"]),
			patch(f"{module}.db.set_value") as set_value,
		):
			campaign.sync_job_links()

		set_value.assert_any_call("Repair Job", "RJ-OLD", "fleet_service_campaign", None)
		set_value.assert_any_call(
			"Repair Job",
			"RJ-NEW",
			"fleet_service_campaign",
			"FSC-2026-00001",
		)

	def _campaign(self, customer, *repair_jobs):
		return FleetServiceCampaign(
			{
				"doctype": "Fleet Service Campaign",
				"campaign_name": "Test Fleet Campaign",
				"customer": customer,
				"fleet_jobs": [{"repair_job": repair_job} for repair_job in repair_jobs],
			}
		)
