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
	_ensure_workflow_states()
	_ensure_workflow_actions()
	workflow = frappe.get_doc({"doctype": "Workflow", "workflow_name": WORKFLOW_NAME})
	if frappe.db.exists("Workflow", WORKFLOW_NAME):
		workflow = frappe.get_doc("Workflow", WORKFLOW_NAME)

	workflow.document_type = DOCUMENT_TYPE
	workflow.is_active = 1
	workflow.override_status = 1
	workflow.send_email_alert = 0
	workflow.enable_action_confirmation = 0
	workflow.workflow_state_field = WORKFLOW_STATE_FIELD
	workflow.set(
		"states",
		[
			{
				"state": state,
				"doc_status": _doc_status(state),
				"allow_edit": allow_edit,
				"style": style,
			}
			for state, allow_edit, style in WORKFLOW_STATES
		],
	)
	workflow.set(
		"transitions",
		[
			{
				"state": state,
				"action": action,
				"next_state": next_state,
				"allowed": allowed,
				"condition": condition,
				"allow_self_approval": 1 if action == "Check In" else 0,
			}
			for state, action, next_state, allowed, condition in WORKFLOW_TRANSITIONS
		],
	)
	if frappe.db.exists("Workflow", WORKFLOW_NAME):
		workflow.save(ignore_permissions=True)
	else:
		workflow.insert(ignore_permissions=True)


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
