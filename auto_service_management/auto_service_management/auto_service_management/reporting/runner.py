import frappe
from frappe import _

from auto_service_management.auto_service_management.reporting.registry import REPORT_DEFINITIONS


def run_report(report_name, filters=None):
	definition = REPORT_DEFINITIONS.get(report_name)
	if not definition:
		frappe.throw(_("Unknown report: {0}").format(report_name))

	has_read_permission = frappe.has_permission(definition.permission_doctype, "read")
	has_select_permission = frappe.has_permission(definition.permission_doctype, "select")
	has_report_permission = frappe.has_permission(definition.permission_doctype, "report")
	if not has_report_permission or not (has_read_permission or has_select_permission):
		frappe.throw(_("You are not permitted to read this report."), frappe.PermissionError)

	query_filters = _build_filters(definition, filters or {})
	query_args = {
		"fields": list(definition.fields),
		"filters": query_filters,
		"order_by": definition.order_by,
		"limit_page_length": 0,
	}
	if definition.group_by:
		query_args["group_by"] = definition.group_by

	if isinstance(definition.source_doctype, tuple):
		rows = []
		for source_doctype in definition.source_doctype:
			source_query_args = {
				**query_args,
				"filters": dict(query_args["filters"]),
			}
			rows.extend(_get_rows(source_doctype, definition, source_query_args))
	else:
		rows = _get_rows(definition.source_doctype, definition, query_args)

	return list(definition.columns), rows


def _build_filters(definition, filters):
	query_filters = dict(definition.base_filters)
	for fieldname in definition.filters:
		if filters.get(fieldname) not in (None, ""):
			query_filters[fieldname] = filters[fieldname]

	if definition.date_field:
		from_date = filters.get("from_date")
		to_date = filters.get("to_date")
		if from_date and to_date:
			query_filters[definition.date_field] = ["between", [from_date, to_date]]
		elif from_date:
			query_filters[definition.date_field] = [">=", from_date]
		elif to_date:
			query_filters[definition.date_field] = ["<=", to_date]

	return query_filters


def _get_rows(source_doctype, definition, query_args):
	if definition.permission_parent_doctype:
		return frappe.get_list(
			source_doctype,
			parent_doctype=definition.permission_parent_doctype,
			**query_args,
		)
	return frappe.get_list(source_doctype, **query_args)
