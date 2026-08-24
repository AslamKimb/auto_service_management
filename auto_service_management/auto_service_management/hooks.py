app_name = "auto_service_management"
app_title = "Car Workshop"
app_publisher = "Aslam Kimbugwe"
app_description = "Automobile Repair Management for Frappe/ERPNext"
app_email = "kimbugwe43@gmail.com"
app_license = "gpl-3.0"

from auto_service_management.auto_service_management.custom_fields import TRACE_CUSTOM_FIELD_NAMES

# Apps
required_apps = ["erpnext"]
app_include_js = ["repair_job_billing.bundle.js"]
app_home = "/desk/workshop-management"
app_logo_url = "/assets/auto_service_management/icons/desktop_icons/solid/car_workshop.svg"
add_to_apps_screen = [
	{
		"name": "auto_service_management",
		"logo": app_logo_url,
		"title": "Car Workshop",
		"route": app_home,
		"has_permission": "auto_service_management.auto_service_management.desktop.check_app_permission",
	}
]

jinja = {
	"methods": [
		"auto_service_management.auto_service_management.printing.get_print_branding",
		"auto_service_management.auto_service_management.printing.get_job_card_context",
	],
}

portal_menu_items = [
	{"title": "My Repairs", "route": "/my-repairs", "role": "Customer"},
]

website_route_rules = [
	{"from_route": "/my-repairs", "to_route": "my_repairs"},
	{"from_route": "/my-repairs/<path:name>", "to_route": "my_repairs"},
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
					"Auto Service Admin",
				],
			],
		],
	},
	{
		"dt": "Custom DocPerm",
		"filters": [
			["parent", "in", ["Sales Invoice", "Customer"]],
			["role", "in", ["Cashier", "Service Advisor"]],
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

override_doctype_dashboards = {
	"Customer": [
		"auto_service_management.auto_service_management.dashboard_overrides.get_customer_dashboard"
	],
}

override_whitelisted_methods = {
	"erpnext.selling.doctype.quotation.quotation.make_sales_invoice": "auto_service_management.auto_service_management.integration.quotation_mapping.make_sales_invoice",
	"erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice": "auto_service_management.auto_service_management.integration.sales_order_mapping.make_sales_invoice",
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
	"Payment Entry": {
		"on_submit": "auto_service_management.auto_service_management.integration.erpnext.document_sync.sync_payment_entry",
		"on_cancel": "auto_service_management.auto_service_management.integration.erpnext.document_sync.sync_payment_entry",
		"on_trash": "auto_service_management.auto_service_management.integration.erpnext.document_sync.sync_payment_entry",
	},
	"Material Request": {
		"validate": "auto_service_management.auto_service_management.integration.erpnext.document_sync.validate_material_request",
		"on_update": "auto_service_management.auto_service_management.integration.erpnext.document_sync.sync_material_request",
		"on_submit": "auto_service_management.auto_service_management.integration.erpnext.document_sync.sync_material_request",
		"on_cancel": "auto_service_management.auto_service_management.integration.erpnext.document_sync.cancel_material_request",
		"on_trash": "auto_service_management.auto_service_management.integration.erpnext.document_sync.trash_material_request",
	},
	"Sales Order": {
		"validate": "auto_service_management.auto_service_management.integration.erpnext.document_sync.validate_sales_order",
		"on_update": "auto_service_management.auto_service_management.integration.erpnext.document_sync.sync_sales_order",
		"on_submit": "auto_service_management.auto_service_management.integration.erpnext.document_sync.submit_sales_order",
		"on_cancel": "auto_service_management.auto_service_management.integration.erpnext.document_sync.cancel_sales_order",
		"on_trash": "auto_service_management.auto_service_management.integration.erpnext.document_sync.trash_sales_order",
	},
	"Timesheet": {
		"on_submit": "auto_service_management.auto_service_management.integration.erpnext.adapters.sync_timesheet_actuals",
		"on_cancel": "auto_service_management.auto_service_management.integration.erpnext.adapters.sync_timesheet_actuals",
	},
}

# Lifecycle hooks — ensure Desktop Icon records exist after install/migrate
after_install = [
	"auto_service_management.patches.vehicle_make_model_catalog.execute",
	"auto_service_management.auto_service_management.custom_fields.ensure_trace_custom_fields",
	"auto_service_management.patches.phase6_permission_matrix_repair.execute",
	"auto_service_management.patches.phase24_reconcile_custom_permissions.execute",
	"auto_service_management.auto_service_management.workflow_setup.deactivate_repair_job_workflow",
	"auto_service_management.auto_service_management.desktop.setup_desktop",
	"auto_service_management.auto_service_management.printing.ensure_print_branding",
]
after_migrate = [
	"auto_service_management.auto_service_management.custom_fields.ensure_trace_custom_fields",
	"auto_service_management.patches.phase6_permission_matrix_repair.execute",
	"auto_service_management.patches.phase24_reconcile_custom_permissions.execute",
	"auto_service_management.auto_service_management.workflow_setup.deactivate_repair_job_workflow",
	"auto_service_management.auto_service_management.desktop.setup_desktop",
	"auto_service_management.auto_service_management.printing.ensure_print_branding",
]
before_tests = [
	"auto_service_management.auto_service_management.custom_fields.ensure_trace_custom_fields",
	"auto_service_management.patches.phase6_permission_matrix_repair.execute",
	"auto_service_management.patches.phase24_reconcile_custom_permissions.execute",
	"auto_service_management.auto_service_management.workflow_setup.deactivate_repair_job_workflow",
	"auto_service_management.auto_service_management.desktop.setup_desktop",
	"auto_service_management.auto_service_management.printing.ensure_print_branding",
]
boot_session = ["auto_service_management.auto_service_management.desktop.remove_auto_generated_sidebar"]
