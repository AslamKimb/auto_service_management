from __future__ import annotations

import frappe


@frappe.whitelist(methods=["POST"])
def make_sales_invoice(source_name, target_doc=None, args=None):
	"""Keep ERPNext's native quotation mapper and add app-owned trace fields."""
	from erpnext.selling.doctype.quotation.quotation import (
		make_sales_invoice as native_make_sales_invoice,
	)

	invoice = native_make_sales_invoice(source_name, target_doc=target_doc, args=args)
	quotation = frappe.get_doc("Quotation", source_name)
	if quotation.get("repair_job"):
		invoice.repair_job = quotation.repair_job

	for quotation_item, invoice_item in zip(
		quotation.get("items") or [], invoice.get("items") or [], strict=False
	):
		for fieldname in (
			"repair_job",
			"customer_vehicle",
			"repair_job_service",
			"repair_component_doctype",
			"repair_component_row",
			"repair_service_line",
		):
			value = quotation_item.get(fieldname)
			if value:
				invoice_item.set(fieldname, value)

	return invoice
