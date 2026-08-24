"""Dashboard extensions for ERPNext master documents."""

from frappe import _


def get_customer_dashboard(data=None):
	"""Extend ERPNext's Customer dashboard with workshop history.

	The standard ERPNext dashboard remains the source of truth.  This hook only
	adds a native transaction group for the app-owned Customer Vehicle and
	Repair Job links.
	"""
	data = data or {}
	transactions = list(data.get("transactions") or [])
	group = next(
		(group for group in transactions if group.get("label") == _("Workshop History")),
		None,
	)
	if group is None:
		group = {"label": _("Workshop History"), "items": []}
		transactions.append(group)

	items = list(group.get("items") or [])
	for doctype in ("Customer Vehicle", "Repair Job"):
		if doctype not in items:
			items.append(doctype)
	group["items"] = items
	data["transactions"] = transactions
	return data
