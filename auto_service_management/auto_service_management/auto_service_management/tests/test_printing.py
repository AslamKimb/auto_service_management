from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.printing import (
	_builder_format_data,
	normalize_logo_url,
	resolve_logo_url,
)


class TestPrinting(UnitTestCase):
	def test_logo_precedence_is_company_then_website(self):
		self.assertEqual(
			resolve_logo_url("/files/company.svg", "/files/app.svg", "/files/banner.svg", "https://dms.test"),
			"https://dms.test/files/company.svg",
		)
		self.assertEqual(
			resolve_logo_url(None, "/files/app.svg", "/files/banner.svg", "https://dms.test"),
			"https://dms.test/files/app.svg",
		)
		self.assertEqual(
			resolve_logo_url(None, None, "/files/banner.svg", "https://dms.test"),
			"https://dms.test/files/banner.svg",
		)

	def test_logo_urls_preserve_absolute_and_data_urls(self):
		self.assertEqual(normalize_logo_url("https://cdn.test/logo.svg", "https://dms.test"), "https://cdn.test/logo.svg")
		self.assertEqual(normalize_logo_url("data:image/svg+xml;base64,abc", "https://dms.test"), "data:image/svg+xml;base64,abc")

	def test_empty_logo_is_not_replaced_with_workspace_icon(self):
		self.assertIsNone(resolve_logo_url(None, None, None, "https://dms.test"))

	def test_builder_layout_uses_editable_custom_html(self):
		data = _builder_format_data(template="estimate_summary")
		self.assertIn('"fieldtype": "Custom HTML"', data)
		self.assertIn("estimate_summary.html", data)

	def test_builder_layout_has_a_printable_fallback(self):
		data = _builder_format_data()
		self.assertIn('"fieldtype": "Custom HTML"', data)
		self.assertIn("{{ doc.name }}", data)
