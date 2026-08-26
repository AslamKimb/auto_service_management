"""Shared print branding and app-owned editable print formats."""

import json

import frappe

_DAMAGE_MARKER_POSITIONS = {
	"Front": (50, 12),
	"Rear": (50, 88),
	"Left Side": (18, 50),
	"Right Side": (82, 50),
	"Roof": (50, 42),
	"Undercarriage": (50, 68),
	"Interior": (50, 56),
	"Engine Bay": (50, 26),
	"Other": (50, 50),
}

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
	("Proforma Invoice", "Sales Order"),
	("Material Request", "Material Request"),
	("Stock Entry", "Stock Entry"),
	("Timesheet", "Timesheet"),
	("Payment Entry", "Payment Entry"),
)

PUBLIC_PRINT_LOGO = "/assets/auto_service_management/images/vectorised-bb109a99.svg"


def normalize_logo_url(value, base_url):
	"""Return a browser/PDF-safe absolute logo URL."""
	if not value:
		return None
	if value.startswith(("http://", "https://", "data:")):
		return value
	return f"{base_url.rstrip('/')}/{value.lstrip('/')}"


def _text(value):
	return str(value).strip() if value not in (None, "") else ""


def _join_nonempty(*values):
	return ", ".join(value for value in (_text(item) for item in values) if value)


def _vehicle_values(vehicle_name):
	vehicle = (
		frappe.db.get_value(
			"Customer Vehicle",
			vehicle_name,
			[
				"registration_number",
				"vin_chassis_number",
				"engine_number",
				"make",
				"model",
				"year_of_manufacture",
				"color",
			],
			as_dict=True,
		)
		if vehicle_name
		else None
	) or frappe._dict()
	model = (
		frappe.db.get_value("Vehicle Model", vehicle.model, "model_name") if vehicle.model else ""
	) or vehicle.model
	return {
		"account": _text(vehicle_name),
		"registration_number": _text(vehicle.registration_number),
		"vin_chassis_number": _text(vehicle.vin_chassis_number),
		"engine_number": _text(vehicle.engine_number),
		"make": _text(vehicle.make),
		"model": _text(model),
		"year_of_manufacture": _text(vehicle.year_of_manufacture),
		"color": _text(vehicle.color),
	}


def _customer_values(customer_name):
	customer = (
		frappe.db.get_value(
			"Customer",
			customer_name,
			[
				"customer_name",
				"tax_id",
				"primary_address",
				"customer_primary_contact",
				"mobile_no",
				"email_id",
			],
			as_dict=True,
		)
		if customer_name
		else None
	) or frappe._dict()
	address = (
		frappe.db.get_value(
			"Address",
			customer.primary_address,
			["address_line1", "address_line2", "city", "state", "country", "pincode"],
			as_dict=True,
		)
		if customer.primary_address
		else None
	) or frappe._dict()
	contact = (
		frappe.db.get_value(
			"Contact",
			customer.customer_primary_contact,
			["first_name", "last_name", "phone", "mobile_no", "email_id"],
			as_dict=True,
		)
		if customer.customer_primary_contact
		else None
	) or frappe._dict()
	return {
		"account": _text(customer_name),
		"name": _text(customer.customer_name) or _text(customer_name),
		"address": _join_nonempty(
			address.address_line1,
			address.address_line2,
			address.city,
			address.state,
			address.country,
			address.pincode,
		),
		"tax_id": _text(customer.tax_id),
		"contact_person": _join_nonempty(contact.first_name, contact.last_name),
		"phone": _text(contact.phone) or _text(customer.mobile_no),
		"mobile": _text(contact.mobile_no) or _text(customer.mobile_no),
		"email": _text(contact.email_id) or _text(customer.email_id),
	}


def build_job_card_snapshot(customer_name, vehicle_name):
	"""Build serializable customer and vehicle values for a Repair Job snapshot."""
	return {
		"captured_at": str(frappe.utils.now_datetime()),
		"customer": _customer_values(customer_name),
		"vehicle": _vehicle_values(vehicle_name),
	}


def _parse_snapshot(value):
	if not value:
		return {}
	try:
		parsed = json.loads(value) if isinstance(value, str) else value
	except (TypeError, ValueError):
		return {}
	return parsed if isinstance(parsed, dict) else {}


def _damage_markers(walkaround_name):
	if not walkaround_name or not frappe.db.exists("Walkaround Inspection", walkaround_name):
		return []
	marks = frappe.get_all(
		"Vehicle Damage Mark",
		filters={"parent": walkaround_name, "parenttype": "Walkaround Inspection"},
		fields=["damage_area", "damage_type", "severity", "description"],
		order_by="idx asc",
	)
	area_counts = {}
	markers = []
	for number, mark in enumerate(marks, start=1):
		area = _text(mark.damage_area) or "Other"
		count = area_counts.get(area, 0)
		area_counts[area] = count + 1
		left, top = _DAMAGE_MARKER_POSITIONS.get(area, _DAMAGE_MARKER_POSITIONS["Other"])
		left += (count % 3 - 1) * 6
		top += (count // 3) * 7
		markers.append(
			{
				"number": number,
				"area": area,
				"damage_type": _text(mark.damage_type),
				"severity": _text(mark.severity),
				"description": _text(mark.description),
				"left": max(7, min(93, left)),
				"top": max(7, min(93, top)),
			}
		)
	return markers


def get_job_card_context(doc):
	"""Return permission-scoped data for the Repair Job Job Card template."""
	snapshot = _parse_snapshot(getattr(doc, "job_card_snapshot", None))
	live_customer = _customer_values(getattr(doc, "customer", None))
	live_vehicle = _vehicle_values(getattr(doc, "customer_vehicle", None))
	snapshot_customer = snapshot.get("customer") or {}
	snapshot_vehicle = snapshot.get("vehicle") or {}
	customer = {**live_customer, **{key: value for key, value in snapshot_customer.items() if value}}
	vehicle = {**live_vehicle, **{key: value for key, value in snapshot_vehicle.items() if value}}
	return {
		"customer": customer,
		"vehicle": vehicle,
		"received_on": snapshot.get("captured_at") or _text(getattr(doc, "creation", None)),
		"terms": frappe.db.get_single_value("Auto Service Settings", "job_card_terms") or "",
		"diagram_url": PUBLIC_PRINT_LOGO,
		"damage_markers": _damage_markers(getattr(doc, "walkaround_inspection", None)),
	}


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
	logo = resolve_logo_url(
		company.company_logo,
		website.app_logo,
		website.banner_image,
		frappe.utils.get_url(),
	)
	# Private file logos are not readable by role-scoped Desk print requests.
	# Use the app-owned public mark so PDFs never render a broken image for
	# Service Advisor and other non-System-Manager roles.
	if logo and "/private/files/" in logo:
		logo = PUBLIC_PRINT_LOGO
	return frappe._dict(
		company=company,
		company_name=company.company_name or company_name or "Auto Service Workshop",
		logo=logo,
		contact=" · ".join(value for value in (company.phone_no, company.email, company.website) if value),
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
	options = (
		html
		or f'{{% set _doc = doc %}}{{% include "templates/includes/auto_service_print/{template}.html" %}}'
	)
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
		frappe.db.set_value("Print Format", doc.name, "print_format_builder_beta", 0, update_modified=False)


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


def _migrate_sales_order_builder_format():
	"""Preserve custom Sales Order builder edits under the Proforma Invoice name."""
	legacy = "DMS Editable - Sales Order"
	current = "DMS Editable - Proforma Invoice"
	if not frappe.db.exists("Print Format", legacy) or frappe.db.exists("Print Format", current):
		return
	try:
		frappe.rename_doc("Print Format", legacy, current, force=True)
	except Exception:
		# A locked or customized installation can complete the rename manually;
		# keeping the legacy format is safer than replacing its content.
		frappe.log_error(frappe.get_traceback(), "Unable to rename Sales Order print format")


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


def _ensure_print_heading(name="Proforma Invoice"):
	if not frappe.db.exists("Print Heading", name):
		frappe.get_doc(
			{
				"doctype": "Print Heading",
				"print_heading": name,
				"description": "DMS Sales Order print heading",
			}
		).insert(ignore_permissions=True)


def ensure_print_branding():
	"""Idempotently create app-owned formats, heading, and branded letterheads."""
	_migrate_sales_order_builder_format()
	_ensure_print_heading()
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
