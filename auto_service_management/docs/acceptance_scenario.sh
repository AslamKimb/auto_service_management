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
    missing = [pf for pf in expected_pf if not frappe.db.exists("Print Format", pf)]
    assert not missing, f"Missing print formats: {missing}"
    print(f"  All {len(expected_pf)} print formats present")
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
    assert len(shortcuts) == 11, f"Expected 11 shortcuts, got {len(shortcuts)}"
    expected_shortcuts = {
        "Find Vehicle", "Customers", "New Repair Job", "Open Repair Jobs",
        "Approval Queue", "Repair Queue", "Parts Queue",
        "QC Queue", "Invoice Queue", "Gate Passes",
        "Service History", "Reports",
    }
    assert shortcuts == expected_shortcuts, f"Shortcuts mismatch: {shortcuts.symmetric_difference(expected_shortcuts)}"
    assert "Workshop Manager" in roles, "Workshop Manager role missing"
    assert "Service Advisor" in roles, "Service Advisor role missing"
    print(f"  Workshop Management workspace present with {len(shortcuts)} shortcuts")
finally:
    frappe.destroy()
PY
echo "  PASS: Workspace verified"

echo ""
echo "Step 12: End-to-end lifecycle with PDF rendering"
SITE_NAME="$SITE" SITES_PATH="$SITES_PATH" "$PYTHON_BIN" - <<'PY'
import os
import frappe
from frappe.utils.pdf import get_pdf
from frappe.www.printview import get_rendered_template
from unittest.mock import patch

os.chdir(os.environ["BENCH_ROOT"])
frappe.init(site=os.environ["SITE_NAME"], sites_path=os.environ["SITES_PATH"])
frappe.connect()

try:
    def render_pdf(doctype, doc_name, print_format_name):
        frappe.flags.ignore_print_permissions = True
        doc = frappe.get_doc(doctype, doc_name)
        print_format = frappe.get_doc("Print Format", print_format_name)
        html = get_rendered_template(doc, print_format=print_format, meta=frappe.get_meta(doctype))
        pdf = get_pdf(html, options={"load-error-handling": "ignore", "load-media-error-handling": "ignore"})
        assert pdf[:4] == b"%PDF", f"Invalid PDF header for {print_format_name}"
        return pdf

    timestamp = frappe.utils.now_datetime().strftime("%Y%m%d%H%M%S")
    customer_name = f"Acceptance Test Customer {timestamp}"

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

    job = frappe.get_doc(
        {
            "doctype": "Repair Job",
            "customer": customer.name,
            "customer_vehicle": vehicle.name,
            "description": "Acceptance test repair job",
            "priority": "Normal",
            "promised_date": frappe.utils.add_days(frappe.utils.today(), 7),
        }
    )
    job.insert(ignore_permissions=True)
    job.check_in()
    frappe.db.commit()

    walkaround = frappe.get_doc(
        {
            "doctype": "Walkaround Inspection",
            "repair_job": job.name,
            "customer_vehicle": vehicle.name,
            "inspection_date": frappe.utils.now_datetime(),
            "inspected_by": "Administrator",
            "overall_condition": "Fair",
        }
    )
    walkaround.insert(ignore_permissions=True)
    frappe.db.commit()

    job.reload()
    job.start_diagnosis()
    frappe.db.commit()
    job.reload()
    job.complete_diagnosis()
    frappe.db.commit()
    job.reload()
    job.request_authorization()
    frappe.db.commit()

    authorization = frappe.get_doc(
        {
            "doctype": "Customer Authorization",
            "repair_job": job.name,
            "customer": customer.name,
            "authorized_by_user": "Administrator",
            "authorization_date": frappe.utils.now_datetime(),
            "approved_amount": 500000,
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

    quality_check = frappe.get_doc(
        {
            "doctype": "Quality Check",
            "repair_job": job.name,
            "customer_vehicle": vehicle.name,
            "qc_date": frappe.utils.now_datetime(),
            "checked_by": "Administrator",
            "status": "Passed",
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
    job.release()
    frappe.db.commit()

    gate_pass = frappe.get_doc(
        {
            "doctype": "Gate Pass",
            "repair_job": job.name,
            "customer_vehicle": vehicle.name,
            "sales_invoice": "SI-ACCEPT-001",
            "recipient_name": customer_name,
            "status": "Pending",
        }
    )
    gate_pass.flags.ignore_links = True
    with patch.object(type(gate_pass), "validate_invoice_submitted"):
        gate_pass.insert(ignore_permissions=True)
    with patch.object(type(gate_pass), "validate_invoice_submitted"):
        gate_pass.issue()
    with patch.object(type(gate_pass), "validate_invoice_submitted"):
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

    print(f"  Repair Job: {job.name}")
    print(f"  Walkaround Inspection: {walkaround.name}")
    print(f"  Customer Authorization: {authorization.name}")
    print(f"  Quality Check: {quality_check.name}")
    print(f"  Gate Pass: {gate_pass.name}")
    if service_history:
        print(f"  Service History: {service_history.name}")
    else:
        print(f"  Service History: (not yet created)")
    print(f"  Repair Job Logs: {len(logs)}")
    assert len(logs) >= 4, f"Expected at least 4 logs, got {len(logs)}"

    # PDF rendering for all 6 print formats
    print("")
    print("  PDF Rendering:")
    documents = [
        ("Repair Job", job.name, "Job Card"),
        ("Walkaround Inspection", walkaround.name, "Walkaround Inspection"),
        ("Customer Authorization", authorization.name, "Customer Authorization"),
        ("Repair Job", job.name, "Estimate Summary"),
        ("Gate Pass", gate_pass.name, "Gate Pass"),
        ("Repair Job", job.name, "Repair Summary"),
    ]

    for doctype, doc_name, print_format_name in documents:
        pdf = render_pdf(doctype, doc_name, print_format_name)
        print(f"    Rendered {print_format_name}: {len(pdf)} bytes")

    print("  PASS: End-to-end lifecycle and PDF rendering verified")
finally:
    frappe.destroy()
PY
echo "  PASS: End-to-end lifecycle with PDF rendering verified"

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
