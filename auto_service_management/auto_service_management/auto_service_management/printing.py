"""Shared print branding and app-owned editable print formats."""

import json

import frappe

DMS_PRINT_FORMATS = (
	("Customer Authorization", "Customer Authorization", "customer_authorization"),
	("Estimate Summary", "Repair Job", "estimate_summary"),
	("Gate Pass", "Gate Pass", "gate_pass"),
	("Job Card", "Repair Job", "job_card"),
	("Repair Summary", "Repair Job", "repair_summary"),
	("Walkaround Inspection", "Walkaround Inspection", "walkaround_inspection"),
)

WORKSHOP_PRINT_FORMATS = (
	("Quotation", "Quotation"),
	("Sales Invoice", "Sales Invoice"),
	("Sales Order", "Sales Order"),
	("Material Request", "Material Request"),
	("Stock Entry", "Stock Entry"),
	("Timesheet", "Timesheet"),
	("Payment Entry", "Payment Entry"),
)


def normalize_logo_url(value, base_url):
	"""Return a browser/PDF-safe absolute logo URL."""
	if not value:
		return None
	if value.startswith(("http://", "https://", "data:")):
		return value
	return f"{base_url.rstrip('/')}/{value.lstrip('/')}"


def resolve_logo_url(company_logo, app_logo, banner_image, base_url):
	"""Resolve the approved company-first logo precedence."""
	return normalize_logo_url(company_logo or app_logo or banner_image, base_url)


def get_print_branding(doc):
	"""Return company details and the logo used by DMS print templates."""
	company_name = (
		getattr(doc, "company", None)
		or frappe.db.get_single_value("Auto Service Settings", "company")
		or frappe.defaults.get_global_default("company")
	)
	company = (
		frappe.db.get_value(
			"Company",
			company_name,
			["company_name", "company_logo", "phone_no", "email", "website"],
			as_dict=True,
		)
		if company_name
		else frappe._dict()
	) or frappe._dict()
	website = frappe.get_single("Website Settings")
	return frappe._dict(
		company=company,
		company_name=company.company_name or company_name or "Auto Service Workshop",
		logo=resolve_logo_url(
			company.company_logo,
			website.app_logo,
			website.banner_image,
			frappe.utils.get_url(),
		),
		contact=" · ".join(
			value for value in (company.phone_no, company.email, company.website) if value
		),
	)


def _builder_format_data(template=None, html=None):
	if not template and not html:
		return json.dumps(
			[
				{
					"fieldname": "_custom_html",
					"fieldtype": "Custom HTML",
					"label": "Custom HTML",
					"options": "<h3>{{ doc.name }}</h3>",
				}
			]
		)
	options = html or f'{{% set _doc = doc %}}{{% include "templates/includes/auto_service_print/{template}.html" %}}'
	return json.dumps(
		[
			{
				"fieldname": "_custom_html",
				"fieldtype": "Custom HTML",
				"label": "Custom HTML",
				"options": options,
			}
		]
	)


def _ensure_builder_format(name, doc_type, format_data=None):
	if not frappe.db.exists("DocType", doc_type):
		return
	existing = frappe.db.exists("Print Format", name)
	if existing:
		fallback = _builder_format_data()
		current = frappe.db.get_value("Print Format", name, "format_data")
		if format_data and current in (None, fallback):
			frappe.db.set_value("Print Format", name, "format_data", format_data, update_modified=False)
		return

	doc = frappe.get_doc(
		{
			"doctype": "Print Format",
			"name": name,
			"doc_type": doc_type,
			"standard": "No",
			"custom_format": 0,
			"print_format_builder": 1,
			"print_format_builder_beta": 0,
			"disabled": 0,
			"format_data": format_data,
		}
	)
	doc.insert(ignore_permissions=True)
	if doc.print_format_builder_beta:
		frappe.db.set_value(
			"Print Format", doc.name, "print_format_builder_beta", 0, update_modified=False
		)


def _workshop_builder_format_data(doc_type):
	"""Carry a usable ERPNext layout into the editable builder copy."""
	sources = frappe.get_all(
		"Print Format",
		{"doc_type": doc_type, "standard": "Yes", "disabled": 0},
		["format_data", "html"],
		order_by="name asc",
	)
	source = next((row for row in sources if row.format_data or row.html), None)
	if source and source.format_data:
		return source.format_data
	return _builder_format_data(html=source.html if source else None)


def _letterhead_content():
	return '{% include "templates/includes/auto_service_print/letterhead.html" %}'


def _ensure_letterhead(name, is_default):
	content = _letterhead_content()
	if frappe.db.exists("Letter Head", name):
		existing = frappe.get_doc("Letter Head", name)
		if existing.content == content and existing.source != "HTML":
			frappe.db.set_value(
				"Letter Head",
				name,
				{"source": "HTML", "content": content},
				update_modified=False,
			)
		return

	doc = frappe.get_doc(
		{
			"doctype": "Letter Head",
			"letter_head_name": name,
			"source": "HTML",
			"content": content,
			"is_default": int(is_default),
			"disabled": 0,
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.set_value(
		"Letter Head",
		name,
		{"source": "HTML", "content": content},
		update_modified=False,
	)


def ensure_print_branding():
	"""Idempotently create app-owned builder formats and branded letterheads."""
	for name, doc_type, template in DMS_PRINT_FORMATS:
		_ensure_builder_format(
			f"DMS Editable - {name}",
			doc_type,
			_builder_format_data(template),
		)

	for name, doc_type in WORKSHOP_PRINT_FORMATS:
		_ensure_builder_format(
			f"DMS Editable - {name}",
			doc_type,
			_workshop_builder_format_data(doc_type),
		)

	current_default = frappe.db.get_value("Letter Head", {"is_default": 1}, "name")
	use_app_default = not current_default or current_default in {
		"Company Letterhead - Grey",
		"Company Letterhead",
	}
	_ensure_letterhead("DMS Company Letterhead", use_app_default)
	_ensure_letterhead("DMS Company Letterhead - Compact", False)
