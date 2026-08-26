from __future__ import annotations

import unittest
from unittest.mock import patch

from auto_service_management.patches.phase16_backfill_invoice_payment_summaries import (
	_backfill_invoice_payment_summaries,
)


class FakeDB:
	def __init__(self, tables=True):
		self.tables = tables

	def table_exists(self, doctype):
		return self.tables


class FakeFrappe:
	def __init__(self, jobs, tables=True):
		self.jobs = jobs
		self.db = FakeDB(tables=tables)

	def get_all(self, doctype, **kwargs):
		if doctype == "Repair Job" and kwargs.get("pluck") == "name":
			return list(self.jobs)
		return []


class TestPhase25InvoicePaymentBackfill(unittest.TestCase):
	def test_backfill_replays_compatibility_sync_for_each_job(self):
		fake_frappe = FakeFrappe(["RJ-1", "RJ-2"])
		calls = []

		with (
			patch(
				"auto_service_management.patches.phase16_backfill_invoice_payment_summaries.frappe",
				fake_frappe,
			),
			patch(
				"auto_service_management.patches.phase16_backfill_invoice_payment_summaries.sync_repair_job_related_tables",
				side_effect=lambda repair_job_name: calls.append(repair_job_name),
			),
		):
			_backfill_invoice_payment_summaries()

		self.assertEqual(["RJ-1", "RJ-2"], calls)

	def test_backfill_is_noop_when_repair_job_table_is_missing(self):
		fake_frappe = FakeFrappe(["RJ-1"], tables=False)
		calls = []

		with (
			patch(
				"auto_service_management.patches.phase16_backfill_invoice_payment_summaries.frappe",
				fake_frappe,
			),
			patch(
				"auto_service_management.patches.phase16_backfill_invoice_payment_summaries.sync_repair_job_related_tables",
				side_effect=lambda repair_job_name: calls.append(repair_job_name),
			),
		):
			_backfill_invoice_payment_summaries()

		self.assertEqual([], calls)
