# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

"""Integration tests for Phase 2-5 DocType controllers.

These tests exercise the server-side validation, workflow transitions,
and ERPNext integration adapters with mocked external calls.
"""

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	COMPONENT_TABLE_BY_TYPE,
	get_repair_job_services,
)
from auto_service_management.auto_service_management.workflow_compatibility import (
	sync_repair_job_related_tables,
)

TEST_COMPONENT_ITEM_CODE = "TEST-WORKSHOP-PART-001"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_erpnext_basics():
	"""Create minimal ERPNext setup data if missing."""
	if not frappe.db.exists("Customer Group", "All Customer Groups"):
		frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": "All Customer Groups",
				"is_group": 1,
				"parent_customer_group": "",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("UOM", "Nos"):
		frappe.get_doc({"doctype": "UOM", "uom_name": "Nos", "enabled": 1}).insert(ignore_permissions=True)
	if not frappe.db.exists("Item Group", "All Item Groups"):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "All Item Groups",
				"is_group": 1,
				"parent_item_group": "",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Item Group", "Auto Service Parts"):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "Auto Service Parts",
				"is_group": 0,
				"parent_item_group": "All Item Groups",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Item", TEST_COMPONENT_ITEM_CODE):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": TEST_COMPONENT_ITEM_CODE,
				"item_name": "Test Workshop Part",
				"item_group": "Auto Service Parts",
				"stock_uom": "Nos",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Customer Group", {"is_group": 0, "name": "Commercial"}):
		frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": "Commercial",
				"is_group": 0,
				"parent_customer_group": "All Customer Groups",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Territory", "All Territories"):
		frappe.get_doc(
			{
				"doctype": "Territory",
				"territory_name": "All Territories",
				"is_group": 1,
				"parent_territory": "",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Territory", {"is_group": 0, "name": "Uganda"}):
		frappe.get_doc(
			{
				"doctype": "Territory",
				"territory_name": "Uganda",
				"is_group": 0,
				"parent_territory": "All Territories",
			}
		).insert(ignore_permissions=True)


def _get_or_create_customer():
	_ensure_erpnext_basics()
	name = frappe.db.get_value("Customer", {"customer_name": "Test Workshop Customer"}, "name")
	if not name:
		doc = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "Test Workshop Customer",
				"customer_group": "Commercial",
				"territory": "Uganda",
			}
		)
		doc.insert(ignore_permissions=True)
		name = doc.name
	return name


def _create_test_vehicle(customer=None):
	"""Create or reuse a test Customer Vehicle."""
	if not customer:
		customer = _get_or_create_customer()
	existing = frappe.db.get_value("Customer Vehicle", {"vin_chassis_number": "TESTVIN-PH7"}, "name")
	if existing:
		return existing
	doc = frappe.get_doc(
		{
			"doctype": "Customer Vehicle",
			"customer": customer,
			"registration_number": "TEST-PH7-001",
			"vin_chassis_number": "TESTVIN-PH7",
			"engine_number": "ENG-PH7-001",
			"make": "Toyota",
			"model": "Hilux",
			"year_of_manufacture": 2022,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _create_repair_job(customer=None, vehicle=None, fuel_level="1/2"):
	"""Create a Draft Repair Job."""
	if not vehicle:
		if not customer:
			customer = _get_or_create_customer()
		vehicle = _create_test_vehicle(customer)
	if not customer:
		customer = frappe.db.get_value("Customer Vehicle", vehicle, "customer")
	doc = frappe.get_doc(
		{
			"doctype": "Repair Job",
			"customer": customer,
			"customer_vehicle": vehicle,
			"odometer_in": 84521,
			"fuel_level": fuel_level,
			"customer_concern": "Battery warning and brake noise",
			"priority": "Normal",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _append_pending_labour_line(job, description="Workshop labour", rate=120000):
	service = _create_job_service(job, description, status="Pending Approval")
	line = _append_service_component(
		service,
		service_type="Labour",
		description=description,
		quantity=1,
		rate=rate,
	)
	job.reload()
	return line.name


def _create_job_service(job, service_name="Workshop service", status="Pending Approval"):
	service = frappe.get_doc(
		{
			"doctype": "Repair Job Service",
			"repair_job": job.name,
			"customer": job.customer,
			"customer_vehicle": job.customer_vehicle,
			"diagnosis_report": job.diagnosis_report,
			"service_name": service_name,
			"status": status,
			"billable": 1,
			"currency": job.currency,
		}
	)
	service.insert(ignore_permissions=True)
	service._desired_status = status
	if status and getattr(service, "status", None) != status:
		frappe.db.set_value("Repair Job Service", service.name, "status", status, update_modified=False)
		service.reload()
	return service


def _append_service_component(
	service,
	*,
	service_type="Labour",
	description="Workshop component",
	item_code=None,
	quantity=1,
	rate=120000,
	assigned_to=None,
):
	table = COMPONENT_TABLE_BY_TYPE[service_type]["fieldname"]
	row = {
		"description": description,
		"item_code": item_code,
	}
	if service_type in {"Part", "Consumable"}:
		row["item_code"] = item_code or TEST_COMPONENT_ITEM_CODE
		row["quantity"] = quantity
		row["rate"] = rate
	if service_type == "Labour":
		row["estimated_hours"] = quantity
		row["hours"] = quantity
		row["billing_hours"] = quantity
		row["billing_rate"] = rate
		row["assigned_to"] = assigned_to
	service.append(table, row)
	service.save(ignore_permissions=True)
	service.reload()
	desired_status = getattr(service, "_desired_status", None)
	if desired_status and getattr(service, "status", None) != desired_status:
		frappe.db.set_value("Repair Job Service", service.name, "status", desired_status, update_modified=False)
		service.reload()
	return service.get(table)[-1]


def _get_job_components(job_name):
	rows = []
	for component_type, definition in COMPONENT_TABLE_BY_TYPE.items():
		price_field = "billing_amount" if component_type == "Labour" else "amount"
		component_rows = frappe.get_all(
			definition["doctype"],
			filters={"repair_job": job_name},
			fields=["name", "description", "status", price_field],
			order_by="creation asc, idx asc",
		)
		for row in component_rows:
			row.service_type = component_type
			row.service_description = row.description
			if not hasattr(row, "amount"):
				row.amount = getattr(row, price_field, None)
			rows.append(row)
	return rows


def _insert_walkaround(job_name, vehicle, fuel_level="1/2"):
	return frappe.get_doc(
		{
			"doctype": "Walkaround Inspection",
			"repair_job": job_name,
			"customer_vehicle": vehicle,
			"inspection_date": frappe.utils.now_datetime(),
			"inspected_by": "Administrator",
			"fuel_level": fuel_level,
		}
	).insert(ignore_permissions=True)


def _insert_diagnosis(job_name, vehicle, complaint="Battery warning and brake noise", road_test_required=0):
	return frappe.get_doc(
		{
			"doctype": "Diagnosis Report",
			"repair_job": job_name,
			"customer_vehicle": vehicle,
			"diagnosis_date": frappe.utils.now_datetime(),
			"diagnosed_by": "Administrator",
			"customer_complaint": complaint,
			"findings": "Electrical fault isolated",
			"recommendations": "Replace faulty component",
			"road_test_required": road_test_required,
			"status": "Submitted",
		}
	).insert(ignore_permissions=True)


def _insert_authorization(job_name, amount=500000):
	return frappe.get_doc(
		{
			"doctype": "Customer Authorization",
			"repair_job": job_name,
			"approved_amount": amount,
			"authorized_by_user": "Administrator",
			"authorization_date": frappe.utils.now_datetime(),
		}
	).insert(ignore_permissions=True)


def _insert_quality_check(job_name, vehicle, status="Passed"):
	return frappe.get_doc(
		{
			"doctype": "Quality Check",
			"repair_job": job_name,
			"customer_vehicle": vehicle,
			"qc_date": frappe.utils.now_datetime(),
			"checked_by": "Administrator",
			"completion_check": 1,
			"fitment_check": 1,
			"fluid_levels_check": 1,
			"warning_lights_clear": 1,
			"cleanliness_check": 1,
			"road_test_check": 1,
			"status": status,
		}
	).insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Walkaround Inspection Tests
# ---------------------------------------------------------------------------


class TestWalkaroundInspection(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def test_walkaround_requires_checked_in_or_diagnosis(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		# Job is in Draft — walkaround should be blocked
		wi = frappe.get_doc(
			{
				"doctype": "Walkaround Inspection",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"inspection_date": frappe.utils.now_datetime(),
				"inspected_by": "Administrator",
			}
		)
		self.assertRaises(frappe.ValidationError, wi.insert)

	def test_walkaround_allowed_after_check_in(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()

		wi = frappe.get_doc(
			{
				"doctype": "Walkaround Inspection",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"inspection_date": frappe.utils.now_datetime(),
				"inspected_by": "Administrator",
			}
		)
		wi.insert(ignore_permissions=True)
		self.assertTrue(wi.name)
		job.reload()
		self.assertEqual(job.job_status, "Assessment")
		self.assertEqual(job.walkaround_inspection, wi.name)

	def test_walkaround_duplicate_for_same_job_is_blocked(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)

		duplicate = frappe.get_doc(
			{
				"doctype": "Walkaround Inspection",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"inspection_date": frappe.utils.now_datetime(),
				"inspected_by": "Administrator",
			}
		)
		self.assertRaises(frappe.ValidationError, duplicate.insert)


# ---------------------------------------------------------------------------
# Customer Authorization Tests
# ---------------------------------------------------------------------------


class TestCustomerAuthorization(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def test_authorization_requires_estimate_prepared_state(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		auth = frappe.get_doc(
			{
				"doctype": "Customer Authorization",
				"repair_job": job_name,
				"approved_amount": 500000,
				"authorized_by_user": "Administrator",
				"authorization_date": frappe.utils.now_datetime(),
			}
		)
		self.assertRaises(frappe.ValidationError, auth.insert)

	def test_authorization_approve_updates_job(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		# Walk to Awaiting Approval state
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		_insert_diagnosis(job_name, self.vehicle)
		_append_pending_labour_line(job, "Authorized labour")
		job = frappe.get_doc("Repair Job", job_name)
		job.request_authorization()

		auth = _insert_authorization(job_name)
		auth.approve()

		job = frappe.get_doc("Repair Job", job_name)
		self.assertEqual(job.customer_authorization, auth.name)
		self.assertEqual(job.job_status, "In Repair")

	def test_authorization_duplicate_for_same_job_is_blocked(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		_insert_diagnosis(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.request_authorization()
		_insert_authorization(job_name)

		duplicate = frappe.get_doc(
			{
				"doctype": "Customer Authorization",
				"repair_job": job_name,
				"approved_amount": 600000,
				"authorized_by_user": "Administrator",
				"authorization_date": frappe.utils.now_datetime(),
			}
		)
		self.assertRaises(frappe.ValidationError, duplicate.insert)


class TestDiagnosisReport(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def test_diagnosis_links_back_to_job(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()

		report = _insert_diagnosis(job_name, self.vehicle)
		job.reload()
		self.assertEqual(job.diagnosis_report, report.name)

	def test_diagnosis_duplicate_for_same_job_is_blocked(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job_name, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		job.start_diagnosis()
		_insert_diagnosis(job_name, self.vehicle)

		duplicate = frappe.get_doc(
			{
				"doctype": "Diagnosis Report",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"diagnosis_date": frappe.utils.now_datetime(),
				"diagnosed_by": "Administrator",
			}
		)
		self.assertRaises(frappe.ValidationError, duplicate.insert)


# ---------------------------------------------------------------------------
# Repair Job Override Tests
# ---------------------------------------------------------------------------


class TestRepairJobOverride(IntegrationTestCase):
	def test_approved_override_requires_approver(self):
		override = frappe.get_doc(
			{
				"doctype": "Repair Job Override",
				"override_type": "Credit Release",
				"status": "Approved",
			}
		)
		self.assertRaises(frappe.ValidationError, override.insert)


# ---------------------------------------------------------------------------
# Workshop Bay Tests
# ---------------------------------------------------------------------------


class TestWorkshopBay(IntegrationTestCase):
	def test_bay_maintenance_blocks_when_occupied(self):
		bay = frappe.get_doc(
			{
				"doctype": "Workshop Bay",
				"bay_name": "Test Bay",
				"status": "Available",
			}
		)
		bay.insert(ignore_permissions=True)
		# Mock occupied_count to return > 0
		with patch.object(type(bay), "occupied_count", return_value=2):
			bay.status = "Under Maintenance"
			self.assertRaises(frappe.ValidationError, bay.save)


# ---------------------------------------------------------------------------
# ERPNext Adapter Tests (mocked)
# ---------------------------------------------------------------------------


class TestERPNextAdapters(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def test_get_item_price_returns_zero_for_missing(self):
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			get_item_price,
		)

		with patch(
			"auto_service_management.auto_service_management.integration.erpnext.adapters.frappe"
		) as mock_frappe:
			mock_frappe.get_single.return_value = MagicMock(
				selling_price_list="Standard Selling", price_list="Standard Selling"
			)
			mock_frappe.get_all.return_value = []
			price = get_item_price("NONEXISTENT-ITEM")
			self.assertEqual(price, 0)

	def test_create_quotation_rejects_empty_lines(self):
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_quotation,
		)

		job = frappe.get_doc("Repair Job", _create_repair_job(self.customer, self.vehicle))
		with self.assertRaises(frappe.ValidationError):
			create_quotation(job)

	def test_create_material_request_rejects_no_parts(self):
		from auto_service_management.auto_service_management.integration.erpnext.adapters import (
			create_material_request,
		)

		job = frappe.get_doc("Repair Job", _create_repair_job(self.customer, self.vehicle))
		with self.assertRaises(frappe.ValidationError):
			create_material_request(job)


class TestPhase7HardeningIntegration(IntegrationTestCase):
	def setUp(self):
		self.customer = _get_or_create_customer()
		self.vehicle = _create_test_vehicle(self.customer)

	def tearDown(self):
		frappe.db.rollback()

	def _build_renderable_job_bundle(self):
		job = frappe.get_doc("Repair Job", _create_repair_job(self.customer, self.vehicle))
		existing_company = frappe.db.get_all("Company", pluck="name", limit=1)
		currency_name = None
		if existing_company:
			currency_name = frappe.db.get_value("Company", existing_company[0], "default_currency")
		currency_name = currency_name or frappe.db.get_value("Currency", {}, "name") or "USD"
		if not existing_company:
			country_name = frappe.db.get_value("Country", {}, "name") or "Uganda"
			if not frappe.db.exists("Country", country_name):
				frappe.get_doc({"doctype": "Country", "country_name": country_name}).insert(ignore_permissions=True)
			currency_name = frappe.db.get_value("Currency", {}, "name") or "USD"
			if not frappe.db.exists("Currency", currency_name):
				frappe.get_doc({"doctype": "Currency", "currency_name": currency_name}).insert(ignore_permissions=True)
			if not frappe.db.exists("UOM", "Hour"):
				frappe.get_doc({"doctype": "UOM", "name": "Hour", "uom_name": "Hour", "enabled": 1}).insert(ignore_permissions=True)
			if not frappe.db.exists("Warehouse Type", "Transit"):
				frappe.get_doc(
					{
						"doctype": "Warehouse Type",
						"name": "Transit",
						"warehouse_type_name": "Transit",
					}
				).insert(ignore_permissions=True)
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": "Auto Service Test Company",
					"abbr": "AST",
					"default_currency": currency_name,
					"country": country_name,
					"valuation_method": "FIFO",
				}
			).insert(ignore_permissions=True)
		fiscal_year_name = f"FY {frappe.utils.today()[:4]}"
		if not frappe.db.exists("Fiscal Year", fiscal_year_name):
			frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"name": fiscal_year_name,
					"year": fiscal_year_name,
					"year_start_date": f"{frappe.utils.today()[:4]}-01-01",
					"year_end_date": f"{frappe.utils.today()[:4]}-12-31",
				}
			).insert(ignore_permissions=True)
		price_list = "Auto Service Test Selling"
		if not frappe.db.exists("Price List", price_list):
			frappe.get_doc(
				{
					"doctype": "Price List",
					"name": price_list,
					"price_list_name": price_list,
					"selling": 1,
					"enabled": 1,
					"currency": currency_name,
				}
			).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Price List", price_list, "currency", currency_name, update_modified=False)
		settings = frappe.get_single("Auto Service Settings")
		if not settings.company:
			companies = frappe.get_all("Company", pluck="name")
			settings.company = companies[0] if companies else None
		company_currency = frappe.db.get_value("Company", settings.company, "default_currency") if settings.company else None
		settings.company = settings.company or frappe.db.get_all("Company", pluck="name", limit=1)[0]
		settings.default_currency = settings.default_currency or company_currency or frappe.db.get_default("currency") or "USD"
		settings.price_list = price_list
		settings.selling_price_list = price_list
		settings.save(ignore_permissions=True)
		frappe.db.commit()
		from_currency = "INR"
		to_currency = settings.default_currency
		if frappe.db.exists("Currency", from_currency) and frappe.db.exists("Currency", to_currency):
			if not frappe.db.exists(
				"Currency Exchange",
				{"date": frappe.utils.today(), "from_currency": from_currency, "to_currency": to_currency},
			):
				frappe.get_doc(
					{
						"doctype": "Currency Exchange",
						"date": frappe.utils.today(),
						"from_currency": from_currency,
						"to_currency": to_currency,
						"exchange_rate": 1,
					}
				).insert(ignore_permissions=True)

		with patch.object(type(job), "_ensure_project"):
			job.check_in()

		walkaround = _insert_walkaround(job.name, self.vehicle)

		job.reload()
		job.start_diagnosis()
		job.reload()
		_insert_diagnosis(job.name, self.vehicle)
		parts_service = _create_job_service(job, "Renderable parts", status="Approved")
		_append_service_component(
			parts_service,
			service_type="Part",
			description="Renderable parts",
			item_code=TEST_COMPONENT_ITEM_CODE,
			quantity=2,
			rate=175000,
		)
		labour_service = _create_job_service(job, "Renderable labour", status="Approved")
		_append_service_component(
			labour_service,
			service_type="Labour",
			description="Renderable labour",
			quantity=1,
			rate=120000,
		)
		job.reload()
		sync_repair_job_related_tables(job.name)
		job.request_authorization()

		authorization = _insert_authorization(job.name, amount=job.total_amount)
		authorization.approve()

		job.reload()
		job.start_work()
		job.reload()
		job.hold_for_qc()
		job.reload()
		quality_check = _insert_quality_check(job.name, self.vehicle)
		job.reload()
		job.pass_qc()
		sales_invoice_name = job.create_sales_invoice()
		frappe.db.commit()
		sales_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)
		if sales_invoice.docstatus == 0:
			sales_invoice.submit()
		frappe.db.commit()
		job.reload()

		gate_pass = frappe.get_doc(
			{
				"doctype": "Gate Pass",
				"repair_job": job.name,
				"customer_vehicle": self.vehicle,
				"sales_invoice": sales_invoice.name,
				"recipient_name": "Print Test Recipient",
				"status": "Pending",
			}
		)
		gate_pass.flags.ignore_links = True
		with patch.object(type(gate_pass), "validate_invoice_submitted"):
			gate_pass.insert(ignore_permissions=True)

		return job.name, walkaround.name, authorization.name, quality_check.name, gate_pass.name

	def _render_pdf(self, doctype, name, print_format_name):
		import frappe.utils.pdf as frappe_pdf
		from frappe.utils.pdf import get_pdf
		import frappe.utils.jinja_globals as frappe_jinja_globals
		from frappe.www.printview import get_rendered_template
		from frappe.website.utils import abs_url

		doc = frappe.get_doc(doctype, name)
		print_format = frappe.get_doc("Print Format", print_format_name)
		assets_json = frappe.parse_json(frappe.read_file("assets/assets.json")) or {}
		assets_rtl_json = frappe.read_file("assets/assets-rtl.json")
		if assets_rtl_json:
			assets_json.update(frappe.parse_json(assets_rtl_json))
		previous_bundled_asset = frappe_pdf.bundled_asset
		previous_bundled_assets = getattr(frappe_jinja_globals, "bundled_assets", None)

		def deterministic_bundled_asset(path, rtl=None):
			if ".bundle." in path and not path.startswith("/assets"):
				if path.endswith(".css") and rtl:
					path = f"rtl_{path}"
				path = assets_json.get(path) or path
			return abs_url(path)

		frappe_pdf.bundled_asset = deterministic_bundled_asset
		frappe_jinja_globals.bundled_assets = assets_json
		frappe.flags.ignore_print_permissions = True
		try:
			html = get_rendered_template(doc, print_format=print_format, meta=frappe.get_meta(doctype))
			pdf = get_pdf(
				html, options={"load-error-handling": "ignore", "load-media-error-handling": "ignore"}
			)
		finally:
			frappe_pdf.bundled_asset = previous_bundled_asset
			frappe_jinja_globals.bundled_assets = previous_bundled_assets
			frappe.flags.ignore_print_permissions = False
		self.assertTrue(pdf.startswith(b"%PDF"))
		return pdf

	def test_all_phase6_print_formats_render_to_pdf(self):
		job_name, walkaround_name, authorization_name, _quality_check_name, gate_pass_name = (
			self._build_renderable_job_bundle()
		)
		documents = [
			("Repair Job", job_name, "Job Card"),
			("Walkaround Inspection", walkaround_name, "Walkaround Inspection"),
			("Customer Authorization", authorization_name, "Customer Authorization"),
			("Repair Job", job_name, "Estimate Summary"),
			("Gate Pass", gate_pass_name, "Gate Pass"),
			("Repair Job", job_name, "Repair Summary"),
		]

		for doctype, name, print_format_name in documents:
			with self.subTest(print_format=print_format_name):
				pdf = self._render_pdf(doctype, name, print_format_name)
				self.assertGreater(len(pdf), 100)

	def test_workflow_actions_require_write_permission(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)

		with patch.object(type(job), "check_permission", side_effect=frappe.PermissionError):
			with self.assertRaises(frappe.PermissionError):
				job.check_in()

	def test_gate_pass_issue_requires_write_permission(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		gate_pass = frappe.get_doc(
			{
				"doctype": "Gate Pass",
				"repair_job": job_name,
				"customer_vehicle": self.vehicle,
				"sales_invoice": "SI-PERM-001",
				"recipient_name": "Restricted User",
				"status": "Pending",
			}
		)
		gate_pass.flags.ignore_links = True
		with patch.object(type(gate_pass), "validate_invoice_submitted"):
			gate_pass.insert(ignore_permissions=True)

		with patch.object(type(gate_pass), "check_permission", side_effect=frappe.PermissionError):
			with self.assertRaises(frappe.PermissionError):
				gate_pass.issue()

	def test_customer_authorization_approve_requires_write_permission(self):
		job_name = _create_repair_job(self.customer, self.vehicle)
		job = frappe.get_doc("Repair Job", job_name)
		with patch.object(type(job), "_ensure_project"):
			job.check_in()
		_insert_walkaround(job.name, self.vehicle)
		job.reload()
		job.start_diagnosis()
		job.reload()
		_insert_diagnosis(job.name, self.vehicle)
		_append_pending_labour_line(job, "Authorization labour")
		job.request_authorization()

		authorization = _insert_authorization(job.name)

		with patch.object(type(authorization), "check_permission", side_effect=frappe.PermissionError):
			with self.assertRaises(frappe.PermissionError):
				authorization.approve()

	def test_desktop_icon_exists_and_is_visible(self):
		"""App-type Desktop Icon for Auto Service Management must exist and not be hidden."""
		icon = frappe.db.get_value(
			"Desktop Icon",
			{"icon_type": "App", "app": "auto_service_management"},
			["name", "hidden", "link_type", "link_to", "standard"],
			as_dict=True,
		)
		self.assertTrue(icon, "Desktop Icon record must exist for auto_service_management")
		self.assertEqual(icon.name, "Auto Service Management")
		self.assertFalse(icon.hidden, "Desktop Icon must not be hidden")
		self.assertEqual(icon.link_type, "Workspace Sidebar")
		self.assertEqual(icon.link_to, "Workshop Management")
		self.assertTrue(icon.standard, "Desktop Icon must be standard")

	def test_workspace_sidebar_is_grouped_for_auto_service_management(self):
		from auto_service_management.auto_service_management.desktop import setup_desktop

		for name in ("Auto Service Management", "Workshop Management"):
			if frappe.db.exists("Workspace Sidebar", name):
				frappe.delete_doc("Workspace Sidebar", name, ignore_permissions=True)

		setup_desktop()

		sidebar = frappe.get_doc("Workspace Sidebar", "Workshop Management")
		self.assertGreater(len(sidebar.items), 6)

		home_item = sidebar.items[0]
		self.assertEqual(home_item.label, "Home")
		self.assertEqual(home_item.type, "Link")
		self.assertEqual(home_item.link_type, "Workspace")
		self.assertEqual(home_item.link_to, "Workshop Management")

		section_labels = [item.label for item in sidebar.items if item.type == "Section Break"]
		self.assertEqual(
			section_labels,
			[
				"Intake & Setup",
				"Workshop Execution",
				"QC, Release & History",
				"Fleet & Exceptions",
				"Reports",
			],
		)

		link_labels = {item.label for item in sidebar.items if item.type == "Link"}
		self.assertIn("Customer Vehicle", link_labels)
		self.assertIn("Repair Job", link_labels)
		self.assertIn("Gate Pass", link_labels)
		self.assertIn("Jobs by Status", link_labels)
