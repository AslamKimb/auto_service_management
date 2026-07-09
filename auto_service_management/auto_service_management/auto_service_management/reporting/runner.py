import frappe
from frappe import _

from auto_service_management.auto_service_management.reporting.registry import REPORT_DEFINITIONS


def run_report(report_name, filters=None):
	definition = REPORT_DEFINITIONS.get(report_name)
	if not definition:
		frappe.throw(_("Unknown report: {0}").format(report_name))

	has_read_permission = frappe.has_permission(definition.permission_doctype, "read")
	has_report_permission = frappe.has_permission(definition.permission_doctype, "report")
	if not (has_read_permission or has_report_permission):
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
			rows.extend(
				_get_rows(
					source_doctype,
					definition,
					source_query_args,
					has_read_permission=has_read_permission,
				)
			)
	else:
		rows = _get_rows(
			definition.source_doctype,
			definition,
			query_args,
			has_read_permission=has_read_permission,
		)

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


def _get_rows(source_doctype, definition, query_args, has_read_permission=False):
	if definition.parent_field:
		return _get_scoped_child_rows(
			source_doctype,
			definition,
			query_args,
			ignore_permissions=not has_read_permission,
		)
	get_rows = frappe.get_list if has_read_permission else frappe.get_all
	return get_rows(source_doctype, **query_args)


def _get_scoped_child_rows(source_doctype, definition, query_args, ignore_permissions=False):
	get_parents = frappe.get_list if not ignore_permissions else frappe.get_all
	allowed_parents = get_parents(definition.permission_doctype, pluck="name", limit_page_length=0)
	if not allowed_parents:
		return []

	query_args["filters"][definition.parent_field] = ["in", allowed_parents]
	return frappe.get_all(source_doctype, **query_args)
