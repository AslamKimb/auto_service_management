import json
from pathlib import Path
from unittest.mock import patch

from frappe import scrub
from frappe.tests import UnitTestCase

REPORT_NAMES = {
	"Corporate Credit Releases",
	"Daily Workshop Load",
	"Delayed Jobs",
	"Discount and Price Change Audit",
	"Gate Pass Register",
	"Jobs by Status",
	"Jobs Waiting for Parts",
	"Labour Hours by Technician",
	"Open Repair Jobs",
	"Parts Used by Repair Job",
	"Repair Revenue by Period",
	"Technician Productivity",
	"Vehicle Service History",
}

PRINT_FORMATS = {
	"customer_authorization": ("Customer Authorization", "Customer Authorization"),
	"estimate_summary": ("Estimate Summary", "Repair Job"),
	"gate_pass": ("Gate Pass", "Gate Pass"),
	"job_card": ("Job Card", "Repair Job"),
	"repair_summary": ("Repair Summary", "Repair Job"),
	"walkaround_inspection": ("Walkaround Inspection", "Walkaround Inspection"),
}

WORKSPACE_SHORTCUTS = {
	"Vehicle Search",
	"New Repair Job",
	"Open Repair Jobs",
	"Approval Queue",
	"Repair Queue",
	"Parts Queue",
	"QC Queue",
	"Invoice Queue",
	"Gate Passes",
	"Service History",
	"Reports",
}

WORKSPACE_ROLES = {
	"Service Advisor",
	"Workshop Manager",
	"Parts Interpreter",
	"Cashier",
	"Security Gate Officer",
}


class TestPhase6Contracts(UnitTestCase):
	def test_registry_contains_every_named_report(self):
		from auto_service_management.auto_service_management.reporting.registry import REPORT_DEFINITIONS

		self.assertEqual(set(REPORT_DEFINITIONS), REPORT_NAMES)

	def test_every_report_declares_filters_order_and_permission_scope(self):
		from auto_service_management.auto_service_management.reporting.registry import REPORT_DEFINITIONS

		for report_name, definition in REPORT_DEFINITIONS.items():
			with self.subTest(report=report_name):
				self.assertTrue(definition.columns)
				self.assertIsInstance(definition.filters, tuple)
				self.assertTrue(definition.order_by)
				self.assertTrue(definition.permission_doctype)

	def test_every_report_has_a_standard_script_report(self):
		module_root = Path(__file__).parents[1]
		for report_name in REPORT_NAMES:
			with self.subTest(report=report_name):
				folder = scrub(report_name)
				report_root = module_root / "report" / folder
				data = json.loads((report_root / f"{folder}.json").read_text(encoding="utf-8"))
				self.assertEqual(data["name"], report_name)
				self.assertEqual(data["report_type"], "Script Report")
				self.assertEqual(data["is_standard"], "Yes")
				self.assertEqual(data["apply_user_permissions"], 1)
				self.assertTrue((report_root / f"{folder}.py").is_file())
				self.assertTrue((report_root / f"{folder}.js").is_file())

	def test_standard_print_formats_are_complete(self):
		module_root = Path(__file__).parents[1]
		for folder, (name, doc_type) in PRINT_FORMATS.items():
			with self.subTest(print_format=name):
				path = module_root / "print_format" / folder / f"{folder}.json"
				data = json.loads(path.read_text(encoding="utf-8"))
				self.assertEqual(data["name"], name)
				self.assertEqual(data["doc_type"], doc_type)
				self.assertEqual(data["module"], "Auto Service Management")
				self.assertEqual(data["standard"], "Yes")
				self.assertIn("{{ doc", data["html"])

	def test_walkaround_print_uses_silhouette_and_damage_markers(self):
		module_root = Path(__file__).parents[1]
		path = module_root / "print_format" / "walkaround_inspection" / "walkaround_inspection.json"
		html = json.loads(path.read_text(encoding="utf-8"))["html"]

		self.assertIn("vehicle-silhouette", html)
		self.assertIn("damage_marks", html)

	def test_job_card_print_includes_intake_fuel_level(self):
		module_root = Path(__file__).parents[1]
		path = module_root / "print_format" / "job_card" / "job_card.json"
		html = json.loads(path.read_text(encoding="utf-8"))["html"]

		self.assertIn("doc.fuel_level", html)

	def test_repair_job_related_document_contract_uses_links_not_inline_fields(self):
		module_root = Path(__file__).parents[1]
		path = module_root / "doctype" / "repair_job" / "repair_job.json"
		doctype = json.loads(path.read_text(encoding="utf-8"))
		fields = {field["fieldname"]: field for field in doctype["fields"]}

		self.assertIn("walkaround_inspection", fields)
		self.assertEqual(fields["walkaround_inspection"]["fieldtype"], "Link")
		self.assertEqual(fields["walkaround_inspection"]["options"], "Walkaround Inspection")
		self.assertIn("diagnosis_report", fields)
		self.assertEqual(fields["diagnosis_report"]["fieldtype"], "Link")
		self.assertEqual(fields["diagnosis_report"]["options"], "Diagnosis Report")
		self.assertIn("customer_authorization", fields)
		self.assertEqual(fields["customer_authorization"]["fieldtype"], "Link")
		self.assertEqual(fields["customer_authorization"]["options"], "Customer Authorization")
		self.assertIn("quality_check", fields)
		self.assertEqual(fields["quality_check"]["fieldtype"], "Link")
		self.assertEqual(fields["quality_check"]["options"], "Quality Check")
		self.assertIn("road_test_report", fields)
		self.assertEqual(fields["road_test_report"]["fieldtype"], "Link")
		self.assertEqual(fields["road_test_report"]["options"], "Road Test Report")
		self.assertIn("gate_pass", fields)
		self.assertEqual(fields["gate_pass"]["fieldtype"], "Link")
		self.assertEqual(fields["gate_pass"]["options"], "Gate Pass")

		for removed in (
			"walkaround_inspection_done",
			"customer_authorized",
			"authorization_date",
			"authorized_by",
			"authorization_notes",
			"quality_check_passed",
			"quality_check_notes",
			"road_test_required",
			"road_test_passed",
			"gate_pass_issued",
			"gate_pass_number",
			"labour_total_hours",
			"labour_total_amount",
		):
			self.assertNotIn(removed, fields)

	def test_repair_summary_print_uses_linked_quality_check_status(self):
		module_root = Path(__file__).parents[1]
		path = module_root / "print_format" / "repair_summary" / "repair_summary.json"
		html = json.loads(path.read_text(encoding="utf-8"))["html"]

		self.assertIn("doc.quality_check", html)
		self.assertIn("Quality Check", html)

	def test_workspace_content_references_declared_shortcuts(self):
		module_root = Path(__file__).parents[1]
		path = module_root / "workspace" / "workshop_management" / "workshop_management.json"
		workspace = json.loads(path.read_text(encoding="utf-8"))
		content = json.loads(workspace["content"])
		declared = {shortcut["label"] for shortcut in workspace["shortcuts"]}
		referenced = {block["data"]["shortcut_name"] for block in content if block["type"] == "shortcut"}

		self.assertEqual(referenced, declared)
		self.assertEqual(referenced, WORKSPACE_SHORTCUTS)
		self.assertIn("Gate Passes", referenced)

	def test_workspace_roles_cover_phase6_desk_personas(self):
		module_root = Path(__file__).parents[1]
		path = module_root / "workspace" / "workshop_management" / "workshop_management.json"
		workspace = json.loads(path.read_text(encoding="utf-8"))
		roles = {row["role"] for row in workspace["roles"]}

		self.assertTrue(WORKSPACE_ROLES.issubset(roles))

	def test_report_runner_applies_permissions_filters_and_ordering(self):
		from auto_service_management.auto_service_management.reporting.runner import run_report

		rows = [{"name": "RJ-2026-00001", "job_status": "In Repair"}]
		with (
			patch(
				"auto_service_management.auto_service_management.reporting.runner.frappe.has_permission",
				side_effect=[True, False],
			),
			patch(
				"auto_service_management.auto_service_management.reporting.runner.frappe.get_list",
				return_value=rows,
			) as get_list,
		):
			columns, data = run_report("Open Repair Jobs", {"customer": "CUST-0001"})

		self.assertEqual(data, rows)
		self.assertTrue(columns)
		get_list.assert_called_once()
		call = get_list.call_args
		self.assertEqual(call.args[0], "Repair Job")
		self.assertEqual(call.kwargs["filters"]["customer"], "CUST-0001")
		self.assertEqual(call.kwargs["order_by"], "promised_date asc, modified desc")

	def test_report_runner_rejects_when_read_and_report_permissions_are_missing(self):
		from auto_service_management.auto_service_management.reporting.runner import run_report

		with patch(
			"auto_service_management.auto_service_management.reporting.runner.frappe.has_permission",
			side_effect=[False, False],
		):
			with self.assertRaises(Exception):
				run_report("Open Repair Jobs", {})

	# ── Desk desktop visibility ──

	def test_hooks_declares_add_to_apps_screen(self):
		"""hooks.py must declare add_to_apps_screen so Frappe creates an App-type Desktop Icon."""
		hooks_root = Path(__file__).parents[2]  # hooks.py is at single-nested package level
		hooks_source = (hooks_root / "hooks.py").read_text(encoding="utf-8")
		self.assertIn("add_to_apps_screen", hooks_source)
		self.assertIn("auto_service_management", hooks_source)
		self.assertIn("/app/workshop-management", hooks_source)

	def test_hooks_declares_lifecycle_hooks_for_desktop_icon(self):
		"""hooks.py must declare lifecycle hooks that run the full desktop setup."""
		hooks_root = Path(__file__).parents[2]  # hooks.py is at single-nested package level
		hooks_source = (hooks_root / "hooks.py").read_text(encoding="utf-8")
		self.assertIn("after_install", hooks_source)
		self.assertIn("after_migrate", hooks_source)
		self.assertIn("desktop.setup_desktop", hooks_source)

	def test_desktop_module_exists_with_required_functions(self):
		"""desktop.py must exist and export create_app_desktop_icon and ensure_permission."""
		module_root = Path(__file__).parents[1]
		desktop_path = module_root / "desktop.py"
		self.assertTrue(desktop_path.is_file(), "desktop.py must exist")
		source = desktop_path.read_text(encoding="utf-8")
		self.assertIn("def create_app_desktop_icon", source)
		self.assertIn("def ensure_permission", source)
		self.assertIn("Desktop Icon", source)
