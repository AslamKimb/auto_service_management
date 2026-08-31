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
	"Customer Vehicle Customer Association": "Customer Vehicle Customer Associations",
	"Workshop Bay": "Workshop Bays",
	"Repair Job": "Repair Jobs",
	"Repair Job Service": "Repair Job Services",
	"Repair Job Service Template": "Repair Job Service Templates",
	"Repair Job Service Template Part": "Repair Job Service Template Parts",
	"Repair Job Service Template Labour": "Repair Job Service Template Labour",
	"Repair Job Service Template Consumable": "Repair Job Service Template Consumables",
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
	"Customer LPO": "Customer LPOs",
	"Customer LPO Vehicle": "Customer LPO Vehicles",
	"Customer LPO Amendment": "Customer LPO Amendments",
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
	"Customer LPO Utilization",
	"Customer LPO Vehicle Progress",
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
	"Customer LPO Utilization": "wallet-cards",
	"Customer LPO Vehicle Progress": "list-tree",
}


def _doctype_link(label, link_to, icon, **kwargs):
	return {"label": label, "link_type": "DocType", "link_to": link_to, "icon": icon, **kwargs}


def _report_link(label, icon=None):
	return {
		"label": label,
		"link_type": "Report",
		"link_to": label,
		"is_query_report": 1,
		"icon": icon or WORKSPACE_REPORT_ICONS.get(label, "file-chart-column"),
	}


_WORKSHOP_ROLES = (
	"Workshop Manager",
	"Service Advisor",
	"Parts Interpreter",
	"Cashier",
	"Security Gate Officer",
	"Workshop Technician",
)

_ADMIN_ROLES = ("System Manager", "Auto Service Admin")


WORKSPACE_HUBS = {
	"Overview": {
		"label": "Overview",
		"workspace_name": "Workshop Management",
		"sidebar_name": "Overview",
		"roles": ("Workshop Manager", "Service Advisor", *_ADMIN_ROLES),
		"icon": "layout-dashboard",
		"logo_url": "/assets/auto_service_management/icons/desktop_icons/solid/workshop_overview.svg",
		"links": (
			_doctype_link("New Repair Job", "Repair Job", "clipboard-list"),
			_report_link("Open Repair Jobs"),
			_doctype_link("Find Vehicle", "Customer Vehicle", "car-front"),
		),
	},
	"Intake": {
		"label": "Intake",
		"workspace_name": "Customer Intake",
		"sidebar_name": "Intake",
		"roles": ("Service Advisor", "Workshop Manager", *_ADMIN_ROLES),
		"icon": "clipboard-list",
		"logo_url": "/assets/auto_service_management/icons/desktop_icons/solid/workshop_intake.svg",
		"links": (
			_doctype_link("Customers", "Customer", "users"),
			_doctype_link("Find Vehicle", "Customer Vehicle", "car-front"),
			_doctype_link("Repair Job", "Repair Job", "clipboard-list"),
			_doctype_link("Walkaround Inspection", "Walkaround Inspection", "scan-search"),
			_doctype_link("Diagnosis Report", "Diagnosis Report", "search-check"),
			_doctype_link("Customer Authorization", "Customer Authorization", "signature"),
		),
	},
	"Workshop": {
		"label": "Workshop",
		"workspace_name": "Workshop Operations",
		"sidebar_name": "Workshop",
		"roles": (
			"Workshop Manager",
			"Workshop Technician",
			"Service Advisor",
			"Parts Interpreter",
			*_ADMIN_ROLES,
		),
		"icon": "wrench",
		"logo_url": "/assets/auto_service_management/icons/desktop_icons/solid/workshop_operations.svg",
		"links": (
			_doctype_link(
				"Repair Queue",
				"Repair Job",
				"clipboard-clock",
				route_options={"job_status": ["not in", ["Closed", "Cancelled"]]},
			),
			_doctype_link("Repair Job Service", "Repair Job Service", "wrench"),
			_doctype_link("Workshop Bay", "Workshop Bay", "warehouse"),
			_doctype_link("Service Templates", "Repair Job Service Template", "copy"),
			_report_link("Daily Workshop Load"),
			_report_link("Workshop Bay View"),
			_report_link("Jobs by Status"),
			_report_link("Delayed Jobs"),
			_report_link("Technician Productivity"),
			_report_link("Labour Hours by Technician"),
		),
	},
	"Parts & Billing": {
		"label": "Parts & Billing",
		"workspace_name": "Parts & Billing",
		"sidebar_name": "Parts & Billing",
		"roles": (
			"Parts Interpreter",
			"Cashier",
			"Service Advisor",
			"Workshop Manager",
			"Accounts Manager",
			*_ADMIN_ROLES,
		),
		"icon": "receipt-text",
		"logo_url": "/assets/auto_service_management/icons/desktop_icons/solid/workshop_parts_billing.svg",
		"links": (
			_report_link("Jobs Waiting for Parts", "package-search"),
			_doctype_link("Material Requests", "Material Request", "package"),
			_doctype_link("Sales Orders", "Sales Order", "file-text"),
			_doctype_link("Sales Invoices", "Sales Invoice", "receipt-text"),
			_doctype_link("Payment Entries", "Payment Entry", "circle-dollar-sign"),
			_report_link("Parts Used by Repair Job", "package-search"),
			_report_link("Repair Revenue by Period", "circle-dollar-sign"),
		),
	},
	"Quality & Release": {
		"label": "Quality & Release",
		"workspace_name": "Quality & Release",
		"sidebar_name": "Quality & Release",
		"roles": (
			"Workshop Manager",
			"Workshop Technician",
			"Service Advisor",
			"Security Gate Officer",
			*_ADMIN_ROLES,
		),
		"icon": "shield-check",
		"logo_url": "/assets/auto_service_management/icons/desktop_icons/solid/workshop_quality_release.svg",
		"links": (
			_doctype_link(
				"QC Queue", "Quality Check", "clipboard-check", route_options={"status": "Pending"}
			),
			_doctype_link("Gate Pass", "Gate Pass", "shield-check"),
			_doctype_link("Service History", "Service History", "history"),
			_report_link("Gate Pass Register", "shield-check"),
			_report_link("Vehicle Service History", "history"),
		),
	},
	"Fleet & History": {
		"label": "Fleet & History",
		"workspace_name": "Fleet & History",
		"sidebar_name": "Fleet & History",
		"roles": ("Workshop Manager", "Service Advisor", "Cashier", "Security Gate Officer", *_ADMIN_ROLES),
		"icon": "caravan",
		"logo_url": "/assets/auto_service_management/icons/desktop_icons/solid/workshop_fleet_history.svg",
		"links": (
			_doctype_link("Fleet Service Campaign", "Fleet Service Campaign", "caravan"),
			_doctype_link("Customer LPO", "Customer LPO", "file-input"),
			_doctype_link("Customers", "Customer", "users"),
			_doctype_link("Find Vehicle", "Customer Vehicle", "car-front"),
			_doctype_link("Service History", "Service History", "history"),
		),
	},
	"Reports": {
		"label": "Reports",
		"workspace_name": "Workshop Reports",
		"sidebar_name": "Reports",
		"roles": (*_WORKSHOP_ROLES, "Accounts Manager", *_ADMIN_ROLES),
		"icon": "file-chart-column",
		"logo_url": "/assets/auto_service_management/icons/desktop_icons/solid/workshop_reports.svg",
		"links": tuple(_report_link(report_name) for report_name in WORKSPACE_REPORT_LINKS),
	},
	"Setup": {
		"label": "Setup",
		"workspace_name": "Workshop Setup",
		"sidebar_name": "Setup",
		"roles": ("Workshop Manager", "Auto Service Admin", "System Manager"),
		"icon": "settings",
		"logo_url": "/assets/auto_service_management/icons/desktop_icons/solid/workshop_setup.svg",
		"links": (
			_doctype_link("Auto Service Settings", "Auto Service Settings", "settings"),
			_doctype_link("Workshop Bays", "Workshop Bay", "warehouse"),
			_doctype_link("Vehicle Makes", "Vehicle Make", "car-front"),
			_doctype_link("Vehicle Models", "Vehicle Model", "car-front"),
			_doctype_link("Service Templates", "Repair Job Service Template", "copy"),
			_doctype_link("Repair Job Overrides", "Repair Job Override", "shield-alert"),
			_doctype_link("Repair Job Logs", "Repair Job Log", "history"),
		),
	},
}

WORKSPACE_LINK_CARDS = tuple(WORKSPACE_HUBS)
WORKSPACE_SIDEBAR_SECTION_ICONS = {label: hub["icon"] for label, hub in WORKSPACE_HUBS.items()}
WORKSPACE_SIDEBAR_HOME = {
	"label": "Home",
	"link_type": "Workspace",
	"link_to": "Workshop Management",
	"icon": "house",
}
WORKSPACE_SIDEBAR_SECTIONS = {label: hub["links"] for label, hub in WORKSPACE_HUBS.items()}


@frappe.whitelist(methods=["GET"])
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


@frappe.whitelist(methods=["GET"])
def get_repair_job_service_parts_card_data():
	return get_component_child_card_data("Repair Job Service Parts")


@frappe.whitelist(methods=["GET"])
def get_repair_job_service_labour_card_data():
	return get_component_child_card_data("Repair Job Service Labour")


@frappe.whitelist(methods=["GET"])
def get_repair_job_service_consumables_card_data():
	return get_component_child_card_data("Repair Job Service Consumables")
