from __future__ import annotations

import frappe

from auto_service_management.auto_service_management.workflow_compatibility import (
	sync_repair_job_related_tables,
)


def execute():
	_backfill_invoice_payment_summaries()


def _backfill_invoice_payment_summaries():
	if not frappe.db.table_exists("Repair Job"):
		return

	for repair_job_name in frappe.get_all(
		"Repair Job", pluck="name", order_by="creation asc, name asc", limit_page_length=0
	):
		sync_repair_job_related_tables(repair_job_name)
