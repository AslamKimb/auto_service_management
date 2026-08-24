from frappe import _


def get_data():
	return {
		"fieldname": "fleet_service_campaign",
		"transactions": [
			{"label": _("Workshop"), "items": ["Repair Job"]},
			{"label": _("Campaign Billing"), "items": ["Sales Order", "Sales Invoice"]},
		],
	}
