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
			"Under Diagnosis",
			"Diagnosed",
			"Awaiting Authorization",
			"Authorized",
			"In Progress",
			"QC Hold",
			"Ready for Release",
			"Released",
			"Closed",
			"Cancelled",
		]
		for state in expected_states:
			self.assertIn(state, VALID_TRANSITIONS, f"Missing transition rules for {state}")

	def test_draft_to_checked_in_allowed(self):
		self.assertIn("Checked In", VALID_TRANSITIONS["Draft"])

	def test_draft_to_in_progress_blocked(self):
		self.assertNotIn("In Progress", VALID_TRANSITIONS["Draft"])

	def test_closed_is_terminal(self):
		self.assertEqual(VALID_TRANSITIONS["Closed"], [])

	def test_cancelled_is_terminal(self):
		self.assertEqual(VALID_TRANSITIONS["Cancelled"], [])

	def test_qc_hold_can_resume_or_release(self):
		self.assertIn("In Progress", VALID_TRANSITIONS["QC Hold"])
		self.assertIn("Ready for Release", VALID_TRANSITIONS["QC Hold"])

	def test_released_must_close(self):
		self.assertEqual(VALID_TRANSITIONS["Released"], ["Closed"])

	def test_full_happy_path(self):
		"""Verify the complete lifecycle from Draft to Closed."""
		path = [
			"Draft",
			"Checked In",
			"Under Diagnosis",
			"Diagnosed",
			"Awaiting Authorization",
			"Authorized",
			"In Progress",
			"QC Hold",
			"In Progress",
			"QC Hold",
			"Ready for Release",
			"Released",
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
			"Under Diagnosis",
			"Diagnosed",
			"Awaiting Authorization",
			"Authorized",
			"In Progress",
			"QC Hold",
			"Ready for Release",
		]
		for state in cancellable:
			self.assertIn(
				"Cancelled",
				VALID_TRANSITIONS[state],
				f"Cancellation from {state} should be allowed",
			)
