from __future__ import annotations

TRACE_CUSTOM_FIELD_NAMES = (
	"Sales Invoice-repair_job",
	"Sales Invoice-fleet_service_campaign",
	"Sales Invoice-customer_lpo",
	"Sales Order-repair_job",
	"Sales Order-repair_job_service",
	"Sales Order-fleet_service_campaign",
	"Sales Order-customer_lpo",
	"Quotation-repair_job",
	"Quotation-repair_job_service",
	"Material Request-repair_job",
	"Timesheet Detail-repair_job",
	"Timesheet Detail-customer_vehicle",
	"Timesheet Detail-repair_job_service",
	"Timesheet Detail-repair_component_doctype",
	"Timesheet Detail-repair_component_row",
	"Timesheet Detail-repair_service_line",
	"Material Request Item-repair_job",
	"Material Request Item-customer_vehicle",
	"Material Request Item-repair_job_service",
	"Material Request Item-repair_component_doctype",
	"Material Request Item-repair_component_row",
	"Material Request Item-repair_service_line",
	"Stock Entry Detail-repair_job",
	"Stock Entry Detail-customer_vehicle",
	"Stock Entry Detail-repair_job_service",
	"Stock Entry Detail-repair_component_doctype",
	"Stock Entry Detail-repair_component_row",
	"Stock Entry Detail-repair_service_line",
	"Sales Invoice Item-repair_job",
	"Sales Invoice Item-customer_vehicle",
	"Sales Invoice Item-repair_job_service",
	"Sales Invoice Item-repair_component_doctype",
	"Sales Invoice Item-repair_component_row",
	"Sales Invoice Item-repair_service_line",
	"Sales Order Item-repair_job",
	"Sales Order Item-customer_vehicle",
	"Sales Order Item-repair_job_service",
	"Sales Order Item-repair_component_doctype",
	"Sales Order Item-repair_component_row",
	"Sales Order Item-repair_service_line",
	"Quotation Item-repair_job",
	"Quotation Item-customer_vehicle",
	"Quotation Item-repair_job_service",
	"Quotation Item-repair_component_doctype",
	"Quotation Item-repair_component_row",
	"Quotation Item-repair_service_line",
)

PARENT_TRACE_FIELDS = {
	"Sales Invoice": [
		{
			"fieldname": "repair_job",
			"label": "Repair Job",
			"fieldtype": "Link",
			"options": "Repair Job",
			"insert_after": "customer",
			"read_only": 1,
			"no_copy": 1,
		},
		{
			"fieldname": "fleet_service_campaign",
			"label": "Fleet Service Campaign",
			"fieldtype": "Link",
			"options": "Fleet Service Campaign",
			"insert_after": "repair_job",
			"read_only": 1,
			"no_copy": 1,
		},
		{
			"fieldname": "customer_lpo",
			"label": "Customer LPO",
			"fieldtype": "Link",
			"options": "Customer LPO",
			"insert_after": "fleet_service_campaign",
			"read_only": 1,
			"no_copy": 1,
		},
	],
	"Sales Order": [
		{
			"fieldname": "repair_job",
			"label": "Repair Job",
			"fieldtype": "Link",
			"options": "Repair Job",
			"insert_after": "customer",
			"read_only": 1,
			"no_copy": 1,
		},
		{
			"fieldname": "repair_job_service",
			"label": "Repair Job Service",
			"fieldtype": "Link",
			"options": "Repair Job Service",
			"insert_after": "repair_job",
			"read_only": 1,
			"no_copy": 1,
		},
		{
			"fieldname": "fleet_service_campaign",
			"label": "Fleet Service Campaign",
			"fieldtype": "Link",
			"options": "Fleet Service Campaign",
			"insert_after": "repair_job_service",
			"read_only": 1,
			"no_copy": 1,
		},
		{
			"fieldname": "customer_lpo",
			"label": "Customer LPO",
			"fieldtype": "Link",
			"options": "Customer LPO",
			"insert_after": "fleet_service_campaign",
			"read_only": 1,
			"no_copy": 1,
		},
	],
	"Material Request": {
		"fieldname": "repair_job",
		"label": "Repair Job",
		"fieldtype": "Link",
		"options": "Repair Job",
		"insert_after": "material_request_type",
		"read_only": 1,
		"no_copy": 1,
	},
	"Quotation": [
		{
			"fieldname": "repair_job",
			"label": "Repair Job",
			"fieldtype": "Link",
			"options": "Repair Job",
			"insert_after": "party_name",
			"read_only": 1,
			"no_copy": 1,
		},
		{
			"fieldname": "repair_job_service",
			"label": "Repair Job Service",
			"fieldtype": "Link",
			"options": "Repair Job Service",
			"insert_after": "repair_job",
			"read_only": 1,
			"no_copy": 1,
		},
	],
}

TRACE_CHILD_DOCTYPES = (
	"Timesheet Detail",
	"Material Request Item",
	"Stock Entry Detail",
	"Sales Invoice Item",
	"Sales Order Item",
	"Quotation Item",
)

TRACE_FIELDS = (
	{
		"fieldname": "repair_job",
		"label": "Repair Job",
		"fieldtype": "Link",
		"options": "Repair Job",
		"read_only": 1,
	},
	{
		"fieldname": "customer_vehicle",
		"label": "Customer Vehicle",
		"fieldtype": "Link",
		"options": "Customer Vehicle",
		"read_only": 1,
	},
	{
		"fieldname": "repair_job_service",
		"label": "Repair Job Service",
		"fieldtype": "Link",
		"options": "Repair Job Service",
		"read_only": 1,
	},
	{
		"fieldname": "repair_component_doctype",
		"label": "Repair Component DocType",
		"fieldtype": "Data",
		"read_only": 1,
	},
	{
		"fieldname": "repair_component_row",
		"label": "Repair Component Row",
		"fieldtype": "Data",
		"read_only": 1,
	},
	{
		"fieldname": "repair_service_line",
		"label": "Legacy Repair Service Line",
		"fieldtype": "Data",
		"read_only": 1,
	},
)


def get_trace_custom_fields():
	custom_fields = {
		doctype: [
			{
				**field,
				"module": "Auto Service Management",
				"insert_after": _get_insert_after(doctype),
				"no_copy": 1,
			}
			for field in TRACE_FIELDS
		]
		for doctype in TRACE_CHILD_DOCTYPES
	}
	for doctype, fields in PARENT_TRACE_FIELDS.items():
		if isinstance(fields, dict):
			fields = [fields]
		custom_fields[doctype] = [{**field, "module": "Auto Service Management"} for field in fields]
	return custom_fields


def ensure_trace_custom_fields():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(get_trace_custom_fields(), update=True)


def _get_insert_after(doctype):
	if doctype == "Timesheet Detail":
		return "activity_type"
	return "item_code"
