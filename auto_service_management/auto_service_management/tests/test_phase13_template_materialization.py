# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	RepairJobService,
)


class _TemplateProbe:
	def __init__(self):
		self.template_name = "RST-001"
		self.service_name = "Engine Service"
		self.description = "Template description"
		self.default_billable = 0
		self.parts = [
			frappe._dict(
				{
					"description": "Oil filter",
					"item_code": "OIL-FILTER",
					"quantity": 2,
					"rate": 100,
					"cost_rate": 60,
					"billable": 1,
				}
			),
			frappe._dict(
				{
					"description": "Oil filter",
					"item_code": "OIL-FILTER",
					"quantity": 2,
					"rate": 100,
					"cost_rate": 60,
					"billable": 1,
				}
			),
		]
		self.labour = [
			frappe._dict(
				{
					"description": "Inspection",
					"activity_type": "Inspection",
					"estimated_hours": 1,
					"billing_hours": 1,
					"billing_rate": 200,
					"costing_rate": 80,
					"billable": 1,
				}
			)
		]
		self.consumables = []

	def get(self, fieldname):
		return getattr(self, fieldname)


class _ServiceProbe:
	def __init__(self, *, parts=None, labour=None, consumables=None, service_name="", description="", billable=None):
		self.repair_service_template = "RST-001"
		self.service_name = service_name
		self.description = description
		self.billable = billable
		self.parts = parts or []
		self.labour = labour or []
		self.consumables = consumables or []

	def get(self, fieldname):
		return getattr(self, fieldname)

	def append(self, fieldname, row):
		getattr(self, fieldname).append(frappe._dict(row))


class TestPhase13TemplateMaterialization(UnitTestCase):
	def test_template_rows_are_materialized_without_duplicate_append(self):
		template = _TemplateProbe()
		service = _ServiceProbe(parts=[frappe._dict(template.parts[0])])

		with patch.object(frappe, "get_doc", return_value=template) as get_doc:
			changed = RepairJobService.materialize_template_components(service)

		self.assertTrue(changed)
		self.assertEqual(service.service_name, template.service_name)
		self.assertEqual(service.description, template.description)
		self.assertEqual(service.billable, template.default_billable)
		self.assertEqual(len(service.parts), 2)
		self.assertEqual(len(service.labour), 1)
		self.assertEqual(len(service.consumables), 0)
		self.assertEqual(get_doc.call_args.args, ("Repair Service Template", "RST-001"))

	def test_materialization_is_idempotent_when_rows_already_match(self):
		template = _TemplateProbe()
		service = _ServiceProbe(
			parts=[frappe._dict(template.parts[0]), frappe._dict(template.parts[1])],
			labour=[frappe._dict(template.labour[0])],
			service_name=template.service_name,
			description=template.description,
			billable=template.default_billable,
		)

		with patch.object(frappe, "get_doc", return_value=template):
			changed = RepairJobService.materialize_template_components(service)

		self.assertFalse(changed)
		self.assertEqual(len(service.parts), 2)
		self.assertEqual(len(service.labour), 1)
		self.assertEqual(len(service.consumables), 0)
