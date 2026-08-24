from pathlib import Path

from frappe.tests import UnitTestCase

WORKSPACE_SHORTCUTS = {
	"Find Vehicle",
	"Customers",
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


class TestPhase7HardeningContracts(UnitTestCase):
	def test_acceptance_script_verifies_roles_workspace_pdfs_and_reinstall(self):
		repo_root = Path(__file__).parents[3]
		script = (repo_root / "docs" / "acceptance_scenario.sh").read_text(encoding="utf-8")

		self.assertIn('bench --site "$TEST_SITE" uninstall-app "$APP" --yes', script)
		self.assertIn('bench --site "$TEST_SITE" install-app "$APP"', script)
		self.assertIn("frappe.db.exists('Workspace', 'Workshop Management')", script)
		self.assertIn("role_name", script)
		self.assertIn("render_pdf", script)
		for print_format in (
			"Job Card",
			"Walkaround Inspection",
			"Customer Authorization",
			"Estimate Summary",
			"Gate Pass",
			"Repair Summary",
		):
			with self.subTest(print_format=print_format):
				self.assertIn(print_format, script)

	def test_workspace_fixture_contains_phase7_shortcuts_and_roles(self):
		import json

		module_root = Path(__file__).parents[1]
		workspace = json.loads(
			(module_root / "workspace" / "workshop_management" / "workshop_management.json").read_text(
				encoding="utf-8"
			)
		)
		declared_shortcuts = {shortcut["label"] for shortcut in workspace["shortcuts"]}
		declared_roles = {row["role"] for row in workspace["roles"]}

		self.assertEqual(declared_shortcuts, WORKSPACE_SHORTCUTS)
		self.assertTrue(WORKSPACE_ROLES.issubset(declared_roles))
