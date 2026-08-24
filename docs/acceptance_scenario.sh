#!/usr/bin/env bash
# Auto Service Management — Phase 7 Acceptance Scenario
# Run inside the frappe_docker development container after Docker is working.

set -euo pipefail

SITE="auto-service.localhost"
TEST_SITE="auto-service-test.localhost"
APP="auto_service_management"
RUFF_BIN="/home/frappe/frappe-bench/env/bin/ruff"
PYTHON_BIN="/home/frappe/frappe-bench/env/bin/python"
SITES_PATH="/home/frappe/frappe-bench/sites"
BENCH_ROOT="/home/frappe/frappe-bench"

export BENCH_ROOT
export RUFF_CACHE_DIR=/tmp/ruff_cache

echo "============================================"
echo " Phase 7 Acceptance Scenario"
echo " $(date)"
echo "============================================"

echo ""
echo "Step 1: Lint and format check"
"$RUFF_BIN" check --config pyproject.toml auto_service_management/
"$RUFF_BIN" format --check --config pyproject.toml auto_service_management/
echo "  PASS: Lint and format clean"

echo ""
echo "Step 2: Migrate dev site"
bench --site "$SITE" migrate
echo "  PASS: Migration completed"

echo ""
echo "Step 3: Build app assets"
bench build --app "$APP"
echo "  PASS: Assets built"

echo ""
echo "Step 4: Run full test suite"
bench --site "$TEST_SITE" run-tests --app "$APP"
echo "  PASS: All tests passed"

echo ""
echo "Step 5: Export fixtures"
bench --site "$SITE" export-fixtures --app "$APP"
echo "  PASS: Fixtures exported"

echo ""
echo "Step 6: Verify fixture sync"
bench --site "$SITE" migrate
echo "  PASS: Fixture sync verified"

echo ""
echo "Step 7: Verify roles"
SITE_NAME="$SITE" SITES_PATH="$SITES_PATH" "$PYTHON_BIN" - <<'PY'
import os
import frappe

os.chdir(os.environ["BENCH_ROOT"])
frappe.init(site=os.environ["SITE_NAME"], sites_path=os.environ["SITES_PATH"])
frappe.connect()

try:
    expected = {
        "Auto Service Admin", "Cashier", "Parts Interpreter",
        "Security Gate Officer", "Service Advisor",
        "Workshop Manager", "Workshop Technician",
    }
    roles = set(frappe.get_all("Role", filters={"role_name": ["in", list(expected)]}, pluck="role_name"))
    missing = expected - roles
    assert not missing, f"Missing roles: {sorted(missing)}"
    print(f"  All {len(expected)} roles present")
finally:
    frappe.destroy()
PY
echo "  PASS: Roles verified"

echo ""
echo "Step 8: Verify DocTypes"
SITE_NAME="$SITE" SITES_PATH="$SITES_PATH" "$PYTHON_BIN" - <<'PY'
import os
import frappe

os.chdir(os.environ["BENCH_ROOT"])
frappe.init(site=os.environ["SITE_NAME"], sites_path=os.environ["SITES_PATH"])
frappe.connect()

try:
    expected_dt = [
        "Auto Service Settings", "Customer Vehicle", "Workshop Bay",
        "Repair Job", "Repair Service Line", "Repair Job Override",
        "Repair Job Log", "Walkaround Inspection", "Vehicle Damage Mark",
        "Diagnosis Report", "Customer Authorization", "Quality Check",
        "Gate Pass", "Service History",
        "Fleet Service Campaign", "Fleet Service Campaign Job",
    ]
    missing = [dt for dt in expected_dt if not frappe.db.exists("DocType", dt)]
    assert not missing, f"Missing DocTypes: {missing}"
    print(f"  All {len(expected_dt)} DocTypes present")
finally:
    frappe.destroy()
PY
echo "  PASS: DocTypes verified"

echo ""
echo "Step 9: Verify reports"
SITE_NAME="$SITE" SITES_PATH="$SITES_PATH" "$PYTHON_BIN" - <<'PY'
import os
import frappe

os.chdir(os.environ["BENCH_ROOT"])
frappe.init(site=os.environ["SITE_NAME"], sites_path=os.environ["SITES_PATH"])
frappe.connect()

try:
    expected_reports = [
        "Open Repair Jobs", "Daily Workshop Load", "Jobs by Status",
        "Jobs Waiting for Parts", "Technician Productivity",
        "Labour Hours by Technician", "Parts Used by Repair Job",
        "Vehicle Service History", "Delayed Jobs",
        "Repair Revenue by Period", "Gate Pass Register",
        "Corporate Credit Releases", "Discount and Price Change Audit",
    ]
    missing = [r for r in expected_reports if not frappe.db.exists("Report", r)]
    assert not missing, f"Missing reports: {missing}"
    print(f"  All {len(expected_reports)} reports present")
finally:
    frappe.destroy()
PY
echo "  PASS: Reports verified"

echo ""
echo "Step 10: Verify print formats"
SITE_NAME="$SITE" SITES_PATH="$SITES_PATH" "$PYTHON_BIN" - <<'PY'
import os
import frappe

os.chdir(os.environ["BENCH_ROOT"])
frappe.init(site=os.environ["SITE_NAME"], sites_path=os.environ["SITES_PATH"])
frappe.connect()

try:
    expected_pf = [
        "Customer Authorization", "Estimate Summary", "Gate Pass",
        "Job Card", "Repair Summary", "Walkaround Inspection",
    ]
    expected_editable = [f"DMS Editable - {pf}" for pf in expected_pf]
    expected_editable.extend(
        f"DMS Editable - {pf}"
        for pf in ("Quotation", "Sales Invoice", "Proforma Invoice", "Material Request", "Stock Entry", "Timesheet", "Payment Entry")
    )
    missing = [pf for pf in expected_pf + expected_editable if not frappe.db.exists("Print Format", pf)]
    assert not missing, f"Missing print formats: {missing}"
    for name in expected_editable:
        row = frappe.db.get_value("Print Format", name, ["standard", "custom_format", "print_format_builder", "disabled"], as_dict=True)
        assert row.standard == "No" and not row.custom_format and row.print_format_builder and not row.disabled, name
    assert frappe.db.exists("Letter Head", "DMS Company Letterhead"), "Branded letterhead missing"
    print(f"  All {len(expected_pf)} canonical and {len(expected_editable)} editable print formats present")
finally:
    frappe.destroy()
PY
echo "  PASS: Print formats verified"

echo ""
echo "Step 11: Verify workspace"
SITE_NAME="$SITE" SITES_PATH="$SITES_PATH" "$PYTHON_BIN" - <<'PY'
import os
import frappe

os.chdir(os.environ["BENCH_ROOT"])
frappe.init(site=os.environ["SITE_NAME"], sites_path=os.environ["SITES_PATH"])
frappe.connect()
try:
    assert frappe.db.exists('Workspace', 'Workshop Management'), "Workspace missing"
    ws = frappe.get_doc("Workspace", "Workshop Management")
    shortcuts = {s.label for s in ws.get("shortcuts", [])}
    roles = {r.role for r in ws.get("roles", [])}
    expected_shortcuts = {"Find Vehicle", "New Repair Job", "Open Repair Jobs"}
    assert shortcuts == expected_shortcuts, f"Overview shortcuts mismatch: {shortcuts.symmetric_difference(expected_shortcuts)}"
    assert "Workshop Manager" in roles, "Workshop Manager role missing"
    assert "Service Advisor" in roles, "Service Advisor role missing"
    icon = frappe.get_doc("Desktop Icon", "Car Workshop")
    assert icon.icon_type == "App", "Car Workshop icon is not the native parent App"
    assert icon.link == "/desk/workshop-management", "Car Workshop app route changed"
    children = frappe.get_all("Desktop Icon", filters={"parent_icon": "Car Workshop"}, pluck="label", order_by="idx asc")
    assert children == ["Overview", "Intake", "Workshop", "Parts & Billing", "Quality & Release", "Fleet & History", "Reports", "Setup"], children
    assert frappe.db.exists("Workspace Sidebar", "Overview"), "Overview sidebar missing"
    print(f"  Workshop Management Overview present with {len(shortcuts)} shortcuts and {len(children)} child hubs")
finally:
    frappe.destroy()
PY
echo "  PASS: Workspace verified"

echo ""
echo "Step 12: End-to-end walk-in repair lifecycle with PDF rendering"
SITE_NAME="$SITE" SITES_PATH="$SITES_PATH" "$PYTHON_BIN" - <<'PY'
import os
import frappe
import frappe.utils.pdf as frappe_pdf
from frappe.utils.pdf import get_pdf
from frappe.www.printview import get_rendered_template
from frappe.website.utils import abs_url

os.chdir(os.environ["BENCH_ROOT"])
frappe.init(site=os.environ["SITE_NAME"], sites_path=os.environ["SITES_PATH"])
frappe.connect()

try:
    def render_pdf(doctype, doc_name, print_format_name):
        frappe.flags.ignore_print_permissions = True
        assets_json = frappe.parse_json(frappe.read_file("assets/assets.json")) or {}
        assets_rtl_json = frappe.read_file("assets/assets-rtl.json")
        if assets_rtl_json:
            assets_json.update(frappe.parse_json(assets_rtl_json))
        previous_bundled_asset = frappe_pdf.bundled_asset

        def deterministic_bundled_asset(path, rtl=None):
            if ".bundle." in path and not path.startswith("/assets"):
                if path.endswith(".css") and rtl:
                    path = f"rtl_{path}"
                path = assets_json.get(path) or path
            return abs_url(path)

        frappe_pdf.bundled_asset = deterministic_bundled_asset
        doc = frappe.get_doc(doctype, doc_name)
        print_format = frappe.get_doc("Print Format", print_format_name)
        try:
            html = get_rendered_template(doc, print_format=print_format, meta=frappe.get_meta(doctype))
            pdf = get_pdf(
                html,
                options={"load-error-handling": "ignore", "load-media-error-handling": "ignore"},
            )
        finally:
            frappe_pdf.bundled_asset = previous_bundled_asset
        assert pdf[:4] == b"%PDF", f"Invalid PDF header for {print_format_name}"
        return pdf, html

    def ensure_item(item_code, item_name, is_stock_item, price_list, rate):
        if not frappe.db.exists("Item", item_code):
            item = frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": item_code,
                    "item_name": item_name,
                    "item_group": "All Item Groups",
                    "stock_uom": "Nos",
                    "is_stock_item": 1 if is_stock_item else 0,
                    "include_item_in_manufacturing": 0,
                }
            )
            item.insert(ignore_permissions=True)
        if not frappe.db.exists("Item Price", {"item_code": item_code, "price_list": price_list}):
            frappe.get_doc(
                {
                    "doctype": "Item Price",
                    "item_code": item_code,
                    "price_list": price_list,
                    "price_list_rate": rate,
                }
            ).insert(ignore_permissions=True)

    timestamp = frappe.utils.now_datetime().strftime("%Y%m%d%H%M%S")
    customer_name = f"Acceptance Test Customer {timestamp}"
    settings = frappe.get_single("Auto Service Settings")
    price_list = settings.selling_price_list or settings.price_list
    assert settings.company, "Auto Service Settings.company is required"
    assert price_list, "Auto Service Settings selling/price list is required"

    parts_item_code = f"ASM-BATTERY-{timestamp[-6:]}"
    labour_item_code = f"ASM-LABOUR-{timestamp[-6:]}"
    ensure_item(parts_item_code, "Acceptance Battery", True, price_list, 175000)
    ensure_item(labour_item_code, "Acceptance Labour", False, price_list, 120000)

    customer = frappe.get_doc(
        {
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_group": "Commercial",
            "territory": "Uganda",
        }
    )
    customer.insert(ignore_permissions=True)

    vehicle = frappe.get_doc(
        {
            "doctype": "Customer Vehicle",
            "customer": customer.name,
            "registration_number": f"UAX-{timestamp[-6:]}",
            "vin_chassis_number": f"VIN-ACCEPT-{timestamp}",
            "engine_number": f"ENG-ACCEPT-{timestamp}",
            "make": "Toyota",
            "model": "Hilux",
            "year_of_manufacture": 2024,
            "color": "White",
        }
    )
    vehicle.insert(ignore_permissions=True)

    search_registration = frappe.get_all(
        "Customer Vehicle",
        filters={"registration_number": vehicle.registration_number},
        pluck="name",
    )
    search_vin = frappe.get_all(
        "Customer Vehicle",
        filters={"vin_chassis_number": vehicle.vin_chassis_number},
        pluck="name",
    )
    search_engine = frappe.get_all(
        "Customer Vehicle",
        filters={"engine_number": vehicle.engine_number},
        pluck="name",
    )
    search_customer = frappe.get_all(
        "Customer Vehicle",
        filters={"customer": customer.name},
        pluck="name",
    )
    assert vehicle.name in search_registration, "Vehicle search by registration failed"
    assert vehicle.name in search_vin, "Vehicle search by VIN failed"
    assert vehicle.name in search_engine, "Vehicle search by engine failed"
    assert vehicle.name in search_customer, "Vehicle search by customer failed"

    job = frappe.get_doc(
        {
            "doctype": "Repair Job",
            "customer": customer.name,
            "customer_vehicle": vehicle.name,
            "description": "Battery replacement, brake noise, engine check",
            "priority": "Normal",
            "promised_date": frappe.utils.add_days(frappe.utils.today(), 7),
            "odometer_in": 84521,
        }
    )
    job.insert(ignore_permissions=True)
    job.check_in()
    frappe.db.commit()
    job.reload()

    walkaround = frappe.get_doc(
        {
            "doctype": "Walkaround Inspection",
            "repair_job": job.name,
            "customer_vehicle": vehicle.name,
            "inspection_date": frappe.utils.now_datetime(),
            "inspected_by": "Administrator",
            "overall_condition": "Fair",
            "odometer_reading": 84521,
            "fuel_level": "1/2",
            "customer_present": 1,
            "condition_notes": "Minor front bumper scratches. Brake noise confirmed by customer.",
        }
    )
    walkaround.insert(ignore_permissions=True)
    frappe.db.commit()

    job.reload()
    job.start_diagnosis()
    frappe.db.commit()
    job.reload()

    diagnosis = frappe.get_doc(
        {
            "doctype": "Diagnosis Report",
            "repair_job": job.name,
            "customer_vehicle": vehicle.name,
            "diagnosis_date": frappe.utils.now_datetime(),
            "diagnosed_by": "Administrator",
            "customer_complaint": "Battery weak, brake noise, engine warning check required",
            "findings": "Battery failed load test; front pads worn; engine scan found minor sensor alert.",
            "recommendations": "Replace battery, inspect front brakes, clear and monitor sensor alert.",
            "estimated_hours": 2.5,
            "required_parts": "Battery, brake pads",
            "status": "Submitted",
        }
    )
    diagnosis.insert(ignore_permissions=True)

    job.append(
        "service_lines",
        {
            "service_type": "Parts",
            "service_description": "Battery replacement",
            "item_code": parts_item_code,
            "quantity": 2,
            "rate": 175000,
            "status": "Approved",
        },
    )
    job.append(
        "service_lines",
        {
            "service_type": "Labour",
            "service_description": "Brake inspection and engine check",
            "item_code": labour_item_code,
            "quantity": 1,
            "rate": 120000,
            "status": "Approved",
        },
    )
    job.save(ignore_permissions=True)
    frappe.db.commit()

    job.reload()
    job.request_authorization()
    frappe.db.commit()
    job.reload()

    authorization = frappe.get_doc(
        {
            "doctype": "Customer Authorization",
            "repair_job": job.name,
            "customer": customer.name,
            "authorized_by_user": "Administrator",
            "authorization_date": frappe.utils.now_datetime(),
            "approved_amount": job.total_amount,
            "status": "Pending",
        }
    )
    authorization.insert(ignore_permissions=True)
    authorization.approve()
    frappe.db.commit()

    job.reload()
    job.authorize()
    frappe.db.commit()
    job.reload()
    job.start_work()
    frappe.db.commit()
    job.reload()

    for line in job.service_lines:
        line.status = "Completed"
    job.odometer_out = 84533
    job.save(ignore_permissions=True)
    frappe.db.commit()

    quality_check = frappe.get_doc(
        {
            "doctype": "Quality Check",
            "repair_job": job.name,
            "customer_vehicle": vehicle.name,
            "qc_date": frappe.utils.now_datetime(),
            "checked_by": "Administrator",
            "status": "Passed",
            "completion_check": 1,
            "fitment_check": 1,
            "fluid_levels_check": 1,
            "warning_lights_clear": 1,
            "cleanliness_check": 1,
            "road_test_check": 0,
            "qc_notes": "Battery replaced and brake inspection completed.",
        }
    )
    quality_check.insert(ignore_permissions=True)
    frappe.db.commit()

    job.reload()
    job.hold_for_qc()
    frappe.db.commit()
    job.reload()
    job.pass_qc()
    frappe.db.commit()
    job.reload()

    sales_order_name = job.create_sales_order()
    frappe.db.commit()
    sales_order = frappe.get_doc("Sales Order", sales_order_name)
    sales_order.submit()
    frappe.db.commit()
    second_sales_order_name = job.create_sales_order()
    frappe.db.commit()
    second_sales_order = frappe.get_doc("Sales Order", second_sales_order_name)
    sales_order_rows = frappe.get_all(
        "Sales Order",
        filters={"repair_job": job.name},
        fields=["name", "transaction_date"],
        order_by="creation asc",
    )
    assert len(sales_order_rows) == 2, f"Expected two Sales Orders, got {len(sales_order_rows)}"
    assert sales_order_rows[0].name != sales_order_rows[1].name, "Repeated Sales Order overwrote history"
    assert sales_order.items, "Sales Order has no billable lines"
    assert all(item.repair_job == job.name for item in sales_order.items)
    from auto_service_management.auto_service_management.integration.sales_order_mapping import (
        make_sales_invoice,
    )

    mapped_invoice = make_sales_invoice(sales_order.name)
    mapped_invoice.insert(ignore_permissions=True)
    assert mapped_invoice.items, "Native Sales Order-to-invoice mapping produced no lines"
    assert all(item.repair_job == job.name for item in mapped_invoice.items)
    assert all(item.so_detail for item in mapped_invoice.items), "Sales Order item trace was not preserved"
    frappe.db.commit()

    sales_invoice_name = job.create_sales_invoice()
    frappe.db.commit()
    sales_invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)
    if sales_invoice.docstatus == 0:
        sales_invoice.submit()
    frappe.db.commit()

    job.reload()
    gate_pass_name = job.create_gate_pass()
    frappe.db.commit()
    gate_pass = frappe.get_doc("Gate Pass", gate_pass_name)
    gate_pass.issue()
    frappe.db.commit()
    gate_pass.reload()
    gate_pass.use_gate_pass()
    frappe.db.commit()

    job.reload()
    job.close()
    frappe.db.commit()
    job.reload()

    # Verify service history
    service_history_name = frappe.db.get_value("Service History", {"repair_job": job.name}, "name")
    if service_history_name:
        service_history = frappe.get_doc("Service History", service_history_name)
    else:
        service_history = None

    logs = frappe.get_all("Repair Job Log", filters={"repair_job": job.name}, pluck="name")

    print(f"  search_registration: {search_registration}")
    print(f"  search_vin: {search_vin}")
    print(f"  search_engine: {search_engine}")
    print(f"  search_customer_count: {len(search_customer)}")
    print(f"  Repair Job: {job.name}")
    print(f"  Project: {job.project}")
    print(f"  Walkaround Inspection: {walkaround.name}")
    print(f"  Diagnosis Report: {diagnosis.name}")
    print(f"  Customer Authorization: {authorization.name}")
    print(f"  Quality Check: {quality_check.name}")
    print(f"  Sales Invoice: {sales_invoice.name}")
    print(f"  Proforma Invoices (Sales Orders): {sales_order.name}, {second_sales_order.name}")
    print(f"  Native Sales Order Invoice: {mapped_invoice.name}")
    print(f"  Gate Pass: {gate_pass.name}")
    if service_history:
        print(f"  Service History: {service_history.name}")
    else:
        print(f"  Service History: (not yet created)")
    print(f"  Repair Job Logs: {len(logs)}")
    print(f"  service_lines: {[(line.service_type, line.amount, line.status, line.item_code) for line in job.service_lines]}")
    print(f"  total_amount: {job.total_amount}")
    print(f"  status_after_close: {job.job_status}")
    assert job.project, "Repair Job project was not created on check-in"
    assert job.job_status == "Closed", f"Expected Closed, got {job.job_status}"
    assert job.total_amount == 470000, f"Expected total 470000, got {job.total_amount}"
    assert sales_invoice.docstatus == 1, "Sales Invoice was not submitted"
    assert len(sales_order_rows) == 2, "Sales Order count did not include repeated proforma invoices"
    assert mapped_invoice.repair_job == job.name, "Native invoice lost Repair Job trace"
    assert gate_pass.status == "Used", f"Expected Used gate pass, got {gate_pass.status}"
    assert service_history is not None, "Service History was not created"
    assert len(logs) >= 10, f"Expected at least 10 logs, got {len(logs)}"

    # Minimal path: optional inspection, diagnosis, authorization, QC, and road-test
    # records are all omitted while the Repair Job still advances to Billing.
    # Failed QC never regresses automatically; rework uses the explicit Return to Repair action.
    minimal_job = frappe.get_doc(
        {
            "doctype": "Repair Job",
            "customer": customer.name,
            "customer_vehicle": vehicle.name,
            "description": "Optional evidence path",
            "priority": "Normal",
            "promised_date": frappe.utils.add_days(frappe.utils.today(), 7),
            "odometer_in": 84522,
        }
    )
    minimal_job.insert(ignore_permissions=True)
    minimal_job.check_in()
    minimal_job.append(
        "service_lines",
        {
            "service_type": "Labour",
            "service_description": "Minimal optional-evidence path",
            "item_code": labour_item_code,
            "quantity": 1,
            "rate": 120000,
            "status": "Approved",
        },
    )
    minimal_job.save(ignore_permissions=True)
    minimal_job.complete_diagnosis()
    minimal_job.start_work()
    minimal_job.mark_ready_for_invoice()
    minimal_job.reload()
    assert minimal_job.job_status == "Billing", f"Optional-evidence path stopped at {minimal_job.job_status}"
    assert not any(
        minimal_job.get(fieldname)
        for fieldname in ("walkaround_inspection", "diagnosis_report", "customer_authorization", "quality_check")
    ), "Optional evidence unexpectedly became required on the minimal path"
    frappe.db.commit()
    print(f"  Minimal optional-evidence path: {minimal_job.name} -> {minimal_job.job_status}")

    # PDF rendering for the core formats and the Sales Order Proforma Invoice
    print("")
    print("  PDF Rendering:")
    documents = [
        ("Repair Job", job.name, "Job Card"),
        ("Walkaround Inspection", walkaround.name, "Walkaround Inspection"),
        ("Customer Authorization", authorization.name, "Customer Authorization"),
        ("Repair Job", job.name, "Estimate Summary"),
        ("Sales Order", sales_order.name, "Proforma Invoice"),
        ("Gate Pass", gate_pass.name, "Gate Pass"),
        ("Repair Job", job.name, "Repair Summary"),
    ]

    for doctype, doc_name, print_format_name in documents:
        pdf, html = render_pdf(doctype, doc_name, print_format_name)
        print(f"    Rendered {print_format_name}: {len(pdf)} bytes")
        if print_format_name == "Estimate Summary":
            assert "This proforma invoice is valid for one month only unless the vehicle is not mobile." in html
            assert "Source:" in html
        if print_format_name == "Proforma Invoice":
            assert "Proforma Invoice" in html
            assert sales_order.name in html

    company_logo = frappe.db.get_value("Company", settings.company, "company_logo")
    website = frappe.get_single("Website Settings")
    website_logos = {"app_logo": website.app_logo, "banner_image": website.banner_image}
    try:
        frappe.db.set_value("Company", settings.company, "company_logo", "/files/acceptance-company-logo.svg")
        _company_pdf, company_logo_html = render_pdf("Repair Job", job.name, "Estimate Summary")
        assert "/files/acceptance-company-logo.svg" in company_logo_html
        frappe.db.set_value("Company", settings.company, "company_logo", None)
        frappe.db.set_value("Website Settings", website.name, "app_logo", "/files/acceptance-app-logo.svg")
        _app_pdf, app_logo_html = render_pdf("Repair Job", job.name, "Estimate Summary")
        assert "/files/acceptance-app-logo.svg" in app_logo_html
        frappe.db.set_value("Website Settings", website.name, "app_logo", None)
        frappe.db.set_value("Website Settings", website.name, "banner_image", "/files/acceptance-banner.svg")
        _banner_pdf, banner_html = render_pdf("Repair Job", job.name, "Estimate Summary")
        assert "/files/acceptance-banner.svg" in banner_html
    finally:
        frappe.db.set_value("Company", settings.company, "company_logo", company_logo)
        for field, value in website_logos.items():
            frappe.db.set_value("Website Settings", website.name, field, value)

    print("  PASS: End-to-end walk-in repair lifecycle and PDF rendering verified")
finally:
    frappe.destroy()
PY
echo "  PASS: End-to-end walk-in repair lifecycle with PDF rendering verified"

echo ""
echo "Step 13: Verify clean uninstall and reinstall on test site"
bench --site "$TEST_SITE" uninstall-app "$APP" --yes
bench --site "$TEST_SITE" install-app "$APP"
bench --site "$TEST_SITE" migrate
SITE_NAME="$TEST_SITE" SITES_PATH="$SITES_PATH" "$PYTHON_BIN" - <<'PY'
import os
import frappe

os.chdir(os.environ["BENCH_ROOT"])
frappe.init(site=os.environ["SITE_NAME"], sites_path=os.environ["SITES_PATH"])
frappe.connect()

try:
    assert frappe.db.exists("DocType", "Repair Job"), "Repair Job DocType missing"
    assert frappe.db.exists("Workspace", "Workshop Management"), "Workspace missing"
    assert frappe.db.exists("Print Format", "Repair Summary"), "Print Format missing"
    assert frappe.db.exists("Print Format", "DMS Editable - Repair Summary"), "Editable print format missing"
    assert frappe.db.exists("Letter Head", "DMS Company Letterhead"), "Branded letterhead missing"
    assert frappe.db.exists("Report", "Open Repair Jobs"), "Report missing"
    print("  Test site reinstall verified")
finally:
    frappe.destroy()
PY
echo "  PASS: Uninstall and reinstall verified"

echo ""
echo "============================================"
echo " Acceptance Scenario Complete"
echo " $(date)"
echo "============================================"
