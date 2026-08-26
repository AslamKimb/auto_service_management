import json
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.workspace_dashboard import (
	CHILD_COMPONENT_CARD_CONFIG,
	WORKSPACE_COVERAGE_NUMBER_CARDS,
	WORKSPACE_DASHBOARD_CHARTS,
	WORKSPACE_DOC_TYPE_COVERAGE,
	WORKSPACE_HUBS,
	WORKSPACE_OPERATIONAL_NUMBER_CARDS,
	WORKSPACE_REPORT_LINKS,
	WORKSPACE_SIDEBAR_HOME,
	WORKSPACE_SIDEBAR_SECTION_ICONS,
	WORKSPACE_SIDEBAR_SECTIONS,
	get_auto_service_settings_configured_card_data,
	get_component_child_card_data,
	get_repair_job_service_consumables_card_data,
	get_repair_job_service_labour_card_data,
	get_repair_job_service_parts_card_data,
)

LEGACY_COMPONENT_DOCTYPES = {
	"Repair Job Service Subcontracted Service",
	"Repair Service Line",
	"Repair Job Invoice Row",
	"Repair Job Payment Row",
	"Repair Job Sales Order Row",
	"Repair Job Service Row",
	"Quality Check Road Test",
}

CATALOG_MASTER_DOCTYPES = {
	"Vehicle Make",
	"Vehicle Model",
	"Vehicle Engine",
	"Item Vehicle Fitment",
}


class TestWorkspaceDashboardContracts(UnitTestCase):
	def test_dashboard_card_methods_are_read_only_get_endpoints(self):
		for method in (
			get_auto_service_settings_configured_card_data,
			get_repair_job_service_parts_card_data,
			get_repair_job_service_labour_card_data,
			get_repair_job_service_consumables_card_data,
		):
			with self.subTest(method=method.__name__):
				self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[method], ["GET"])

	def test_boot_payload_excludes_legacy_navigation_keys(self):
		from auto_service_management.auto_service_management.desktop import remove_auto_generated_sidebar

		bootinfo = frappe._dict(
			workspace_sidebar_item={
				"auto service management": {"items": []},
				"workshop management": {"items": []},
				"overview": {"items": [{"label": "Home"}]},
				"unrelated": {"items": []},
			}
		)

		remove_auto_generated_sidebar(bootinfo)

		self.assertNotIn("auto service management", bootinfo.workspace_sidebar_item)
		self.assertNotIn("workshop management", bootinfo.workspace_sidebar_item)
		self.assertIn("overview", bootinfo.workspace_sidebar_item)
		self.assertIn("unrelated", bootinfo.workspace_sidebar_item)

	def test_doc_type_coverage_constant_matches_app_doctype_inventory(self):
		module_root = Path(__file__).parents[1]
		doctype_root = module_root / "doctype"
		discovered = set()

		for doctype_dir in doctype_root.iterdir():
			if not doctype_dir.is_dir() or doctype_dir.name.startswith("__"):
				continue
			json_path = doctype_dir / f"{doctype_dir.name}.json"
			if not json_path.is_file():
				continue
			discovered.add(json.loads(json_path.read_text(encoding="utf-8"))["name"])

		self.assertEqual(
			set(WORKSPACE_DOC_TYPE_COVERAGE),
			discovered - LEGACY_COMPONENT_DOCTYPES - CATALOG_MASTER_DOCTYPES,
		)
		self.assertTrue(LEGACY_COMPONENT_DOCTYPES.issubset(discovered))
		self.assertTrue(CATALOG_MASTER_DOCTYPES.issubset(discovered))

	def test_overview_keeps_operational_metrics_only(self):
		path = Path(__file__).parents[1] / "workspace" / "workshop_management" / "workshop_management.json"
		workspace = json.loads(path.read_text(encoding="utf-8"))
		content = json.loads(workspace["content"])

		self.assertEqual(workspace["label"], "Overview")
		self.assertEqual(workspace["title"], "Workshop Management")
		self.assertEqual(
			{row["chart_name"] for row in workspace["charts"]},
			set(WORKSPACE_DASHBOARD_CHARTS),
		)
		self.assertEqual(
			{row["number_card_name"] for row in workspace["number_cards"]},
			set(WORKSPACE_OPERATIONAL_NUMBER_CARDS),
		)
		self.assertNotIn("DocType Coverage", json.dumps(content))
		self.assertFalse(
			set(WORKSPACE_COVERAGE_NUMBER_CARDS)
			& {block["data"].get("number_card_name") for block in content if block["type"] == "number_card"}
		)

	def test_all_eight_workspace_fixtures_match_hub_contract(self):
		root = Path(__file__).parents[1] / "workspace"
		fixture_by_name = {
			json.loads(path.read_text(encoding="utf-8"))["name"]: json.loads(path.read_text(encoding="utf-8"))
			for path in root.glob("*/*.json")
		}
		self.assertEqual(len(fixture_by_name), 8)

		for label, hub in WORKSPACE_HUBS.items():
			with self.subTest(hub=label):
				workspace = fixture_by_name[hub["workspace_name"]]
				self.assertEqual(workspace["app"], "auto_service_management")
				self.assertEqual(workspace["type"], "Workspace")
				self.assertEqual(workspace["label"], label)
				self.assertEqual(workspace["title"], hub["workspace_name"])
				self.assertEqual(set(role["role"] for role in workspace["roles"]), set(hub["roles"]))
				links = json.loads(workspace["content"])
				fixture_links = [
					(item["label"], item["link_type"], item["link_to"]) for item in workspace["links"]
				]
				hub_links = [(item["label"], item["link_type"], item["link_to"]) for item in hub["links"]]
				self.assertEqual(fixture_links, hub_links)
				link_targets = [item.get("link_to") for item in workspace["shortcuts"]]
				self.assertEqual(len(link_targets), len(set(link_targets)))
				self.assertTrue(links)

	def test_sidebar_definitions_have_exact_hub_order_and_no_duplicate_targets(self):
		self.assertEqual(
			tuple(WORKSPACE_HUBS),
			(
				"Overview",
				"Intake",
				"Workshop",
				"Parts & Billing",
				"Quality & Release",
				"Fleet & History",
				"Reports",
				"Setup",
			),
		)
		self.assertEqual(WORKSPACE_SIDEBAR_HOME["link_to"], "Workshop Management")
		self.assertEqual(set(WORKSPACE_SIDEBAR_SECTION_ICONS), set(WORKSPACE_HUBS))

		for label, items in WORKSPACE_SIDEBAR_SECTIONS.items():
			with self.subTest(hub=label):
				self.assertTrue(items)
				targets = [(item["link_type"], item["link_to"]) for item in items]
				self.assertEqual(len(targets), len(set(targets)))
				self.assertTrue(all(item.get("icon") for item in items))

		self.assertEqual(
			tuple(item["label"] for item in WORKSPACE_SIDEBAR_SECTIONS["Reports"]),
			WORKSPACE_REPORT_LINKS,
		)

	def test_every_sidebar_icon_exists_in_frappe_lucide_sprite(self):
		sprite = (
			Path(frappe.get_app_path("frappe")) / "public" / "icons" / "lucide" / "icons.svg"
		).read_text(encoding="utf-8")
		icons = {WORKSPACE_SIDEBAR_HOME["icon"], *WORKSPACE_SIDEBAR_SECTION_ICONS.values()}
		icons.update(item["icon"] for items in WORKSPACE_SIDEBAR_SECTIONS.values() for item in items)

		for icon in icons:
			with self.subTest(icon=icon):
				self.assertIn(f'id="icon-{icon}"', sprite)

	def test_hub_launcher_logo_assets_exist(self):
		app_root = Path(__file__).parents[2]
		for label, hub in WORKSPACE_HUBS.items():
			with self.subTest(hub=label):
				self.assertTrue(hub["logo_url"].startswith("/assets/auto_service_management/"))
				asset_path = (
					app_root / "public" / hub["logo_url"].split("/assets/auto_service_management/", 1)[1]
				)
				self.assertTrue(asset_path.is_file(), asset_path)

	def test_singleton_settings_number_card_returns_one_when_configured(self):
		with patch(
			"auto_service_management.auto_service_management.workspace_dashboard.frappe.db.exists",
			return_value=True,
		):
			result = get_auto_service_settings_configured_card_data()

		self.assertEqual(result["value"], 1)
		self.assertEqual(result["fieldtype"], "Int")
		self.assertEqual(result["route"], ["Form", "Auto Service Settings", "Auto Service Settings"])

	def test_singleton_settings_number_card_returns_zero_when_missing(self):
		with patch(
			"auto_service_management.auto_service_management.workspace_dashboard.frappe.db.exists",
			return_value=False,
		):
			result = get_auto_service_settings_configured_card_data()

		self.assertEqual(result["value"], 0)
		self.assertEqual(result["fieldtype"], "Int")
		self.assertEqual(result["route"], ["Form", "Auto Service Settings", "Auto Service Settings"])

	def test_component_child_number_cards_count_rows_via_parent_permission(self):
		with (
			patch(
				"auto_service_management.auto_service_management.workspace_dashboard.frappe.has_permission"
			) as has_permission,
			patch(
				"auto_service_management.auto_service_management.workspace_dashboard.frappe.db.count",
				return_value=7,
			) as count,
		):
			result = get_component_child_card_data("Repair Job Service Consumables")

		config = CHILD_COMPONENT_CARD_CONFIG["Repair Job Service Consumables"]
		has_permission.assert_called_once_with(config["parent_doctype"], "read", throw=True)
		count.assert_called_once_with(config["child_doctype"])
		self.assertEqual(result["value"], 7)
		self.assertEqual(result["fieldtype"], "Int")
		self.assertEqual(result["route"], config["route"])
