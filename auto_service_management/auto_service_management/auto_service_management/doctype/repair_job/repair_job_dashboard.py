"""Native Connections dashboard for Repair Job."""

from frappe import _


def get_data():
	"""Return the native Frappe dashboard contract for Repair Job."""
	return {
		"fieldname": "repair_job",
		"internal_links": {
			"Customer": "customer",
			"Customer Vehicle": "customer_vehicle",
			"Project": "project",
			"Fleet Service Campaign": "fleet_service_campaign",
			"Quotation": "quotation",
			"Sales Order": ["sales_orders", "sales_order"],
			"Sales Invoice": ["sales_invoices", "sales_invoice"],
			"Payment Entry": ["payment_entries", "payment_entry"],
			"Repair Job Service": ["repair_job_services", "repair_job_service"],
		},
		"transactions": [
			{
				"label": _("Workshop"),
				"items": [
					"Repair Job Service",
					"Walkaround Inspection",
					"Diagnosis Report",
					"Customer Authorization",
					"Quality Check",
					"Gate Pass",
					"Service History",
					"Repair Job Override",
					"Repair Job Log",
				],
			},
			{
				"label": _("Billing & Materials"),
				"items": [
					"Sales Order",
					"Sales Invoice",
					"Payment Entry",
					"Material Request",
					"Quotation",
				],
			},
			{
				"label": _("Context"),
				"items": [
					"Customer",
					"Customer Vehicle",
					"Project",
					"Fleet Service Campaign",
				],
			},
		],
	}
