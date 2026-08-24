"""Focused contracts for current-model Repair Job Service Templates."""

import inspect
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from auto_service_management.auto_service_management.doctype.repair_job_service import repair_job_service


class _Doc(SimpleNamespace):
	def __init__(self, **values):
		super().__init__(**values)
		self._tables = values.pop("_tables", {})

	def get(self, fieldname):
		return self._tables.get(fieldname, [])

	def append(self, fieldname, values):
		doctype = _TABLE_DOCTYPES[fieldname]
		if self.doctype == "Repair Job Service Template":
			doctype = f"Repair Job Service Template {doctype.removeprefix('Repair Job Service ')}"
		values = dict(values)
		if doctype in {"Repair Job Service Part", "Repair Job Service Consumable"}:
			values.setdefault("warehouse", None)
			values.setdefault("uom", None)
		row = _Doc(doctype=doctype, **values)
		self._tables.setdefault(fieldname, []).append(row)
		return row

	def check_permission(self, permission):
		self.checked_permission = permission


_TABLE_DOCTYPES = {
	"parts": "Repair Job Service Part",
	"labour": "Repair Job Service Labour",
	"consumables": "Repair Job Service Consumable",
}


class TestRepairJobServiceTemplates(unittest.TestCase):
	def test_template_schema_is_current_model_and_price_free(self):
		root = Path(__file__).resolve().parents[1] / "doctype"
		parent = json.loads(
			(root / "repair_job_service_template" / "repair_job_service_template.json").read_text()
		)
		self.assertEqual(parent["name"], "Repair Job Service Template")
		self.assertIn("vehicle_make", {field["fieldname"] for field in parent["fields"]})
		self.assertIn("vehicle_model", {field["fieldname"] for field in parent["fields"]})
		for child in ("part", "labour", "consumable"):
			child_json = json.loads(
				(root / f"repair_job_service_template_{child}" / f"repair_job_service_template_{child}.json").read_text()
			)
			self.assertEqual(child_json["istable"], 1)
			fieldnames = {field["fieldname"] for field in child_json["fields"]}
			self.assertNotIn("rate", fieldnames)
			self.assertNotIn("cost_rate", fieldnames)
			self.assertNotIn("discount_percentage", fieldnames)

	def test_template_mappers_are_post_only_and_unsaved(self):
		source = inspect.getsource(repair_job_service)
		self.assertIn('@frappe.whitelist(methods=["POST"])\ndef make_repair_job_service(', source)
		self.assertIn('@frappe.whitelist(methods=["POST"])\ndef make_repair_job_service_template(', source)
		self.assertIn('@frappe.whitelist(methods=["GET"])\ndef get_compatible_repair_job_service_templates', source)
		self.assertNotIn("Repair Service Template\", source_name", source)

	def test_native_mapping_callbacks_route_the_synced_unsaved_doc(self):
		root = Path(__file__).resolve().parents[1] / "doctype"
		job_js = (root / "repair_job" / "repair_job.js").read_text(encoding="utf-8")
		service_js = (root / "repair_job_service" / "repair_job_service.js").read_text(encoding="utf-8")
		template_js = (root / "repair_job_service_template" / "repair_job_service_template.js").read_text(
			encoding="utf-8"
		)
		self.assertIn("const docs = result.message ? frappe.model.sync(result.message) : [];", job_js)
		self.assertIn("const service = docs[0];", job_js)
		self.assertIn("frappe.set_route(\"Form\", service.doctype, service.name)", job_js)
		self.assertIn('frm.add_custom_button("Create Repair Job Service"', job_js)
		self.assertNotIn('frm.add_custom_button("Create Service"', job_js)
		self.assertIn("const docs = r.message ? frappe.model.sync(r.message) : [];", service_js)
		self.assertIn("const template = docs[0];", service_js)
		self.assertIn("frappe.set_route('Form', template.doctype, template.name)", service_js)
		self.assertIn("const service = docs[0];", template_js)
		self.assertIn('frappe.set_route("Form", service.doctype, service.name)', template_js)

	def test_template_to_service_maps_scope_and_snapshots_current_price(self):
		template = _Doc(
			name="RJST-1",
			is_active=1,
			service_name="Oil Service",
			description="Change oil",
			vehicle_make="Toyota",
			vehicle_model="Prado",
			default_billable=1,
			_tables={
				"parts": [_Doc(doctype="Repair Job Service Template Part", item_code="OIL", quantity=4, billable=1)],
				"labour": [_Doc(doctype="Repair Job Service Template Labour", item_code="LAB", estimated_hours=1.5, billable=1)],
				"consumables": [],
			},
		)
		job = _Doc(
			name="RJ-1",
			customer="CUST-1",
			customer_vehicle="VEH-1",
			diagnosis_report="DR-1",
			currency="UGX",
		)
		service = _Doc(doctype="Repair Job Service", repair_job=None)
		settings = _Doc(default_warehouse="Stores", default_labour_item="DEFAULT-LAB", default_labour_rate=80)
		fake_frappe = SimpleNamespace(
			get_doc=lambda doctype, *_args: template if doctype == "Repair Job Service Template" else job,
			has_permission=lambda *_args, **_kwargs: True,
			get_single=lambda *_args: settings,
			db=SimpleNamespace(
				get_value=lambda doctype, *_args, **_kwargs: (
					SimpleNamespace(make="Toyota", model="Prado")
					if doctype == "Customer Vehicle"
					else "Litre"
				)
			),
		)
		with (
			patch.object(repair_job_service, "frappe", fake_frappe),
			patch.object(repair_job_service, "_coerce_target_doc", return_value=service),
			patch("auto_service_management.auto_service_management.integration.erpnext.adapters.get_item_price", side_effect=lambda item: {"OIL": 25, "LAB": 100}[item]),
		):
			result = repair_job_service.make_repair_job_service("RJST-1", repair_job="RJ-1")

		self.assertIs(result, service)
		self.assertEqual(service.repair_job, "RJ-1")
		self.assertEqual(service.customer, "CUST-1")
		self.assertEqual(service.customer_vehicle, "VEH-1")
		self.assertEqual(service.diagnosis_report, "DR-1")
		self.assertEqual(service.currency, "UGX")
		self.assertEqual(service.repair_job_service_template, "RJST-1")
		self.assertEqual(service._tables["parts"][0].rate, 25)
		self.assertEqual(service._tables["parts"][0].warehouse, "Stores")
		self.assertEqual(service._tables["labour"][0].billing_rate, 100)
		self.assertEqual(service._tables["labour"][0].billing_hours, 1.5)
		self.assertFalse(hasattr(service._tables["parts"][0], "discount_percentage"))

	def test_service_to_template_excludes_prices_and_operational_traces(self):
		service = _Doc(
			name="RJS-1", service_name="Brake Service", description="Pads", billable=1,
			_tables={
				"parts": [_Doc(doctype="Repair Job Service Part", item_code="PAD", quantity=2, rate=70, cost_rate=50, discount_percentage=10, warehouse="Stores", sales_invoice="SI-1", billable=1)],
				"labour": [], "consumables": [],
			},
		)
		template = _Doc(doctype="Repair Job Service Template", template_name=None)
		fake_frappe = SimpleNamespace(
			get_doc=lambda *_args: service,
			has_permission=lambda *_args, **_kwargs: True,
		)
		with (
			patch.object(repair_job_service, "frappe", fake_frappe),
			patch.object(repair_job_service, "_coerce_target_doc", return_value=template),
		):
			result = repair_job_service.make_repair_job_service_template("RJS-1")

		row = result._tables["parts"][0]
		self.assertEqual(result.template_name, "Brake Service")
		self.assertEqual(row.item_code, "PAD")
		self.assertFalse(hasattr(row, "rate"))
		self.assertFalse(hasattr(row, "discount_percentage"))
		self.assertFalse(hasattr(row, "warehouse"))
		self.assertFalse(hasattr(row, "sales_invoice"))

	def test_compatible_query_keeps_exact_model_then_make_then_global(self):
		job = _Doc(customer_vehicle="VEH-1")
		rows = [
			frappe._dict(name="GLOBAL", template_name="Global", vehicle_make=None, vehicle_model=None),
			frappe._dict(name="MAKE", template_name="Make", vehicle_make="Toyota", vehicle_model=None),
			frappe._dict(name="MODEL", template_name="Model", vehicle_make="Toyota", vehicle_model="Toyota - Prado"),
			frappe._dict(name="WRONG", template_name="Wrong", vehicle_make="Ford", vehicle_model=None),
		]
		fake_frappe = SimpleNamespace(
			get_doc=lambda *_args: job,
			get_all=lambda *_args, **_kwargs: rows,
			db=SimpleNamespace(
				get_value=lambda *_args, **_kwargs: frappe._dict(make="Toyota", model="Toyota - Prado")
			),
		)
		with (
			patch.object(repair_job_service, "frappe", fake_frappe),
		):
			self.assertEqual(
				[row.name for row in repair_job_service.get_compatible_repair_job_service_templates("RJ-1")],
				["MODEL", "MAKE", "GLOBAL"],
			)
