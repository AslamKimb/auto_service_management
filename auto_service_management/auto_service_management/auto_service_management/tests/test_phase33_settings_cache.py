"""Focused contracts for the stable Auto Service Settings cache boundary."""

import inspect
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management import settings_cache
from auto_service_management.auto_service_management.doctype.auto_service_settings.auto_service_settings import (
	AutoServiceSettings,
)
from auto_service_management.auto_service_management.integration.erpnext import (
	adapters,
	component_mapping,
	document_sync,
)


class TestPhase33SettingsCache(UnitTestCase):
	def tearDown(self):
		settings_cache.clear_settings_cache()
		frappe.db.rollback()

	def test_get_settings_reuses_native_document_cache(self):
		settings_cache.clear_settings_cache()
		settings = frappe._dict(doctype="Auto Service Settings", name="Auto Service Settings", company="Co")
		with patch.object(frappe.model.document, "get_doc", return_value=settings) as get_doc:
			first = settings_cache.get_settings()
			second = settings_cache.get_settings()

		self.assertIs(first, settings)
		self.assertIs(second, settings)
		get_doc.assert_called_once_with("Auto Service Settings")

	def test_settings_controller_explicitly_invalidates_cache_on_update_and_trash(self):
		doc = AutoServiceSettings({"doctype": "Auto Service Settings", "name": "Auto Service Settings"})
		with patch(
			"auto_service_management.auto_service_management.doctype.auto_service_settings.auto_service_settings.clear_settings_cache"
		) as invalidate:
			doc.on_update()
			doc.on_trash()

		self.assertEqual(invalidate.call_count, 2)

	def test_runtime_settings_reads_route_through_cache_boundary(self):
		for module in (adapters, component_mapping, document_sync):
			with self.subTest(module=module.__name__):
				source = inspect.getsource(module)
				self.assertNotIn('get_single("Auto Service Settings")', source)
				if module is adapters:
					self.assertIn("_get_cached_settings", source)
				else:
					self.assertIn("_get_settings", source)
