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
	"Workshop Bay View",
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

WORKSPACE_REPORT_ICONS = {
	"Open Repair Jobs": "clipboard-list",
	"Daily Workshop Load": "calendar-clock",
	"Workshop Bay View": "warehouse",
	"Jobs by Status": "chart-gantt",
	"Jobs Waiting for Parts": "package-search",
	"Technician Productivity": "gauge",
	"Labour Hours by Technician": "clock",
	"Parts Used by Repair Job": "package-search",
	"Vehicle Service History": "history",
	"Delayed Jobs": "triangle-alert",
	"Repair Revenue by Period": "circle-dollar-sign",
	"Gate Pass Register": "shield-check",
	"Corporate Credit Releases": "hand-coins",
	"Discount and Price Change Audit": "badge-percent",
}

WORKSPACE_SIDEBAR_SECTION_ICONS = {
	"Intake & Setup": "settings",
	"Workshop Execution": "wrench",
	"QC, Release & History": "shield-check",
	"Fleet & Exceptions": "caravan",
	"Reports": "file-chart-column",
}

WORKSPACE_SIDEBAR_HOME = {
	"label": "Home",
	"link_type": "Workspace",
	"link_to": "Workshop Management",
	"icon": "house",
}

WORKSPACE_SIDEBAR_SECTIONS = {
	"Intake & Setup": (
		{
			"label": "Auto Service Settings",
			"link_type": "DocType",
			"link_to": "Auto Service Settings",
			"icon": "settings",
		},
		{
			"label": "Customer Vehicle",
			"link_type": "DocType",
			"link_to": "Customer Vehicle",
			"icon": "car-front",
		},
		{"label": "Workshop Bay", "link_type": "DocType", "link_to": "Workshop Bay", "icon": "warehouse"},
		{
			"label": "Repair Job",
			"link_type": "DocType",
			"link_to": "Repair Job",
			"icon": "clipboard-list",
		},
		{
			"label": "Walkaround Inspection",
			"link_type": "DocType",
			"link_to": "Walkaround Inspection",
			"icon": "scan-search",
		},
		{
			"label": "Diagnosis Report",
			"link_type": "DocType",
			"link_to": "Diagnosis Report",
			"icon": "search-check",
		},
		{
			"label": "Customer Authorization",
			"link_type": "DocType",
			"link_to": "Customer Authorization",
			"icon": "signature",
		},
	),
	"Workshop Execution": (
		{
			"label": "Repair Job",
			"link_type": "DocType",
			"link_to": "Repair Job",
			"icon": "clipboard-list",
		},
		{
			"label": "Repair Job Service",
			"link_type": "DocType",
			"link_to": "Repair Job Service",
			"icon": "wrench",
		},
		{
			"label": "Repair Queue",
			"link_type": "DocType",
			"link_to": "Repair Job",
			"icon": "clipboard-clock",
			"route_options": {
				"job_status": ["not in", ["Closed", "Cancelled"]],
			},
		},
		{
			"label": "Parts Queue",
			"link_type": "Report",
			"link_to": "Jobs Waiting for Parts",
			"is_query_report": 1,
			"icon": "package-search",
		},
		{
			"label": "Quality Check",
			"link_type": "DocType",
			"link_to": "Quality Check",
			"icon": "clipboard-check",
		},
		{
			"label": "Repair Job Log",
			"link_type": "DocType",
			"link_to": "Repair Job Log",
			"icon": "history",
		},
		{
			"label": "Repair Job Override",
			"link_type": "DocType",
			"link_to": "Repair Job Override",
			"icon": "shield-alert",
		},
	),
	"QC, Release & History": (
		{
			"label": "QC Queue",
			"link_type": "DocType",
			"link_to": "Quality Check",
			"route_options": {"status": "Pending"},
			"icon": "clipboard-check",
		},
		{
			"label": "Invoice Queue",
			"link_type": "DocType",
			"link_to": "Sales Invoice",
			"route_options": {"docstatus": 0},
			"icon": "receipt-text",
		},
		{"label": "Gate Pass", "link_type": "DocType", "link_to": "Gate Pass", "icon": "shield-check"},
		{
			"label": "Gate Passes",
			"link_type": "Report",
			"link_to": "Gate Pass Register",
			"is_query_report": 1,
			"icon": "shield-check",
		},
		{
			"label": "Service History",
			"link_type": "DocType",
			"link_to": "Service History",
			"icon": "history",
		},
		{
			"label": "Vehicle Service History",
			"link_type": "Report",
			"link_to": "Vehicle Service History",
			"is_query_report": 1,
			"icon": "history",
		},
	),
	"Fleet & Exceptions": (
		{
			"label": "Fleet Service Campaign",
			"link_type": "DocType",
			"link_to": "Fleet Service Campaign",
			"icon": "caravan",
		},
		{
			"label": "Repair Job Override",
			"link_type": "DocType",
			"link_to": "Repair Job Override",
			"icon": "shield-alert",
		},
		{
			"label": "Corporate Credit Releases",
			"link_type": "Report",
			"link_to": "Corporate Credit Releases",
			"is_query_report": 1,
			"icon": "hand-coins",
		},
		{
			"label": "Discount and Price Change Audit",
			"link_type": "Report",
			"link_to": "Discount and Price Change Audit",
			"is_query_report": 1,
			"icon": "badge-percent",
		},
	),
	"Reports": tuple(
		{
			"label": report_name,
			"link_type": "Report",
			"link_to": report_name,
			"is_query_report": 1,
			"icon": WORKSPACE_REPORT_ICONS.get(report_name, "file-chart-column"),
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
