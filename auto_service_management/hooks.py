app_name = "auto_service_management"
app_title = "Auto Service Management"
app_description = "Auto service and workshop management for ERPNext."
app_home = "/app/workshop-management"

add_to_apps_screen = [
	{
		"name": app_name,
		"title": app_title,
		"route": app_home,
	}
]

app_include_css = "/assets/auto_service_management/css/auto_service_management.css"

after_install = "auto_service_management.auto_service_management.desktop.setup_desktop"
after_migrate = "auto_service_management.auto_service_management.desktop.setup_desktop"

doctype_js = {
	"Sales Invoice": "public/js/sales_invoice.js",
	"Material Request": "public/js/material_request.js",
}

doc_events = {
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
		"on_cancel": "auto_service_management.auto_service_management.integration.erpnext.document_sync.cancel_material_request",
		"on_trash": "auto_service_management.auto_service_management.integration.erpnext.document_sync.trash_material_request",
	},
}
