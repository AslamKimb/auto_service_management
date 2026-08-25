"""Customer LPO intake, authorization, and consolidated billing workflow."""

from __future__ import annotations

import csv
import io

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from auto_service_management.auto_service_management.doctype.customer_lpo_vehicle.customer_lpo_vehicle import (
	normalize_registration_number,
)

CSV_COLUMNS = (
	"registration_number",
	"customer_vehicle",
	"requested_work",
	"planned_date",
	"allocated_ceiling",
	"remarks",
)
CSV_REQUIRED_COLUMNS = {"registration_number"}
ACTIVE_DOCSTATUSES = (0, 1)


def _get_lpo(name: str, permission: str = "read"):
	lpo = frappe.get_doc("Customer LPO", name)
	lpo.check_permission(permission)
	return lpo


def _require_submitted(lpo):
	if lpo.docstatus != 1:
		frappe.throw(_("Customer LPO {0} must be submitted before this action.").format(lpo.name))


def _parse_json(value, label):
	if isinstance(value, str):
		value = frappe.parse_json(value)
	if not isinstance(value, (list, tuple)):
		frappe.throw(_("{0} must be a list.").format(label))
	return list(value)


def _normalise_row(row, index: int):
	if not isinstance(row, dict):
		frappe.throw(_("Vehicle row {0} must be an object.").format(index))
	values = {str(key).strip(): value for key, value in row.items() if str(key).strip()}
	unknown = sorted(set(values) - set(CSV_COLUMNS))
	if unknown:
		frappe.throw(_("Vehicle row {0} has unsupported columns: {1}.").format(index, ", ".join(unknown)))
	registration = normalize_registration_number(values.get("registration_number"))
	if not registration:
		frappe.throw(_("Vehicle row {0} requires registration_number.").format(index))
	allocated_ceiling = values.get("allocated_ceiling")
	if allocated_ceiling not in (None, ""):
		try:
			allocated_ceiling = flt(allocated_ceiling)
		except (TypeError, ValueError):
			frappe.throw(_("Vehicle row {0} has an invalid allocated_ceiling.").format(index))
		if allocated_ceiling < 0:
			frappe.throw(_("Vehicle row {0} cannot have a negative allocated_ceiling.").format(index))
	else:
		allocated_ceiling = None
	planned_date = values.get("planned_date") or None
	if planned_date:
		try:
			planned_date = getdate(planned_date)
		except Exception:
			frappe.throw(_("Vehicle row {0} has an invalid planned_date.").format(index))
	return {
		"registration_number": registration,
		"customer_vehicle": str(values.get("customer_vehicle") or "").strip() or None,
		"requested_work": str(values.get("requested_work") or "").strip() or None,
		"planned_date": planned_date,
		"allocated_ceiling": allocated_ceiling,
		"remarks": str(values.get("remarks") or "").strip() or None,
	}


def _rows_from_csv(csv_text: str):
	if not str(csv_text or "").strip():
		frappe.throw(_("CSV content is required."))
	reader = csv.DictReader(io.StringIO(csv_text))
	columns = [str(column or "").strip() for column in (reader.fieldnames or [])]
	if set(columns) != set(CSV_COLUMNS):
		missing = sorted(set(CSV_COLUMNS) - set(columns))
		unknown = sorted(set(columns) - set(CSV_COLUMNS))
		problems = []
		if missing:
			problems.append(_("missing {0}").format(", ".join(missing)))
		if unknown:
			problems.append(_("unsupported {0}").format(", ".join(unknown)))
		frappe.throw(_("CSV columns are invalid: {0}.").format("; ".join(problems)))
	return [_normalise_row(row, index) for index, row in enumerate(reader, start=2)]


def _get_csv_text(csv_text=None, file_url=None):
	if csv_text is not None:
		return csv_text
	if not file_url:
		return None
	file_doc = frappe.get_doc("File", {"file_url": file_url})
	file_doc.check_permission("read")
	content = file_doc.get_content()
	try:
		return content.decode("utf-8") if isinstance(content, bytes) else str(content)
	except UnicodeDecodeError:
		frappe.throw(_("Vehicle CSV must be UTF-8 encoded."))


def _normalise_rows(rows=None, csv_text=None, file_url=None):
	csv_text = _get_csv_text(csv_text, file_url)
	if csv_text is not None:
		return _rows_from_csv(csv_text)
	rows = _parse_json(rows or [], _("Vehicle rows"))
	return [_normalise_row(row, index) for index, row in enumerate(rows, start=1)]


def _resolve_vehicle(customer: str, registration_number: str, requested_name: str | None = None):
	if requested_name:
		vehicle = frappe.db.get_value(
			"Customer Vehicle",
			requested_name,
			["name", "customer", "registration_number"],
			as_dict=True,
		)
		if not vehicle:
			return None, "Not Found"
		if vehicle.customer != customer:
			frappe.throw(
				_("Customer Vehicle {0} does not belong to Customer {1}.").format(
					requested_name, customer
				)
			)
		if registration_number and vehicle.registration_number != registration_number:
			frappe.throw(
				_("Customer Vehicle {0} registration does not match {1}.").format(
					requested_name, registration_number
				)
			)
		return vehicle.name, "Resolved"
	vehicles = frappe.get_all(
		"Customer Vehicle",
		filters={"customer": customer, "registration_number": registration_number},
		pluck="name",
		limit_page_length=0,
	)
	if len(vehicles) == 1:
		return vehicles[0], "Resolved"
	if len(vehicles) > 1:
		return None, "Ambiguous"
	return None, "Not Found"


@frappe.whitelist(methods=["GET"])
def preview_vehicle_csv(lpo_name: str, csv_text: str | None = None, file_url: str | None = None, rows=None) -> dict:
	"""Validate CSV/JSON rows without mutating the Customer LPO."""
	lpo = _get_lpo(lpo_name, "read")
	values = _normalise_rows(rows, csv_text, file_url)
	seen = set()
	result = []
	for row in values:
		registration = row["registration_number"]
		duplicate = registration in seen
		seen.add(registration)
		vehicle, status = _resolve_vehicle(lpo.customer, registration, row.get("customer_vehicle"))
		result.append({**row, "customer_vehicle": vehicle or row.get("customer_vehicle"), "resolution": status, "duplicate": duplicate})
	return {"columns": list(CSV_COLUMNS), "count": len(result), "rows": result}


@frappe.whitelist(methods=["POST"])
def import_vehicle_csv(lpo_name: str, csv_text: str | None = None, file_url: str | None = None, rows=None) -> dict:
	"""Append validated vehicle rows atomically to a draft Customer LPO."""
	lpo = _get_lpo(lpo_name, "write")
	if lpo.docstatus != 0:
		frappe.throw(_("Vehicle rows can only be imported into a draft Customer LPO."))
	values = _normalise_rows(rows, csv_text, file_url)
	seen = {row.registration_number for row in lpo.get("vehicle_rows") or []}
	for row in values:
		if row["registration_number"] in seen:
			frappe.throw(
				_("Registration number {0} is already present on Customer LPO {1}.").format(
					row["registration_number"], lpo.name
				)
			)
		seen.add(row["registration_number"])
		vehicle, status = _resolve_vehicle(lpo.customer, row["registration_number"], row.get("customer_vehicle"))
		if status == "Ambiguous":
			frappe.throw(
				_("Registration number {0} matches more than one Customer Vehicle.").format(
					row["registration_number"]
				)
			)
		row["customer_vehicle"] = vehicle or row.get("customer_vehicle")
		lpo.append("vehicle_rows", row)
	lpo.save()
	return {"lpo": lpo.name, "imported": len(values), "vehicle_count": len(lpo.get("vehicle_rows") or [])}


@frappe.whitelist(methods=["POST"])
def resolve_vehicle_rows(lpo_name: str, row_names=None, create_confirmed: bool = False) -> dict:
	"""Resolve registration numbers against the customer's native vehicle master."""
	lpo = _get_lpo(lpo_name, "write")
	if lpo.docstatus != 0:
		frappe.throw(_("Vehicle rows can only be resolved on a draft Customer LPO."))
	create_confirmed = cint(create_confirmed)
	requested = set(str(value) for value in (_parse_json(row_names, _("Vehicle row names")) if row_names else []))
	resolved = unresolved = 0
	for row in lpo.get("vehicle_rows") or []:
		if requested and row.name not in requested:
			continue
		vehicle, status = _resolve_vehicle(lpo.customer, row.registration_number, row.customer_vehicle)
		if status == "Resolved":
			row.customer_vehicle = vehicle
			row.status = "Resolved"
			resolved += 1
		elif create_confirmed and status == "Not Found":
			frappe.has_permission("Customer Vehicle", "create", throw=True)
			new_vehicle = frappe.get_doc(
				{
					"doctype": "Customer Vehicle",
					"customer": lpo.customer,
					"registration_number": row.registration_number,
				}
			).insert()
			row.customer_vehicle = new_vehicle.name
			row.status = "Resolved"
			resolved += 1
		else:
			unresolved += 1
	lpo.save()
	return {"lpo": lpo.name, "resolved": resolved, "unresolved": unresolved}


def _campaign_name(lpo):
	return lpo.lpo_number or lpo.name


@frappe.whitelist(methods=["POST"])
def create_campaign_and_repair_jobs(lpo_name: str) -> dict:
	"""Create one Fleet Service Campaign and one Repair Job per LPO vehicle."""
	lpo = _get_lpo(lpo_name, "write")
	_require_submitted(lpo)
	if not lpo.get("vehicle_rows"):
		frappe.throw(_("At least one vehicle is required before creating Repair Jobs."))
	for row in lpo.get("vehicle_rows") or []:
		if not row.customer_vehicle:
			frappe.throw(
				_("Vehicle row {0} must resolve to a Customer Vehicle before job creation.").format(row.idx)
			)
	campaign_name = lpo.get("fleet_service_campaign")
	if campaign_name:
		campaign = frappe.get_doc("Fleet Service Campaign", campaign_name)
		campaign.check_permission("write")
		if campaign.customer_lpo and campaign.customer_lpo != lpo.name:
			frappe.throw(_("Fleet Service Campaign {0} is already linked to Customer LPO {1}.").format(campaign.name, campaign.customer_lpo))
	else:
		campaign = frappe.get_doc(
			{
				"doctype": "Fleet Service Campaign",
				"campaign_name": _campaign_name(lpo),
				"customer": lpo.customer,
				"campaign_start": lpo.issue_date or today(),
				"campaign_end": lpo.expiry_date,
				"status": "Draft",
				"description": lpo.work_instruction,
				"customer_lpo": lpo.name,
			}
		)
		campaign.insert()
		lpo.db_set("fleet_service_campaign", campaign.name, update_modified=False)
	for row in lpo.get("vehicle_rows") or []:
		if row.repair_job:
			job = frappe.get_doc("Repair Job", row.repair_job)
			if job.customer != lpo.customer or job.customer_vehicle != row.customer_vehicle:
				frappe.throw(_("Repair Job {0} does not match its LPO vehicle.").format(job.name))
			if job.get("customer_lpo") and job.customer_lpo != lpo.name:
				frappe.throw(_("Repair Job {0} is already linked to Customer LPO {1}.").format(job.name, job.customer_lpo))
			if job.get("fleet_service_campaign") and job.fleet_service_campaign != campaign.name:
				frappe.throw(_("Repair Job {0} does not belong to Fleet Service Campaign {1}.").format(job.name, campaign.name))
			continue
		job = frappe.get_doc(
			{
				"doctype": "Repair Job",
				"customer": lpo.customer,
				"customer_vehicle": row.customer_vehicle,
				"odometer_in": 0,
				"customer_concern": row.requested_work or lpo.work_instruction or _("LPO requested work"),
				"promised_date": row.planned_date,
				"fleet_service_campaign": campaign.name,
				"customer_lpo": lpo.name,
				"job_status": "Draft",
			}
		)
		job.insert()
		row.repair_job = job.name
		row.status = "Job Created"
	if not lpo.get("fleet_service_campaign"):
		lpo.fleet_service_campaign = campaign.name
	lpo.save()
	return {"lpo": lpo.name, "fleet_service_campaign": campaign.name, "repair_jobs": [row.repair_job for row in lpo.vehicle_rows]}


@frappe.whitelist(methods=["GET"])
def get_lpo_summary(lpo_name: str) -> dict:
	lpo = _get_lpo(lpo_name, "read")
	vehicles = []
	for row in lpo.get("vehicle_rows") or []:
		job = None
		if row.repair_job and frappe.has_permission("Repair Job", "read"):
			jobs = frappe.get_list(
				"Repair Job",
				filters={"name": row.repair_job},
				fields=["name", "job_status", "total_amount", "customer_vehicle"],
				limit_page_length=1,
			)
			job = jobs[0] if jobs else None
		vehicles.append({"name": row.name, "registration_number": row.registration_number, "customer_vehicle": row.customer_vehicle, "repair_job": job or row.repair_job, "status": row.status})
	invoices = frappe.get_list(
		"Sales Invoice",
		filters={"customer_lpo": lpo.name},
		fields=["name", "docstatus", "status", "posting_date", "grand_total", "rounded_total", "net_total", "outstanding_amount"],
		order_by="posting_date desc, creation desc",
		limit_page_length=0,
	) if frappe.db.exists("DocType", "Sales Invoice") and frappe.has_permission("Sales Invoice", "read") else []
	orders = frappe.get_list(
		"Sales Order",
		filters={"customer_lpo": lpo.name},
		fields=["name", "docstatus", "status", "transaction_date", "grand_total", "per_billed"],
		order_by="transaction_date desc, creation desc",
		limit_page_length=0,
	) if frappe.db.exists("DocType", "Sales Order") and frappe.has_permission("Sales Order", "read") else []
	return {
		"lpo": lpo.name,
		"status": lpo.status,
		"authorized_amount": _effective_authorized_amount(lpo),
		"ceiling_basis": lpo.ceiling_basis,
		"vehicles": vehicles,
		"sales_orders": orders,
		"sales_invoices": invoices,
		"used_amount": sum(_invoice_amount(row, lpo.ceiling_basis) for row in invoices if row.docstatus == 1),
	}


@frappe.whitelist(methods=["POST"])
def make_sales_order(lpo_name: str, target_doc: str | dict | None = None, component_refs=None):
	lpo = _get_lpo(lpo_name, "read")
	_require_submitted(lpo)
	campaign = _require_campaign(lpo)
	frappe.has_permission("Sales Order", "create", throw=True)
	_assert_one_active_document("Sales Order", lpo.name, target_doc)
	from auto_service_management.auto_service_management.integration.erpnext.component_mapping import (
		map_campaign_sales_order,
	)

	target = map_campaign_sales_order(
		campaign.name,
		target_doc=target_doc,
		component_refs=component_refs,
		permission="read",
	)
	target.customer_lpo = lpo.name
	return target


@frappe.whitelist(methods=["POST"])
def make_sales_invoice(lpo_name: str, target_doc: str | dict | None = None, component_refs=None):
	lpo = _get_lpo(lpo_name, "read")
	_require_submitted(lpo)
	campaign = _require_campaign(lpo)
	frappe.has_permission("Sales Invoice", "create", throw=True)
	_assert_one_active_document("Sales Invoice", lpo.name, target_doc)
	active_orders = frappe.get_list(
		"Sales Order",
		filters={"customer_lpo": lpo.name, "docstatus": 1},
		fields=["name"],
		order_by="creation desc",
		limit_page_length=1,
	)
	if active_orders:
		from auto_service_management.auto_service_management.integration.sales_order_mapping import (
			make_sales_invoice as map_sales_order_invoice,
		)

		target = map_sales_order_invoice(active_orders[0].get("name"), target_doc=target_doc)
	else:
		from auto_service_management.auto_service_management.integration.erpnext.component_mapping import (
			map_campaign_sales_invoice,
		)

		target = map_campaign_sales_invoice(
			campaign.name,
			target_doc=target_doc,
			component_refs=component_refs,
			permission="read",
		)
	target.customer_lpo = lpo.name
	return target


def validate_lpo_sales_document(doc):
	"""Validate LPO identity and authorization before ERPNext totals are posted."""
	lpo_name = doc.get("customer_lpo")
	if not lpo_name:
		return
	lpo = _get_lpo(lpo_name, "read")
	_require_submitted(lpo)
	if lpo.status in {"Expired", "Completed", "Cancelled", "Exhausted"}:
		frappe.throw(_("Customer LPO {0} is {1} and cannot receive new billing.").format(lpo.name, lpo.status))
	if doc.get("customer") and doc.customer != lpo.customer:
		frappe.throw(_("Sales document customer must match Customer LPO {0}.").format(lpo.name))
	if doc.get("company") and lpo.company and doc.company != lpo.company:
		frappe.throw(_("Sales document company must match Customer LPO {0}.").format(lpo.name))
	if doc.get("currency") and lpo.currency and doc.currency != lpo.currency:
		frappe.throw(_("Sales document currency must match Customer LPO {0}.").format(lpo.name))
	if lpo.get("fleet_service_campaign") and doc.get("fleet_service_campaign") != lpo.fleet_service_campaign:
		frappe.throw(_("Sales document Fleet Service Campaign must match Customer LPO {0}.").format(lpo.name))
	if getattr(doc, "docstatus", 0) in ACTIVE_DOCSTATUSES:
		_assert_one_active_document(doc.doctype, lpo.name, {"name": doc.name} if doc.name else None)
	if doc.doctype == "Sales Order":
		_validate_lpo_order_ceiling(doc, lpo)


def _validate_lpo_order_ceiling(doc, lpo):
	used = 0
	for row in frappe.get_all(
		"Sales Invoice",
		filters={"customer_lpo": lpo.name, "docstatus": 1},
		fields=["net_total", "grand_total", "rounded_total", "disable_rounded_total"],
		limit_page_length=0,
	):
		used += _invoice_amount(row, lpo.ceiling_basis)
	proposed = _invoice_amount(doc, lpo.ceiling_basis)
	if used + proposed > _effective_authorized_amount(lpo, permission_scoped=False) + 0.0001:
		frappe.throw(
			_("Customer LPO {0} ceiling exceeded by Sales Order: {1} proposed against {2} remaining. Submit an LPO amendment first.").format(
				lpo.name,
				proposed,
				max(_effective_authorized_amount(lpo, permission_scoped=False) - used, 0),
			)
		)


def validate_lpo_sales_invoice(doc):
	"""Compatibility wrapper for integrations and tests."""
	validate_lpo_invoice_ceiling(doc)


@frappe.whitelist(methods=["POST"])
def close_lpo(lpo_name: str):
	lpo = _get_lpo(lpo_name, "write")
	_require_submitted(lpo)
	open_jobs = []
	for row in lpo.get("vehicle_rows") or []:
		if row.repair_job:
			status = frappe.db.get_value("Repair Job", row.repair_job, "job_status")
			if status not in {"Closed", "Cancelled"}:
				open_jobs.append(f"{row.registration_number} ({status or 'Unknown'})")
	if open_jobs:
		frappe.throw(_("All LPO vehicle jobs must be closed or cancelled: {0}.").format(", ".join(open_jobs)))
	lpo.status = "Completed"
	lpo.closed_on = frappe.utils.now_datetime()
	lpo.closed_by = frappe.session.user
	lpo.save()
	return lpo.name


def _require_campaign(lpo):
	if not lpo.get("fleet_service_campaign"):
		frappe.throw(_("Create the Fleet Service Campaign and Repair Jobs before billing."))
	campaign = frappe.get_doc("Fleet Service Campaign", lpo.fleet_service_campaign)
	campaign.check_permission("read")
	if campaign.customer != lpo.customer:
		frappe.throw(_("Fleet Service Campaign customer must match the Customer LPO."))
	return campaign


def _set_if_field(doc, fieldname, value):
	if doc.meta.has_field(fieldname):
		doc.set(fieldname, value)


def _assert_one_active_document(doctype, lpo_name, target_doc=None):
	target_name = None
	if isinstance(target_doc, str):
		target_name = target_doc
	elif isinstance(target_doc, dict):
		target_name = target_doc.get("name")
	filters = {"customer_lpo": lpo_name, "docstatus": ["in", ACTIVE_DOCSTATUSES]}
	if target_name:
		filters["name"] = ["!=", target_name]
	active = frappe.get_list(
		doctype,
		filters=filters,
		pluck="name",
		limit_page_length=0,
	)
	if active:
		frappe.throw(_("Customer LPO {0} already has an active {1}: {2}.").format(lpo_name, doctype, ", ".join(active)))


def _effective_authorized_amount(lpo, *, permission_scoped=True):
	amount = flt(lpo.authorized_amount)
	if frappe.db.exists("DocType", "Customer LPO Amendment"):
		query = frappe.get_list if permission_scoped else frappe.get_all
		for amendment in query(
			"Customer LPO Amendment",
			filters={"customer_lpo": lpo.name, "docstatus": 1},
			fields=["amount_increase"],
			limit_page_length=0,
		):
			amount += flt(amendment.amount_increase)
	return amount


def _invoice_amount(invoice, basis):
	if basis == "Tax Exclusive":
		return flt(invoice.net_total)
	if not getattr(invoice, "disable_rounded_total", False):
		return flt(invoice.rounded_total)
	return flt(invoice.grand_total)


def get_lpo_invoice_amount(doc, ceiling_basis=None):
	"""Return the ERPNext-authoritative amount used against an LPO ceiling."""
	if ceiling_basis == "Tax Exclusive":
		return flt(doc.net_total)
	if not doc.get("disable_rounded_total"):
		return flt(doc.rounded_total)
	return flt(doc.grand_total)


def validate_lpo_invoice_ceiling(doc):
	"""Block invoice validation when submitted LPO authorization is exceeded."""
	lpo_name = doc.get("customer_lpo")
	if not lpo_name:
		return
	lpo = _get_lpo(lpo_name, "read")
	_require_submitted(lpo)
	used = 0
	for row in frappe.get_all(
		"Sales Invoice",
		filters={"customer_lpo": lpo.name, "docstatus": 1, "name": ["!=", doc.name]},
		fields=["name", "net_total", "grand_total", "rounded_total", "disable_rounded_total"],
		limit_page_length=0,
	):
		used += _invoice_amount(row, lpo.ceiling_basis)
	current = get_lpo_invoice_amount(doc, lpo.ceiling_basis)
	authorized = _effective_authorized_amount(lpo, permission_scoped=False)
	if used + current > authorized + 0.0001:
		frappe.throw(
			_("Customer LPO {0} ceiling exceeded: {1} used of {2} authorized ({3}). Submit an LPO amendment before invoicing.").format(
				lpo.name,
				used + current,
				authorized,
				lpo.ceiling_basis,
			)
		)


def sync_lpo_from_sales_document(doc):
	"""Keep the LPO aggregate links authoritative after ERPNext saves a document."""
	lpo_name = doc.get("customer_lpo")
	if not lpo_name or not frappe.db.exists("Customer LPO", lpo_name):
		return
	lpo = frappe.get_doc("Customer LPO", lpo_name)
	if doc.doctype == "Sales Order":
		_set_if_field(lpo, "sales_order", None if doc.docstatus == 2 else doc.name)
	elif doc.doctype == "Sales Invoice":
		_set_if_field(lpo, "sales_invoice", None if doc.docstatus == 2 else doc.name)
	lpo.save(ignore_permissions=True)
