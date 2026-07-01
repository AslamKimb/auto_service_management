# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from auto_service_management.auto_service_management.doctype.repair_job.repair_job import (
	VALID_TRANSITIONS,
)


class TestRepairJobWorkflow(IntegrationTestCase):
	"""Test the Repair Job status state machine."""

	def test_valid_transitions_exist(self):
		"""All expected states must have defined transitions."""
		expected_states = [
			"Draft",
			"Checked In",
			"Walkaround Inspection",
			"Diagnosis",
			"Estimate Prepared",
			"Waiting for Customer Approval",
			"Approved",
			"In Repair",
			"Quality Check",
			"Ready for Invoice",
			"Invoiced",
			"Gate Pass Issued",
			"Closed",
			"Closed - Diagnosis Only",
			"Cancelled",
		]
		for state in expected_states:
			self.assertIn(state, VALID_TRANSITIONS, f"Missing transition rules for {state}")

	def test_draft_to_checked_in_allowed(self):
		self.assertIn("Checked In", VALID_TRANSITIONS["Draft"])

	def test_draft_to_in_repair_blocked(self):
		self.assertNotIn("In Repair", VALID_TRANSITIONS["Draft"])

	def test_closed_is_terminal(self):
		self.assertEqual(VALID_TRANSITIONS["Closed"], [])

	def test_cancelled_is_terminal(self):
		self.assertEqual(VALID_TRANSITIONS["Cancelled"], [])

	def test_quality_check_can_resume_or_move_to_invoice(self):
		self.assertIn("In Repair", VALID_TRANSITIONS["Quality Check"])
		self.assertIn("Ready for Invoice", VALID_TRANSITIONS["Quality Check"])

	def test_gate_pass_issued_must_close(self):
		self.assertEqual(VALID_TRANSITIONS["Gate Pass Issued"], ["Closed", "Closed - Diagnosis Only"])

	def test_full_happy_path(self):
		"""Verify the complete lifecycle from Draft to Closed."""
		path = [
			"Draft",
			"Checked In",
			"Walkaround Inspection",
			"Diagnosis",
			"Estimate Prepared",
			"Waiting for Customer Approval",
			"Approved",
			"In Repair",
			"Quality Check",
			"In Repair",
			"Quality Check",
			"Ready for Invoice",
			"Invoiced",
			"Gate Pass Issued",
			"Closed",
		]
		for i in range(len(path) - 1):
			self.assertIn(
				path[i + 1],
				VALID_TRANSITIONS[path[i]],
				f"Transition {path[i]} -> {path[i + 1]} should be valid",
			)

	def test_cancellation_from_any_non_terminal(self):
		"""Cancellation should be allowed from most active states."""
		cancellable = [
			"Draft",
			"Checked In",
			"Walkaround Inspection",
			"Diagnosis",
			"Estimate Prepared",
			"Waiting for Customer Approval",
			"Approved",
			"In Repair",
			"Quality Check",
			"Ready for Invoice",
		]
		for state in cancellable:
			self.assertIn(
				"Cancelled",
				VALID_TRANSITIONS[state],
				f"Cancellation from {state} should be allowed",
			)

	def test_diagnosis_only_path_exists(self):
		path = [
			"Draft",
			"Checked In",
			"Walkaround Inspection",
			"Diagnosis",
			"Ready for Invoice",
			"Invoiced",
			"Gate Pass Issued",
			"Closed - Diagnosis Only",
		]
		for i in range(len(path) - 1):
			self.assertIn(path[i + 1], VALID_TRANSITIONS[path[i]])
