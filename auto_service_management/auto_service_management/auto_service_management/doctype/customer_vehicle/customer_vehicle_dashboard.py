"""Workshop history dashboard for Customer Vehicle."""

from frappe import _


def get_data():
	return {
		"fieldname": "customer_vehicle",
		"transactions": [
			{
				"label": _("Workshop History"),
				"items": ["Repair Job", "Repair Job Service", "Service History"],
			}
		],
	}
