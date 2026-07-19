import frappe

WORKSPACE_DASHBOARD_CHARTS = (
	"Repair Job Status Breakdown",
	"Repair Job Intake Trend",
	"Closed Repair Revenue Trend",
	"Gate Pass Status Breakdown",
	"Quality Check Status Breakdown",
)

WORKSPACE_OPERATIONAL_NUMBER_CARDS = (
	"Open Repair Jobs",
	"Pending Authorizations",
	"Pending Quality Checks",
	"Issued Gate Passes",
	"Ongoing Fleet Campaigns",
)

WORKSPACE_DOC_TYPE_COVERAGE = {
	"Auto Service Settings": "Auto Service Settings Configured",
	"Customer Vehicle": "Customer Vehicles",
	"Workshop Bay": "Workshop Bays",
	"Repair Job": "Repair Jobs",
	"Repair Job Service": "Repair Job Services",
	"Repair Job Service Part": "Repair Job Service Parts",
	"Repair Job Service Labour": "Repair Job Service Labour",
	"Repair Job Service Consumable": "Repair Job Service Consumables",
	"Repair Job Override": "Repair Job Overrides",
	"Repair Job Log": "Repair Job Logs",
	"Walkaround Inspection": "Walkaround Inspections",
	"Vehicle Damage Mark": "Vehicle Damage Marks",
	"Diagnosis Report": "Diagnosis Reports",
	"Customer Authorization": "Customer Authorizations",
	"Quality Check": "Quality Checks",
	"Gate Pass": "Gate Passes",
	"Service History": "Service History Records",
	"Fleet Service Campaign": "Fleet Service Campaigns",
	"Fleet Service Campaign Job": "Fleet Campaign Jobs",
}

WORKSPACE_COVERAGE_NUMBER_CARDS = tuple(WORKSPACE_DOC_TYPE_COVERAGE.values())

CHILD_COMPONENT_CARD_CONFIG = {
	"Repair Job Service Parts": {
		"child_doctype": "Repair Job Service Part",
		"parent_doctype": "Repair Job Service",
		"route": ["List", "Repair Job Service", "List"],
	},
	"Repair Job Service Labour": {
		"child_doctype": "Repair Job Service Labour",
		"parent_doctype": "Repair Job Service",
		"route": ["List", "Repair Job Service", "List"],
	},
	"Repair Job Service Consumables": {
		"child_doctype": "Repair Job Service Consumable",
		"parent_doctype": "Repair Job Service",
		"route": ["List", "Repair Job Service", "List"],
	},
}

WORKSPACE_LINK_CARDS = (
	"Intake & Setup",
	"Workshop Execution",
	"QC, Release & History",
	"Fleet & Exceptions",
	"Reports",
)

WORKSPACE_REPORT_LINKS = (
	"Open Repair Jobs",
	"Daily Workshop Load",
	"Jobs by Status",
	"Jobs Waiting for Parts",
	"Technician Productivity",
	"Labour Hours by Technician",
	"Parts Used by Repair Job",
	"Vehicle Service History",
	"Delayed Jobs",
	"Repair Revenue by Period",
	"Gate Pass Register",
	"Corporate Credit Releases",
	"Discount and Price Change Audit",
)

WORKSPACE_SIDEBAR_HOME = {
	"label": "Home",
	"link_type": "Workspace",
	"link_to": "Workshop Management",
}

WORKSPACE_SIDEBAR_SECTIONS = {
	"Intake & Setup": (
		{"label": "Auto Service Settings", "link_type": "DocType", "link_to": "Auto Service Settings"},
		{"label": "Customer Vehicle", "link_type": "DocType", "link_to": "Customer Vehicle"},
		{"label": "Workshop Bay", "link_type": "DocType", "link_to": "Workshop Bay"},
		{"label": "Repair Job", "link_type": "DocType", "link_to": "Repair Job"},
		{
			"label": "Walkaround Inspection",
			"link_type": "DocType",
			"link_to": "Walkaround Inspection",
		},
		{"label": "Diagnosis Report", "link_type": "DocType", "link_to": "Diagnosis Report"},
		{
			"label": "Customer Authorization",
			"link_type": "DocType",
			"link_to": "Customer Authorization",
		},
	),
	"Workshop Execution": (
		{"label": "Repair Job", "link_type": "DocType", "link_to": "Repair Job"},
		{"label": "Repair Job Service", "link_type": "DocType", "link_to": "Repair Job Service"},
		{
			"label": "Repair Queue",
			"link_type": "DocType",
			"link_to": "Repair Job",
			"route_options": {
				"job_status": ["not in", ["Closed", "Cancelled"]],
			},
		},
		{
			"label": "Parts Queue",
			"link_type": "Report",
			"link_to": "Jobs Waiting for Parts",
			"is_query_report": 1,
		},
		{"label": "Quality Check", "link_type": "DocType", "link_to": "Quality Check"},
		{"label": "Repair Job Log", "link_type": "DocType", "link_to": "Repair Job Log"},
		{
			"label": "Repair Job Override",
			"link_type": "DocType",
			"link_to": "Repair Job Override",
		},
	),
	"QC, Release & History": (
		{
			"label": "QC Queue",
			"link_type": "DocType",
			"link_to": "Quality Check",
			"route_options": {"status": "Pending"},
		},
		{
			"label": "Invoice Queue",
			"link_type": "DocType",
			"link_to": "Sales Invoice",
			"route_options": {"docstatus": 0},
		},
		{"label": "Gate Pass", "link_type": "DocType", "link_to": "Gate Pass"},
		{
			"label": "Gate Passes",
			"link_type": "Report",
			"link_to": "Gate Pass Register",
			"is_query_report": 1,
		},
		{"label": "Service History", "link_type": "DocType", "link_to": "Service History"},
		{
			"label": "Vehicle Service History",
			"link_type": "Report",
			"link_to": "Vehicle Service History",
			"is_query_report": 1,
		},
	),
	"Fleet & Exceptions": (
		{
			"label": "Fleet Service Campaign",
			"link_type": "DocType",
			"link_to": "Fleet Service Campaign",
		},
		{
			"label": "Repair Job Override",
			"link_type": "DocType",
			"link_to": "Repair Job Override",
		},
		{
			"label": "Corporate Credit Releases",
			"link_type": "Report",
			"link_to": "Corporate Credit Releases",
			"is_query_report": 1,
		},
		{
			"label": "Discount and Price Change Audit",
			"link_type": "Report",
			"link_to": "Discount and Price Change Audit",
			"is_query_report": 1,
		},
	),
	"Reports": tuple(
		{
			"label": report_name,
			"link_type": "Report",
			"link_to": report_name,
			"is_query_report": 1,
		}
		for report_name in WORKSPACE_REPORT_LINKS
	),
}


@frappe.whitelist()
def get_auto_service_settings_configured_card_data():
	configured = 1 if frappe.db.exists("Auto Service Settings", "Auto Service Settings") else 0
	return {
		"value": configured,
		"fieldtype": "Int",
		"route": ["Form", "Auto Service Settings", "Auto Service Settings"],
	}


def get_component_child_card_data(card_label: str):
	config = CHILD_COMPONENT_CARD_CONFIG[card_label]
	frappe.has_permission(config["parent_doctype"], "read", throw=True)
	return {
		"value": frappe.db.count(config["child_doctype"]),
		"fieldtype": "Int",
		"route": config["route"],
	}


@frappe.whitelist()
def get_repair_job_service_parts_card_data():
	return get_component_child_card_data("Repair Job Service Parts")


@frappe.whitelist()
def get_repair_job_service_labour_card_data():
	return get_component_child_card_data("Repair Job Service Labour")


@frappe.whitelist()
def get_repair_job_service_consumables_card_data():
	return get_component_child_card_data("Repair Job Service Consumables")
