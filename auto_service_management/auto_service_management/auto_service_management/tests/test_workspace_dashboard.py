import json
from pathlib import Path
from unittest.mock import patch

from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.workspace_dashboard import (
	WORKSPACE_COVERAGE_NUMBER_CARDS,
	WORKSPACE_DASHBOARD_CHARTS,
	WORKSPACE_DOC_TYPE_COVERAGE,
	WORKSPACE_LINK_CARDS,
	WORKSPACE_OPERATIONAL_NUMBER_CARDS,
	WORKSPACE_REPORT_LINKS,
	WORKSPACE_SIDEBAR_HOME,
	WORKSPACE_SIDEBAR_SECTIONS,
	get_auto_service_settings_configured_card_data,
)


class TestWorkspaceDashboardContracts(UnitTestCase):
	def test_doc_type_coverage_constant_matches_app_doctype_inventory(self):
		module_root = Path(__file__).parents[1]
		doctype_root = module_root / "doctype"
		discovered = set()

		for doctype_dir in doctype_root.iterdir():
			if not doctype_dir.is_dir():
				continue
			json_path = doctype_dir / f"{doctype_dir.name}.json"
			if not json_path.is_file():
				continue
			discovered.add(json.loads(json_path.read_text(encoding="utf-8"))["name"])

		self.assertEqual(set(WORKSPACE_DOC_TYPE_COVERAGE), discovered)
		self.assertEqual(len(WORKSPACE_DOC_TYPE_COVERAGE), 17)

	def test_workspace_declares_expected_dashboard_charts_and_number_cards(self):
		module_root = Path(__file__).parents[1]
		path = module_root / "workspace" / "workshop_management" / "workshop_management.json"
		workspace = json.loads(path.read_text(encoding="utf-8"))

		declared_charts = {row["chart_name"] for row in workspace["charts"]}
		declared_cards = {row["number_card_name"] for row in workspace["number_cards"]}

		self.assertEqual(declared_charts, set(WORKSPACE_DASHBOARD_CHARTS))
		self.assertEqual(
			declared_cards,
			set(WORKSPACE_OPERATIONAL_NUMBER_CARDS).union(WORKSPACE_COVERAGE_NUMBER_CARDS),
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
		self.assertIn(
			{"label": "Customer Vehicle", "link_type": "DocType", "link_to": "Customer Vehicle"},
			WORKSPACE_SIDEBAR_SECTIONS["Intake & Setup"],
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
