import frappe
from frappe.tests import IntegrationTestCase

from auto_service_management.auto_service_management.doctype.fleet_service_campaign.fleet_service_campaign import (
	make_repair_job,
)
from auto_service_management.auto_service_management.tests.test_controllers_integration import (
	_create_test_vehicle,
	_get_or_create_customer,
)


class TestFleetServiceCampaignLifecycle(IntegrationTestCase):
	def test_mapped_repair_job_save_and_campaign_removal_stay_synchronized(self):
		customer = _get_or_create_customer()
		vehicle = _create_test_vehicle(customer)
		campaign = frappe.get_doc(
			{
				"doctype": "Fleet Service Campaign",
				"campaign_name": "Lifecycle Campaign",
				"customer": customer,
				"status": "Ongoing",
			}
		).insert(ignore_permissions=True)

		repair_job = make_repair_job(campaign.name)
		repair_job.update(
			{
				"customer_vehicle": vehicle,
				"odometer_in": 84521,
				"customer_concern": "Campaign service",
			}
		)
		repair_job.insert(ignore_permissions=True)

		campaign.reload()
		self.assertEqual([row.repair_job for row in campaign.fleet_jobs], [repair_job.name])
		self.assertEqual(repair_job.fleet_service_campaign, campaign.name)

		campaign.set("fleet_jobs", [])
		campaign.save()
		repair_job.reload()
		self.assertIsNone(repair_job.fleet_service_campaign)
