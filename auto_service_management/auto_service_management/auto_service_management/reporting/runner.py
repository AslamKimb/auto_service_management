import frappe
from frappe import _

from auto_service_management.auto_service_management.reporting.registry import REPORT_DEFINITIONS

REPORT_PAGE_SIZE = 500


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
	_build_permission_scope_filters(definition, query_filters)
	query_args = {
		"fields": list(definition.fields),
		"filters": query_filters,
		"order_by": definition.order_by,
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


def _build_permission_scope_filters(definition, query_filters):
	"""Restrict linked rows to records the user may read on the business DocType.

	Frappe's ``parent_doctype`` argument can describe only the immediate parent
	of a child table. Nested component rows are children of ``Repair Job
	Service`` but their business permission scope is ``Repair Job``. Resolve
	the permitted Repair Job names first, then apply that scope to the child
	query without bypassing permissions.
	"""
	if not definition.parent_field:
		return {}

	if definition.child_parent_doctype == definition.permission_doctype:
		return {}

	if definition.source_doctype == definition.permission_doctype:
		return {}

	allowed_rows = frappe.get_list(
		definition.permission_doctype,
		fields=["name"],
		limit=REPORT_PAGE_SIZE,
		limit_start=0,
		order_by="creation asc, name asc",
	)
	allowed_names = [row["name"] for row in allowed_rows]
	permission_offset = len(allowed_rows)
	while len(allowed_rows) == REPORT_PAGE_SIZE:
		allowed_rows = frappe.get_list(
			definition.permission_doctype,
			fields=["name"],
			limit=REPORT_PAGE_SIZE,
			limit_start=permission_offset,
			order_by="creation asc, name asc",
		)
		allowed_names.extend(row["name"] for row in allowed_rows)
		permission_offset += len(allowed_rows)
	existing_filter = query_filters.get(definition.parent_field)
	if not allowed_names:
		query_filters[definition.parent_field] = ["in", ["__no_permission__"]]
		return

	if isinstance(existing_filter, str):
		query_filters[definition.parent_field] = (
			existing_filter if existing_filter in allowed_names else ["in", ["__no_permission__"]]
		)
	elif (
		isinstance(existing_filter, list)
		and len(existing_filter) == 2
		and existing_filter[0] == "in"
		and isinstance(existing_filter[1], (list, tuple, set))
	):
		query_filters[definition.parent_field] = [
			"in",
			[name for name in existing_filter[1] if name in allowed_names],
		]
	else:
		query_filters[definition.parent_field] = ["in", allowed_names]


def _get_rows(source_doctype, definition, query_args):
	rows = []
	offset = 0
	while True:
		page_args = {
			**query_args,
			"limit": REPORT_PAGE_SIZE,
			"limit_start": offset,
		}
		if definition.child_parent_doctype:
			page_args["filters"] = _build_child_filter_list(
				source_doctype,
				page_args.get("filters", {}),
			)
			page_args["order_by"] = _build_child_order_by(
				source_doctype,
				page_args.get("order_by"),
			)
			page = frappe.get_list(
				source_doctype,
				parent_doctype=definition.child_parent_doctype,
				**page_args,
			)
		else:
			page = frappe.get_list(source_doctype, **page_args)
		rows.extend(page)
		if len(page) < REPORT_PAGE_SIZE:
			_sort_child_rows(rows, definition)
			return rows
		offset += len(page)


def _build_child_filter_list(source_doctype, filters):
	"""Keep Frappe v16's immediate child parent context for every filter field."""
	if not isinstance(filters, dict):
		return filters

	child_filters = []
	for fieldname, condition in filters.items():
		if isinstance(condition, (list, tuple)) and len(condition) == 2:
			operator, value = condition
		else:
			operator, value = "=", condition
		child_filters.append([source_doctype, fieldname, operator, value])
	return child_filters


def _build_child_order_by(source_doctype, order_by):
	"""Use permission-safe storage ordering for v16 child queries."""
	if (
		source_doctype
		in {
			"Repair Job Service Part",
			"Repair Job Service Consumable",
			"Repair Job Service Labour",
		}
		and order_by
		and "repair_job" in order_by
	):
		return "idx asc, name asc"
	return order_by


def _sort_child_rows(rows, definition):
	"""Restore the report's job grouping after permission-safe child paging."""
	if definition.child_parent_doctype and definition.order_by and "repair_job" in definition.order_by:
		rows.sort(key=lambda row: (row.get("repair_job") or "", row.get("idx") or 0))
