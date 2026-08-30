from frappe import _


def get_data(data=None):
	"""Return the native dashboard contract for the Customer LPO override hook."""
	return {
		"fieldname": "customer_lpo",
		"internal_links": {"Customer Vehicle": ["vehicle_rows", "customer_vehicle"]},
		"transactions": [
			{
				"label": _("Fleet Operations"),
				"items": ["Fleet Service Campaign", "Repair Job", "Customer Vehicle"],
			},
			{"label": _("Billing"), "items": ["Sales Order", "Sales Invoice", "Customer LPO Amendment"]},
		],
	}
