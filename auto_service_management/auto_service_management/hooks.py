app_name = "auto_service_management"
app_title = "Auto Service Management"
app_publisher = "Aslam Kimbugwe"
app_description = "Automobile Repair Management for Frappe/ERPNext"
app_email = "kimbugwe43@gmail.com"
app_license = "gpl-3.0"

# Apps
required_apps = ["erpnext"]

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
