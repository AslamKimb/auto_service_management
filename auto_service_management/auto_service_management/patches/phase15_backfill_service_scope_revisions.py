from __future__ import annotations

import json

import frappe
from frappe.utils import flt

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	EXCLUDED_SERVICE_STATUSES,
	get_repair_job_services,
)


def execute():
	_backfill_service_scope_revisions()


def _backfill_service_scope_revisions():
	if not frappe.db.table_exists("Repair Job"):
		return
	if not frappe.db.table_exists("Customer Authorization"):
		return

	approved_authorizations = frappe.get_all(
		"Customer Authorization",
		filters={"status": "Approved"},
		fields=["name", "repair_job", "scope_revision", "scope_total_amount", "approved_amount"],
		order_by="creation asc, name asc",
		limit_page_length=0,
	)
	approvals_by_job = {}
	orphaned_approvals = []
	for authorization in approved_authorizations:
		if not authorization.repair_job or not frappe.db.exists("Repair Job", authorization.repair_job):
			orphaned_approvals.append(
				{
					"customer_authorization": authorization.name,
					"repair_job": authorization.repair_job,
					"status": "Approved",
					"reason": "Approved authorization is not linked to an existing Repair Job.",
				}
			)
			continue
		approvals_by_job.setdefault(authorization.repair_job, []).append(authorization)

	exceptions = list(orphaned_approvals)
	for repair_job_name in frappe.get_all("Repair Job", pluck="name", order_by="creation asc, name asc", limit_page_length=0):
		scope_revision, scope_total_amount = _submitted_service_scope(repair_job_name)
		frappe.db.set_value(
			"Repair Job",
			repair_job_name,
			{
				"scope_revision": scope_revision,
				"total_amount": scope_total_amount,
			},
			update_modified=False,
		)

		job_authorizations = approvals_by_job.get(repair_job_name, [])
		if not job_authorizations and (scope_revision or scope_total_amount):
			exceptions.append(
				{
					"repair_job": repair_job_name,
					"status": "Approved",
					"reason": "Submitted service scope has no approved Customer Authorization snapshot.",
				}
			)
			continue

		for authorization in job_authorizations:
			if int(authorization.scope_revision or 0) != scope_revision or flt(authorization.scope_total_amount) != scope_total_amount:
				exceptions.append(
					{
						"repair_job": repair_job_name,
						"customer_authorization": authorization.name,
						"status": authorization.status,
						"old_scope_revision": int(authorization.scope_revision or 0),
						"old_scope_total_amount": flt(authorization.scope_total_amount),
						"scope_revision": scope_revision,
						"scope_total_amount": scope_total_amount,
						"reason": "Approved authorization scope snapshot was stale and has been refreshed.",
					}
				)
			frappe.db.set_value(
				"Customer Authorization",
				authorization.name,
				{
					"scope_revision": scope_revision,
					"scope_total_amount": scope_total_amount,
				},
				update_modified=False,
			)

	if exceptions:
		frappe.logger("auto_service_management").warning(
			"RWF-024 service scope exceptions: %s",
			json.dumps(exceptions, sort_keys=True),
		)


def _submitted_service_scope(repair_job_name: str) -> tuple[int, float]:
	revision = 0
	total_amount = 0.0
	for service in get_repair_job_services(repair_job_name):
		if service.status in EXCLUDED_SERVICE_STATUSES:
			continue
		revision += 1
		total_amount += flt(service.total_amount)
	return revision, total_amount
