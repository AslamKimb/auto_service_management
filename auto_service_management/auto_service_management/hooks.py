app_name = "auto_service_management"
app_title = "Auto Service Management"
app_publisher = "Aslam Kimbugwe"
app_description = "Automobile Repair Management for Frappe/ERPNext"
app_email = "kimbugwe43@gmail.com"
app_license = "gpl-3.0"

from auto_service_management.auto_service_management.custom_fields import TRACE_CUSTOM_FIELD_NAMES

# Apps
required_apps = ["erpnext"]

# Desk desktop surfacing — creates an App-type Desktop Icon so the module
# card appears on the Frappe Desk desktop alongside Accounting, Selling, etc.
add_to_apps_screen = [
	{
		"name": app_name,
		"title": app_title,
		"route": "/app/workshop-management",
		"has_permission": "auto_service_management.auto_service_management.desktop.ensure_permission",
	}
]

# Fixtures — filtered to app-owned roles only
fixtures = [
	{
		"dt": "Role",
		"filters": [
			[
				"role_name",
				"in",
				[
					"Workshop Manager",
					"Service Advisor",
					"Parts Interpreter",
					"Cashier",
					"Security Gate Officer",
					"Workshop Technician",
				],
			],
		],
	},
	{
		"dt": "Custom DocPerm",
		"filters": [
			["parent", "=", "Sales Invoice"],
			["role", "=", "Cashier"],
			["permlevel", "=", 0],
		],
	},
	{
		"dt": "Property Setter",
		"filters": [
			["doc_type", "=", "Repair Job"],
			["field_name", "in", ["odometer_in", "customer_concern"]],
			["property", "=", "reqd"],
		],
	},
	{
		"dt": "Custom Field",
		"filters": [
			["name", "in", list(TRACE_CUSTOM_FIELD_NAMES)],
		],
	},
]

# DocType Events
doctype_js = {
	"Sales Invoice": "public/js/sales_invoice.js",
	"Material Request": "public/js/material_request.js",
}

doc_events = {
	"User": {
		"validate": "auto_service_management.auto_service_management.user_defaults.assign_default_workspace",
	},
	"Sales Invoice": {
		"validate": "auto_service_management.auto_service_management.integration.erpnext.document_sync.validate_sales_invoice",
		"on_update": "auto_service_management.auto_service_management.integration.erpnext.document_sync.sync_sales_invoice",
		"on_submit": "auto_service_management.auto_service_management.integration.erpnext.document_sync.submit_sales_invoice",
		"on_cancel": "auto_service_management.auto_service_management.integration.erpnext.document_sync.cancel_sales_invoice",
		"on_trash": "auto_service_management.auto_service_management.integration.erpnext.document_sync.trash_sales_invoice",
	},
	"Material Request": {
		"validate": "auto_service_management.auto_service_management.integration.erpnext.document_sync.validate_material_request",
		"on_update": "auto_service_management.auto_service_management.integration.erpnext.document_sync.sync_material_request",
		"on_submit": "auto_service_management.auto_service_management.integration.erpnext.document_sync.sync_material_request",
		"on_cancel": "auto_service_management.auto_service_management.integration.erpnext.document_sync.cancel_material_request",
		"on_trash": "auto_service_management.auto_service_management.integration.erpnext.document_sync.trash_material_request",
	},
	"Timesheet": {
		"on_submit": "auto_service_management.auto_service_management.integration.erpnext.adapters.sync_timesheet_actuals",
		"on_cancel": "auto_service_management.auto_service_management.integration.erpnext.adapters.sync_timesheet_actuals",
	},
}

# Lifecycle hooks — ensure Desktop Icon records exist after install/migrate
after_install = [
	"auto_service_management.auto_service_management.custom_fields.ensure_trace_custom_fields",
	"auto_service_management.auto_service_management.desktop.setup_desktop",
]
after_migrate = [
	"auto_service_management.auto_service_management.custom_fields.ensure_trace_custom_fields",
	"auto_service_management.auto_service_management.desktop.setup_desktop",
]
before_tests = [
	"auto_service_management.auto_service_management.custom_fields.ensure_trace_custom_fields",
	"auto_service_management.auto_service_management.desktop.setup_desktop",
]
