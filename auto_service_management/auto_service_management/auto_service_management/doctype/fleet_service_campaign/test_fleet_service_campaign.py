from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.fleet_service_campaign.fleet_service_campaign import (
	FleetServiceCampaign,
	make_repair_job,
)
from auto_service_management.auto_service_management.doctype.repair_job.repair_job import RepairJob


class TestFleetServiceCampaign(UnitTestCase):
	def test_duplicate_repair_job_is_rejected(self):
		campaign = self._campaign("CUST-0001", "RJ-0001", "RJ-0001")
		lookup = (
			"auto_service_management.auto_service_management.doctype."
			"fleet_service_campaign.fleet_service_campaign.frappe.db.get_value"
		)
		with patch(
			lookup,
			return_value=frappe._dict(customer="CUST-0001", fleet_service_campaign=None),
		):
			self.assertRaises(frappe.ValidationError, campaign.validate)

	def test_repair_job_for_another_customer_is_rejected(self):
		campaign = self._campaign("CUST-0001", "RJ-0001")
		lookup = (
			"auto_service_management.auto_service_management.doctype."
			"fleet_service_campaign.fleet_service_campaign.frappe.db.get_value"
		)
		with patch(
			lookup,
			return_value=frappe._dict(customer="CUST-OTHER", fleet_service_campaign=None),
		):
			self.assertRaises(frappe.ValidationError, campaign.validate)

	def test_repair_job_assigned_to_another_campaign_is_rejected(self):
		campaign = self._campaign("CUST-0001", "RJ-0001")
		campaign.name = "FSC-2026-00001"
		lookup = (
			"auto_service_management.auto_service_management.doctype."
			"fleet_service_campaign.fleet_service_campaign.frappe.db.get_value"
		)
		with patch(
			lookup,
			return_value=frappe._dict(
				customer="CUST-0001",
				fleet_service_campaign="FSC-OTHER",
			),
		):
			self.assertRaises(frappe.ValidationError, campaign.validate_job_customers)

	def test_campaign_link_is_synchronized_to_repair_jobs(self):
		campaign = self._campaign("CUST-0001", "RJ-NEW")
		campaign.name = "FSC-2026-00001"
		module = (
			"auto_service_management.auto_service_management.doctype."
			"fleet_service_campaign.fleet_service_campaign.frappe"
		)
		old_job = self._repair_job_doc("RJ-OLD", "FSC-2026-00001")
		new_job = self._repair_job_doc("RJ-NEW", None)
		with (
			patch(f"{module}.get_all", return_value=["RJ-OLD"]),
			patch(f"{module}.get_doc", side_effect=[old_job, new_job]),
		):
			campaign.sync_job_links()

		self.assertIsNone(old_job.fleet_service_campaign)
		self.assertEqual(new_job.fleet_service_campaign, "FSC-2026-00001")
		old_job.save.assert_called_once_with()
		new_job.save.assert_called_once_with()
		self.assertTrue(old_job.flags.skip_fleet_campaign_sync)
		self.assertTrue(new_job.flags.skip_fleet_campaign_sync)

	def test_make_repair_job_returns_unsaved_prefilled_target(self):
		campaign = self._campaign("CUST-0001")
		campaign.name = "FSC-2026-00001"
		campaign.status = "Ongoing"
		campaign.check_permission = MagicMock()
		target = frappe._dict(
			doctype="Repair Job",
			docstatus=0,
			customer=None,
			fleet_service_campaign=None,
		)
		module = (
			"auto_service_management.auto_service_management.doctype."
			"fleet_service_campaign.fleet_service_campaign.frappe"
		)
		with (
			patch(f"{module}.get_doc", return_value=campaign),
			patch(f"{module}.new_doc", return_value=target),
			patch(f"{module}.has_permission") as has_permission,
		):
			mapped = make_repair_job("FSC-2026-00001")

		campaign.check_permission.assert_called_once_with("write")
		has_permission.assert_called_once_with("Repair Job", "create", throw=True)
		self.assertIs(mapped, target)
		self.assertEqual(mapped.customer, "CUST-0001")
		self.assertEqual(mapped.fleet_service_campaign, "FSC-2026-00001")

	def test_make_repair_job_rejects_closed_campaign(self):
		campaign = self._campaign("CUST-0001")
		campaign.name = "FSC-2026-00001"
		campaign.status = "Closed"
		campaign.check_permission = MagicMock()
		module = (
			"auto_service_management.auto_service_management.doctype."
			"fleet_service_campaign.fleet_service_campaign.frappe"
		)
		with (
			patch(f"{module}.get_doc", return_value=campaign),
			patch(f"{module}.new_doc") as new_doc,
			patch(f"{module}.has_permission"),
		):
			self.assertRaises(frappe.ValidationError, make_repair_job, "FSC-2026-00001")

		new_doc.assert_not_called()

	def test_repair_job_sync_appends_campaign_row_once(self):
		job = RepairJob(
			{
				"doctype": "Repair Job",
				"name": "RJ-0001",
				"customer": "CUST-0001",
				"fleet_service_campaign": "FSC-2026-00001",
			}
		)
		campaign = self._campaign("CUST-0001")
		campaign.name = "FSC-2026-00001"
		campaign.save = MagicMock()
		job.get_doc_before_save = MagicMock(return_value=None)
		module = (
			"auto_service_management.auto_service_management.doctype."
			"repair_job.repair_job.frappe"
		)
		with patch(f"{module}.get_doc", return_value=campaign):
			job.sync_fleet_campaign_membership()

		self.assertEqual([row.repair_job for row in campaign.fleet_jobs], ["RJ-0001"])
		self.assertTrue(campaign.flags.skip_job_link_sync)
		campaign.save.assert_called_once_with()

		job.get_doc_before_save = MagicMock(
			return_value=frappe._dict(fleet_service_campaign="FSC-2026-00001")
		)
		campaign.save.reset_mock()
		with patch(f"{module}.get_doc", return_value=campaign):
			job.sync_fleet_campaign_membership()
		campaign.save.assert_not_called()

	def test_repair_job_campaign_validation_rejects_customer_mismatch(self):
		job = RepairJob(
			{
				"doctype": "Repair Job",
				"customer": "CUST-0001",
				"fleet_service_campaign": "FSC-2026-00001",
			}
		)
		job.get_doc_before_save = MagicMock(return_value=None)
		campaign = self._campaign("CUST-OTHER")
		campaign.name = "FSC-2026-00001"
		campaign.status = "Ongoing"
		module = (
			"auto_service_management.auto_service_management.doctype."
			"repair_job.repair_job.frappe"
		)
		with patch(f"{module}.get_doc", return_value=campaign):
			self.assertRaises(frappe.ValidationError, job.validate_fleet_service_campaign)

	def test_repair_job_campaign_validation_rejects_closed_campaign(self):
		job = RepairJob(
			{
				"doctype": "Repair Job",
				"customer": "CUST-0001",
				"fleet_service_campaign": "FSC-2026-00001",
			}
		)
		job.get_doc_before_save = MagicMock(return_value=None)
		campaign = self._campaign("CUST-0001")
		campaign.name = "FSC-2026-00001"
		campaign.status = "Closed"
		campaign.check_permission = MagicMock()
		module = (
			"auto_service_management.auto_service_management.doctype."
			"repair_job.repair_job.frappe"
		)
		with patch(f"{module}.get_doc", return_value=campaign):
			self.assertRaises(frappe.ValidationError, job.validate_fleet_service_campaign)
		campaign.check_permission.assert_called_once_with("write")

	def test_repair_job_sync_moves_between_campaigns(self):
		job = RepairJob(
			{
				"doctype": "Repair Job",
				"name": "RJ-0001",
				"customer": "CUST-0001",
				"fleet_service_campaign": "FSC-NEW",
			}
		)
		job.get_doc_before_save = MagicMock(
			return_value=frappe._dict(fleet_service_campaign="FSC-OLD")
		)
		old_campaign = self._campaign("CUST-0001", "RJ-0001")
		old_campaign.name = "FSC-OLD"
		old_campaign.save = MagicMock()
		old_campaign.check_permission = MagicMock()
		new_campaign = self._campaign("CUST-0001")
		new_campaign.name = "FSC-NEW"
		new_campaign.save = MagicMock()
		new_campaign.check_permission = MagicMock()
		module = (
			"auto_service_management.auto_service_management.doctype."
			"repair_job.repair_job.frappe"
		)
		with patch(f"{module}.get_doc", side_effect=[old_campaign, new_campaign]):
			job.sync_fleet_campaign_membership()

		self.assertEqual(old_campaign.fleet_jobs, [])
		self.assertEqual([row.repair_job for row in new_campaign.fleet_jobs], ["RJ-0001"])
		old_campaign.save.assert_called_once_with()
		new_campaign.save.assert_called_once_with()

	def _campaign(self, customer, *repair_jobs):
		return FleetServiceCampaign(
			{
				"doctype": "Fleet Service Campaign",
				"campaign_name": "Test Fleet Campaign",
				"customer": customer,
				"fleet_jobs": [{"repair_job": repair_job} for repair_job in repair_jobs],
			}
		)

	def _repair_job_doc(self, name, campaign):
		doc = MagicMock(name=name)
		doc.name = name
		doc.fleet_service_campaign = campaign
		doc.flags = frappe._dict()
		return doc
