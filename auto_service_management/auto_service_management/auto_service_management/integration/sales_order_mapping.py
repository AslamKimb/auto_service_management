import frappe

TRACE_FIELDS = (
	"repair_job",
	"customer_vehicle",
	"repair_job_service",
	"repair_component_doctype",
	"repair_component_row",
	"repair_service_line",
)


@frappe.whitelist(methods=["POST"])
def make_sales_invoice(source_name, target_doc=None, args=None):
	"""Use ERPNext's mapper and preserve Repair Job component traces."""
	from erpnext.selling.doctype.sales_order.sales_order import (
		make_sales_invoice as native_make_sales_invoice,
	)

	invoice = native_make_sales_invoice(source_name, target_doc=target_doc, args=args)
	sales_order = frappe.get_doc("Sales Order", source_name)
	if sales_order.get("fleet_service_campaign"):
		invoice.fleet_service_campaign = sales_order.fleet_service_campaign
		invoice.repair_job = None
		invoice.project = None
	elif sales_order.get("repair_job"):
		invoice.repair_job = sales_order.repair_job

	sales_order_items = sales_order.get("items") or []
	invoice_items = invoice.get("items") or []
	items_by_source = {
		item.get("so_detail"): item for item in invoice_items if item.get("so_detail")
	}
	for index, sales_order_item in enumerate(sales_order_items):
		invoice_item = items_by_source.get(sales_order_item.get("name"))
		if not invoice_item and index < len(invoice_items):
			# ERPNext normally supplies so_detail. Positional fallback keeps compatibility
			# with older mapper responses that omit it without overriding an exact match.
			invoice_item = invoice_items[index]
		if not invoice_item:
			continue
		for fieldname in TRACE_FIELDS:
			value = sales_order_item.get(fieldname)
			if value:
				invoice_item.set(fieldname, value)
		if sales_order_item.get("sales_order") and not invoice_item.get("sales_order"):
			invoice_item.sales_order = sales_order_item.sales_order
		if sales_order_item.get("name") and not invoice_item.get("so_detail"):
			invoice_item.so_detail = sales_order_item.name
	return invoice
