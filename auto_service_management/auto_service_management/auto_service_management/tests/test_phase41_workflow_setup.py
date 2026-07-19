from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
import unittest

from auto_service_management.auto_service_management.workflow_setup import (
	WORKFLOW_NAME,
	ensure_repair_job_workflow,
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

	def exists(self, doctype, name):
		return (doctype, name) in self.existing


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
	def test_ensure_repair_job_workflow_builds_reduced_state_machine(self):
		fake_frappe = _FakeFrappe()

		with patch("auto_service_management.auto_service_management.workflow_setup.frappe", fake_frappe):
			ensure_repair_job_workflow()

		workflow = fake_frappe.created[WORKFLOW_NAME]
		self.assertEqual(workflow.document_type, "Repair Job")
		self.assertEqual(workflow.workflow_state_field, "workflow_state")
		self.assertTrue(workflow.inserted)
		self.assertEqual(9, len(workflow.states))
		self.assertEqual(12, len(workflow.transitions))
		self.assertEqual(
			{
				"Draft",
				"Assessment",
				"Awaiting Approval",
				"In Repair",
				"Quality Check",
				"Billing",
				"Ready for Release",
				"Closed",
				"Cancelled",
			},
			{row["state"] for row in workflow.states},
		)
