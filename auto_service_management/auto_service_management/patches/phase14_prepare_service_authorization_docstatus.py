from __future__ import annotations

import json

import frappe

SERVICE_DOCSTATUS_MAP = {
	"Draft": 0,
	"Pending Approval": 0,
	"Approved": 1,
	"In Progress": 1,
	"Completed": 1,
	"Rejected": 2,
	"Deferred": 2,
	"Cancelled": 2,
}

AUTHORIZATION_DOCSTATUS_MAP = {
	"Pending": 0,
	"Expired": 0,
	"Approved": 1,
	"Rejected": 2,
}


def execute():
	_prepare_authorization_docstatus()


def _prepare_service_docstatus():
	_apply_docstatus_map(
		"Repair Job Service",
		"status",
		SERVICE_DOCSTATUS_MAP,
		legacy_note_label="service",
	)


def _prepare_authorization_docstatus():
	_apply_docstatus_map(
		"Customer Authorization",
		"status",
		AUTHORIZATION_DOCSTATUS_MAP,
		legacy_note_label="authorization",
	)


def _apply_docstatus_map(doctype: str, status_field: str, mapping: dict[str, int], legacy_note_label: str):
	if not frappe.db.table_exists(doctype):
		return

	notes = []
	for row in frappe.get_all(
		doctype,
		fields=["name", status_field, "docstatus"],
		order_by="creation asc, name asc",
		limit_page_length=0,
	):
		status_value = _row_value(row, status_field)
		target_docstatus = mapping.get(status_value)
		if target_docstatus is None:
			continue
		if _row_value(row, "docstatus") != target_docstatus:
			frappe.db.set_value(
				doctype, _row_value(row, "name"), "docstatus", target_docstatus, update_modified=False
			)
		if status_value in {"Rejected", "Deferred", "Cancelled", "Expired"}:
			notes.append(
				{
					"doctype": doctype,
					"name": _row_value(row, "name"),
					"status": status_value,
					"docstatus": target_docstatus,
					"note": f"Legacy {legacy_note_label} cancellation/expiry status has no stored reason text.",
				}
			)

	if notes:
		frappe.logger("auto_service_management").warning(
			"RWF-023 %s docstatus notes: %s",
			doctype,
			json.dumps(notes, sort_keys=True),
		)


def _row_value(row, fieldname):
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)
