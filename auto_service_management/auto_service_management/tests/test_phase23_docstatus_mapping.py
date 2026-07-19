# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest

from auto_service_management.patches.phase14_prepare_service_authorization_docstatus import (
	AUTHORIZATION_DOCSTATUS_MAP,
	SERVICE_DOCSTATUS_MAP,
	_apply_docstatus_map,
)


class TestPhase23DocstatusMapping(unittest.TestCase):
	def test_service_docstatus_map_updates_matching_rows_and_logs_notes(self):
		rows = [
			SimpleNamespace(name="RJS-1", status="Draft", docstatus=2),
			SimpleNamespace(name="RJS-2", status="Rejected", docstatus=0),
			SimpleNamespace(name="RJS-3", status="Unknown", docstatus=0),
		]
		fake_logger = SimpleNamespace(warning=Mock())
		set_value = Mock()
		fake_frappe = SimpleNamespace(
			db=SimpleNamespace(
				table_exists=lambda doctype: doctype == "Repair Job Service",
				set_value=set_value,
			),
			get_all=lambda *args, **kwargs: rows,
			logger=lambda name: fake_logger,
		)

		with patch("auto_service_management.patches.phase14_prepare_service_authorization_docstatus.frappe", fake_frappe):
			_apply_docstatus_map("Repair Job Service", "status", SERVICE_DOCSTATUS_MAP, legacy_note_label="service")

		set_value.assert_has_calls(
			[
				unittest.mock.call("Repair Job Service", "RJS-1", "docstatus", 0, update_modified=False),
				unittest.mock.call("Repair Job Service", "RJS-2", "docstatus", 2, update_modified=False),
			]
		)
		self.assertEqual(fake_logger.warning.call_count, 1)

	def test_authorization_docstatus_map_updates_matching_rows(self):
		rows = [
			SimpleNamespace(name="CA-1", status="Pending", docstatus=1),
			SimpleNamespace(name="CA-2", status="Approved", docstatus=0),
			SimpleNamespace(name="CA-3", status="Rejected", docstatus=0),
		]
		set_value = Mock()
		fake_frappe = SimpleNamespace(
			db=SimpleNamespace(
				table_exists=lambda doctype: doctype == "Customer Authorization",
				set_value=set_value,
			),
			get_all=lambda *args, **kwargs: rows,
			logger=lambda name: SimpleNamespace(warning=Mock()),
		)

		with patch("auto_service_management.patches.phase14_prepare_service_authorization_docstatus.frappe", fake_frappe):
			_apply_docstatus_map(
				"Customer Authorization",
				"status",
				AUTHORIZATION_DOCSTATUS_MAP,
				legacy_note_label="authorization",
			)

		set_value.assert_has_calls(
			[
				unittest.mock.call("Customer Authorization", "CA-1", "docstatus", 0, update_modified=False),
				unittest.mock.call("Customer Authorization", "CA-2", "docstatus", 1, update_modified=False),
				unittest.mock.call("Customer Authorization", "CA-3", "docstatus", 2, update_modified=False),
			]
		)

	def test_missing_table_is_noop(self):
		fake_frappe = SimpleNamespace(db=SimpleNamespace(table_exists=lambda doctype: False))
		with patch("auto_service_management.patches.phase14_prepare_service_authorization_docstatus.frappe", fake_frappe):
			_apply_docstatus_map("Repair Job Service", "status", SERVICE_DOCSTATUS_MAP, legacy_note_label="service")
