app_name = "auto_service_management"
app_title = "Auto Service Management"
app_publisher = "Aslam Kimbugwe"
app_description = "Automobile Repair Management for Frappe/ERPNext"
app_email = "kimbugwe43@gmail.com"
app_license = "gpl-3.0"

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
]

# DocType Events
doc_events = {
	"User": {
		"validate": "auto_service_management.auto_service_management.user_defaults.assign_default_workspace",
	},
	"Sales Invoice": {
		"on_submit": "auto_service_management.auto_service_management.integration.erpnext.adapters.on_invoice_submit",
	},
}

# Lifecycle hooks — ensure Desktop Icon records exist after install/migrate
after_install = [
	"auto_service_management.auto_service_management.desktop.create_app_desktop_icon",
]
after_migrate = [
	"auto_service_management.auto_service_management.desktop.create_app_desktop_icon",
]
