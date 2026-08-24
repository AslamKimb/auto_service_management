from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReportDefinition:
	source_doctype: str | tuple[str, ...]
	columns: tuple[dict, ...]
	fields: tuple[str, ...]
	filters: tuple[str, ...]
	order_by: str
	permission_doctype: str
	base_filters: dict = field(default_factory=dict)
	date_field: str | None = None
	group_by: str | None = None
	parent_field: str | None = None
	permission_parent_doctype: str | None = None


def column(label, fieldname, fieldtype="Data", options=None, width=140):
	value = {
		"label": label,
		"fieldname": fieldname,
		"fieldtype": fieldtype,
		"width": width,
	}
	if options:
		value["options"] = options
	return value
