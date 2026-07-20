from __future__ import annotations

import frappe

WORKFLOW_NAME = "Repair Job Workflow"
DOCUMENT_TYPE = "Repair Job"
WORKFLOW_STATE_FIELD = "workflow_state"

WORKFLOW_STATES = (
	("Draft", "Service Advisor", "Info"),
	("Assessment", "Service Advisor", "Info"),
	("Awaiting Approval", "Service Advisor", "Warning"),
	("In Repair", "Workshop Manager", "Primary"),
	("Quality Check", "Workshop Manager", "Warning"),
	("Billing", "Accounts Manager", "Info"),
	("Ready for Release", "Workshop Manager", "Success"),
	("Closed", "Workshop Manager", "Success"),
	("Cancelled", "Workshop Manager", "Danger"),
)

WORKFLOW_TRANSITIONS = (
	("Draft", "Check In", "Assessment", "Service Advisor", None),
	("Assessment", "Request Approval", "Awaiting Approval", "Service Advisor", None),
	("Assessment", "Complete Diagnosis", "Billing", "Service Advisor", "not doc.repair_job_services"),
	("Awaiting Approval", "Approve", "In Repair", "Workshop Manager", None),
	("Awaiting Approval", "Cancel", "Cancelled", "Workshop Manager", None),
	("In Repair", "Send to QC", "Quality Check", "Workshop Manager", None),
	("Quality Check", "Return to Repair", "In Repair", "Workshop Manager", None),
	("Quality Check", "Pass QC", "Billing", "Workshop Manager", None),
	("Billing", "Mark Ready for Release", "Ready for Release", "Accounts Manager", "doc.payment_status == 'Paid'"),
	("Billing", "Reopen Approval", "Awaiting Approval", "Service Advisor", None),
	("Ready for Release", "Reopen Billing", "Billing", "Accounts Manager", None),
	("Ready for Release", "Close Job", "Closed", "Security Gate Officer", "doc.gate_pass and frappe.db.get_value('Gate Pass', doc.gate_pass, 'status') == 'Used'"),
)


def ensure_repair_job_workflow():
	"""Compatibility hook: keep the legacy Workflow record inactive.

	Repair Job transitions belong to the controller and documentary evidence.
	The old native workflow is retained for one release so existing
	``workflow_state`` data remains readable, but it must not be executable.
	"""
	deactivate_repair_job_workflow()


def deactivate_repair_job_workflow():
	if not frappe.db.exists("Workflow", WORKFLOW_NAME):
		return
	if frappe.db.get_value("Workflow", WORKFLOW_NAME, "is_active"):
		frappe.db.set_value("Workflow", WORKFLOW_NAME, "is_active", 0, update_modified=False)


def _ensure_workflow_states():
	for state, _allow_edit, _style in WORKFLOW_STATES:
		_upsert_simple_doc(
			"Workflow State",
			"workflow_state_name",
			state,
			{
				"icon": "flag",
				"style": _style,
			},
		)


def _ensure_workflow_actions():
	actions = {action for _state, action, _next_state, _allowed, _condition in WORKFLOW_TRANSITIONS}
	for action in actions:
		_upsert_simple_doc("Workflow Action Master", "workflow_action_name", action, {})


def _upsert_simple_doc(doctype: str, key_field: str, key_value: str, values: dict):
	if frappe.db.exists(doctype, key_value):
		doc = frappe.get_doc(doctype, key_value)
		changed = False
		for fieldname, value in values.items():
			if getattr(doc, fieldname, None) != value:
				setattr(doc, fieldname, value)
				changed = True
		if changed:
			doc.save(ignore_permissions=True)
		return doc
	doc = frappe.get_doc({"doctype": doctype, key_field: key_value, **values})
	doc.insert(ignore_permissions=True)
	return doc


def _doc_status(state: str) -> int:
	if state == "Closed":
		return 1
	if state == "Cancelled":
		return 2
	return 0
