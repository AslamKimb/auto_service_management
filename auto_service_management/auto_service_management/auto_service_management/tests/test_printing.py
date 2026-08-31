import json
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from auto_service_management.auto_service_management.doctype.repair_job.repair_job import RepairJob
from auto_service_management.auto_service_management.printing import (
	_builder_format_data,
	_company_address,
	_damage_markers,
	get_job_card_context,
	normalize_logo_url,
	resolve_logo_url,
)


class TestPrinting(UnitTestCase):
	def test_logo_precedence_is_company_then_website_then_navbar_then_banner(self):
		self.assertEqual(
			resolve_logo_url(
				"/files/company.svg",
				"/files/app.svg",
				"/private/files/navbar.svg",
				"/files/banner.svg",
				"https://dms.test",
			),
			"https://dms.test/files/company.svg",
		)
		self.assertEqual(
			resolve_logo_url(
				None,
				"/files/app.svg",
				"/private/files/navbar.svg",
				"/files/banner.svg",
				"https://dms.test",
			),
			"https://dms.test/files/app.svg",
		)
		self.assertEqual(
			resolve_logo_url(
				None,
				None,
				"/private/files/navbar.svg",
				"/files/banner.svg",
				"https://dms.test",
			),
			"https://dms.test/private/files/navbar.svg",
		)
		self.assertEqual(
			resolve_logo_url(None, None, None, "/files/banner.svg", "https://dms.test"),
			"https://dms.test/files/banner.svg",
		)
		self.assertIsNone(resolve_logo_url(None, None, None, None, "https://dms.test"))

	def test_logo_urls_preserve_absolute_and_data_urls(self):
		self.assertEqual(
			normalize_logo_url("https://cdn.test/logo.svg", "https://dms.test"), "https://cdn.test/logo.svg"
		)
		self.assertEqual(
			normalize_logo_url("data:image/svg+xml;base64,abc", "https://dms.test"),
			"data:image/svg+xml;base64,abc",
		)

	def test_company_address_returns_location_address_and_contact_fields(self):
		with patch(
			"frappe.get_all",
			side_effect=[
				["ADDR-1"],
				[
					frappe._dict(
						address_line1="Plot 1",
						address_line2="Industrial Area",
						city="Kampala",
						state="Central",
						country="Uganda",
						pincode="256",
						phone="0700000000",
						email_id="office@example.test",
					)
				],
			],
		):
			address = _company_address("Garage")

		self.assertEqual(address.location, "Kampala, Central, Uganda")
		self.assertEqual(address.address, "Plot 1, Industrial Area, Kampala, Central, Uganda, 256")
		self.assertEqual(address.phone, "0700000000")
		self.assertEqual(address.email, "office@example.test")

	def test_empty_logo_does_not_use_vehicle_diagram(self):
		logo = resolve_logo_url(None, None, None, None, "https://dms.test")
		self.assertIsNone(logo)

	def test_builder_layout_uses_editable_custom_html(self):
		data = _builder_format_data(template="estimate_summary")
		self.assertIn('"fieldtype": "Custom HTML"', data)
		self.assertIn("estimate_summary.html", data)

	def test_builder_layout_has_a_printable_fallback(self):
		data = _builder_format_data()
		self.assertIn('"fieldtype": "Custom HTML"', data)
		self.assertIn("{{ doc.name }}", data)

	def test_job_card_snapshot_is_write_once(self):
		job = RepairJob(
			{
				"doctype": "Repair Job",
				"customer": "Customer-1",
				"customer_vehicle": "Vehicle-1",
			}
		)
		snapshot = {"customer": {"name": "Frozen Customer"}, "vehicle": {"registration_number": "UAA 001A"}}
		with patch(
			"auto_service_management.auto_service_management.printing.build_job_card_snapshot",
			return_value=snapshot,
		) as builder:
			job.capture_job_card_snapshot()
			job.customer = "Customer-2"
			job.capture_job_card_snapshot()

		self.assertEqual(json.loads(job.job_card_snapshot), snapshot)
		builder.assert_called_once_with("Customer-1", "Vehicle-1")

	def test_job_card_context_prefers_snapshot_and_reads_terms(self):
		doc = frappe._dict(
			customer="Customer-1",
			customer_vehicle="Vehicle-1",
			job_card_snapshot=json.dumps(
				{
					"captured_at": "2026-08-23 10:00:00",
					"customer": {"name": "Frozen Customer", "address": "Frozen Address"},
					"vehicle": {"registration_number": "UAA 001A"},
				}
			),
			walkaround_inspection=None,
			creation="2026-08-22 10:00:00",
		)
		with (
			patch(
				"auto_service_management.auto_service_management.printing._customer_values",
				return_value={"name": "Live Customer", "address": "Live Address", "account": "Customer-1"},
			),
			patch(
				"auto_service_management.auto_service_management.printing._vehicle_values",
				return_value={"registration_number": "UAA 999Z", "account": "Vehicle-1"},
			),
			patch(
				"auto_service_management.auto_service_management.printing._damage_markers",
				return_value=[],
			),
			patch("frappe.db.get_single_value", return_value="Approved workshop terms"),
		):
			context = get_job_card_context(doc)

		self.assertEqual(context["customer"]["name"], "Frozen Customer")
		self.assertEqual(context["customer"]["address"], "Frozen Address")
		self.assertEqual(context["vehicle"]["registration_number"], "UAA 001A")
		self.assertEqual(context["terms"], "Approved workshop terms")
		self.assertEqual(context["received_on"], "2026-08-23 10:00:00")

	def test_damage_markers_use_vehicle_damage_mark_fields(self):
		with (
			patch("frappe.db.exists", return_value=True),
			patch(
				"frappe.get_all",
				return_value=[
					frappe._dict(
						damage_area="Front",
						damage_type="Dent",
						severity="Moderate",
						description="Bonnet edge",
					)
				],
			),
		):
			markers = _damage_markers("WI-1")

		self.assertEqual(markers[0]["area"], "Front")
		self.assertEqual(markers[0]["description"], "Bonnet edge")
		self.assertEqual(markers[0]["number"], 1)
