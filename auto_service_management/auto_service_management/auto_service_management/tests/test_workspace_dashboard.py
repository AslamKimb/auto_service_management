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
	WORKSPACE_LINK_CARDS,
	WORKSPACE_OPERATIONAL_NUMBER_CARDS,
	WORKSPACE_REPORT_LINKS,
	WORKSPACE_SIDEBAR_HOME,
	WORKSPACE_SIDEBAR_SECTION_ICONS,
	WORKSPACE_SIDEBAR_SECTIONS,
	get_auto_service_settings_configured_card_data,
	get_component_child_card_data,
)

LEGACY_COMPONENT_DOCTYPES = {
	"Repair Job Service Subcontracted Service",
	"Repair Service Line",
	"Repair Job Invoice Row",
	"Repair Job Payment Row",
	"Repair Job Service Row",
	"Quality Check Road Test",
}

CATALOG_MASTER_DOCTYPES = {"Vehicle Make", "Vehicle Model"}


class TestWorkspaceDashboardContracts(UnitTestCase):
	def test_boot_payload_excludes_legacy_navigation_keys(self):
		from auto_service_management.auto_service_management.desktop import remove_auto_generated_sidebar

		bootinfo = frappe._dict(
			workspace_sidebar_item={
				"auto service management": {"items": []},
				"workshop management": {"items": []},
				"car workshop": {"items": [{"label": "Home"}]},
				"unrelated": {"items": []},
			}
		)

		remove_auto_generated_sidebar(bootinfo)

		self.assertNotIn("auto service management", bootinfo.workspace_sidebar_item)
		self.assertNotIn("workshop management", bootinfo.workspace_sidebar_item)
		self.assertIn("car workshop", bootinfo.workspace_sidebar_item)
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

	def test_workspace_declares_expected_dashboard_charts_and_number_cards(self):
		module_root = Path(__file__).parents[1]
		path = module_root / "workspace" / "workshop_management" / "workshop_management.json"
		workspace = json.loads(path.read_text(encoding="utf-8"))

		declared_charts = {row["chart_name"] for row in workspace["charts"]}
		declared_cards = {row["number_card_name"] for row in workspace["number_cards"]}

		self.assertEqual(len(workspace["shortcuts"]), 11)
		self.assertEqual(len(workspace["links"]), 36)
		self.assertEqual(declared_charts, set(WORKSPACE_DASHBOARD_CHARTS))
		self.assertEqual(
			declared_cards,
			set(WORKSPACE_OPERATIONAL_NUMBER_CARDS).union(WORKSPACE_COVERAGE_NUMBER_CARDS),
		)

	def test_pending_authorizations_card_uses_readable_docstatus_filter(self):
		module_root = Path(__file__).parents[1]
		path = module_root / "number_card" / "pending_authorizations" / "pending_authorizations.json"
		number_card = json.loads(path.read_text(encoding="utf-8"))

		self.assertEqual(
			json.loads(number_card["filters_json"]),
			[["Customer Authorization", "docstatus", "=", 0]],
		)

	def test_workspace_content_references_expected_dashboard_blocks(self):
		module_root = Path(__file__).parents[1]
		path = module_root / "workspace" / "workshop_management" / "workshop_management.json"
		workspace = json.loads(path.read_text(encoding="utf-8"))
		content = json.loads(workspace["content"])

		chart_refs = {block["data"]["chart_name"] for block in content if block["type"] == "chart"}
		number_card_refs = {
			block["data"]["number_card_name"] for block in content if block["type"] == "number_card"
		}
		card_refs = {block["data"]["card_name"] for block in content if block["type"] == "card"}

		self.assertEqual(chart_refs, set(WORKSPACE_DASHBOARD_CHARTS))
		self.assertEqual(
			number_card_refs,
			set(WORKSPACE_OPERATIONAL_NUMBER_CARDS).union(WORKSPACE_COVERAGE_NUMBER_CARDS),
		)
		self.assertEqual(card_refs, set(WORKSPACE_LINK_CARDS))

	def test_sidebar_definition_matches_grouped_navigation_contract(self):
		self.assertEqual(WORKSPACE_SIDEBAR_HOME["label"], "Home")
		self.assertEqual(WORKSPACE_SIDEBAR_HOME["link_to"], "Workshop Management")
		self.assertEqual(tuple(WORKSPACE_SIDEBAR_SECTIONS), WORKSPACE_LINK_CARDS)
		self.assertTrue(
			any(
				item["label"] == "Customer Vehicle"
				and item["link_type"] == "DocType"
				and item["link_to"] == "Customer Vehicle"
				for item in WORKSPACE_SIDEBAR_SECTIONS["Intake & Setup"]
			)
		)
		self.assertTrue(
			any(item["label"] == "Repair Queue" for item in WORKSPACE_SIDEBAR_SECTIONS["Workshop Execution"])
		)
		self.assertTrue(
			any(item["label"] == "Gate Pass" for item in WORKSPACE_SIDEBAR_SECTIONS["QC, Release & History"])
		)
		self.assertTrue(
			any(
				item["label"] == "Corporate Credit Releases"
				for item in WORKSPACE_SIDEBAR_SECTIONS["Fleet & Exceptions"]
			)
		)
		report_labels = tuple(item["label"] for item in WORKSPACE_SIDEBAR_SECTIONS["Reports"])
		self.assertEqual(report_labels, WORKSPACE_REPORT_LINKS)

	def test_every_sidebar_section_and_link_declares_an_icon(self):
		self.assertEqual(WORKSPACE_SIDEBAR_HOME["icon"], "house")
		self.assertEqual(set(WORKSPACE_SIDEBAR_SECTION_ICONS), set(WORKSPACE_SIDEBAR_SECTIONS))
		for section_label, items in WORKSPACE_SIDEBAR_SECTIONS.items():
			with self.subTest(section=section_label):
				self.assertTrue(WORKSPACE_SIDEBAR_SECTION_ICONS[section_label])
			for item in items:
				with self.subTest(section=section_label, item=item["label"]):
					self.assertTrue(item["icon"])

	def test_every_sidebar_icon_exists_in_frappe_lucide_sprite(self):
		sprite = (
			Path(frappe.get_app_path("frappe"))
			/ "public"
			/ "icons"
			/ "lucide"
			/ "icons.svg"
		).read_text(encoding="utf-8")
		icons = {WORKSPACE_SIDEBAR_HOME["icon"], *WORKSPACE_SIDEBAR_SECTION_ICONS.values()}
		icons.update(item["icon"] for items in WORKSPACE_SIDEBAR_SECTIONS.values() for item in items)

		for icon in icons:
			with self.subTest(icon=icon):
				self.assertIn(f'id="icon-{icon}"', sprite)

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
