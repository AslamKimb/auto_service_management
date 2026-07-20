from __future__ import annotations

import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.modules.setdefault("frappe", types.SimpleNamespace())

from auto_service_management.auto_service_management.auto_service_management.workflow_setup import (
	WORKFLOW_NAME,
	deactivate_repair_job_workflow,
)


class _FakeDoc:
	def __init__(self, doctype, **values):
		self.doctype = doctype
		self.flags = SimpleNamespace()
		self._values = dict(values)
		self.inserted = False
		self.saved = False

	def set(self, fieldname, value):
		self._values[fieldname] = value

	def insert(self, ignore_permissions=False):
		self.inserted = True
		return self

	def save(self, ignore_permissions=False):
		self.saved = True
		return self

	def __getattr__(self, fieldname):
		try:
			return self._values[fieldname]
		except KeyError as exc:
			raise AttributeError(fieldname) from exc

	def __setattr__(self, fieldname, value):
		if fieldname in {"doctype", "flags", "_values", "inserted", "saved"}:
			object.__setattr__(self, fieldname, value)
			return
		self._values[fieldname] = value


class _FakeDB:
	def __init__(self):
		self.existing = set()
		self.values = {("Workflow", WORKFLOW_NAME, "is_active"): 1}

	def exists(self, doctype, name):
		return (doctype, name) in self.existing

	def get_value(self, doctype, name, fieldname):
		return self.values.get((doctype, name, fieldname))

	def set_value(self, doctype, name, fieldname, value, update_modified=False):
		self.values[(doctype, name, fieldname)] = value


class _FakeFrappe:
	def __init__(self):
		self.db = _FakeDB()
		self.created = {}

	def get_doc(self, doc_or_doctype, name=None):
		if isinstance(doc_or_doctype, dict):
			doctype = doc_or_doctype["doctype"]
			doc = _FakeDoc(doctype, **{k: v for k, v in doc_or_doctype.items() if k != "doctype"})
			if doctype == "Workflow":
				self.created[WORKFLOW_NAME] = doc
			return doc
		return self.created[name]


class TestPhase41WorkflowSetup(unittest.TestCase):
	def test_deactivate_repair_job_workflow_disables_legacy_workflow(self):
		fake_frappe = _FakeFrappe()
		workflow = _FakeDoc("Workflow", is_active=1)
		fake_frappe.created[WORKFLOW_NAME] = workflow
		fake_frappe.db.existing.add(("Workflow", WORKFLOW_NAME))

		with patch(
			"auto_service_management.auto_service_management.auto_service_management.workflow_setup.frappe",
			fake_frappe,
		):
			deactivate_repair_job_workflow()

		self.assertEqual(0, fake_frappe.db.values[("Workflow", WORKFLOW_NAME, "is_active")])
