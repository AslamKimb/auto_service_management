"""Replace first-generation app print layouts without taking future edits."""

import json

import frappe


def execute():
	from auto_service_management.auto_service_management.printing import (
		DMS_PRINT_FORMATS,
		WORKSHOP_PRINT_FORMATS,
		WORKSHOP_PRINT_TEMPLATES,
		_custom_format_html,
	)

	for name, template in WORKSHOP_PRINT_TEMPLATES.items():
		print_format = f"DMS Editable - {name}"
		current = frappe.db.get_value(
			"Print Format",
			print_format,
			["custom_format", "print_format_builder"],
			as_dict=True,
		)
		# Only migrate the old app-generated builder copy. A user who has
		# already switched this record to a custom format owns that HTML now.
		if current and not current.custom_format and current.print_format_builder:
			frappe.db.set_value(
				"Print Format",
				print_format,
				{
					"custom_format": 1,
					"print_format_builder": 0,
					"format_data": None,
					"html": _custom_format_html(template),
				},
				update_modified=False,
			)

	# Frappe's standard renderer recognizes HTML, not the old builder label
	# "Custom HTML". Normalize the other app-owned builder copies as well.
	legacy_builder_names = [name for name, _doc_type, *_rest in DMS_PRINT_FORMATS]
	legacy_builder_names.extend(
		name for name, _doc_type in WORKSHOP_PRINT_FORMATS if name not in WORKSHOP_PRINT_TEMPLATES
	)
	for name in legacy_builder_names:
		print_format = f"DMS Editable - {name}"
		current = frappe.db.get_value("Print Format", print_format, "format_data")
		if not current:
			continue
		try:
			layout = json.loads(current)
		except (TypeError, ValueError):
			continue
		changed = False
		for field in layout:
			if field.get("fieldtype") == "Custom HTML":
				field["fieldtype"] = "HTML"
				changed = True
		if changed:
			frappe.db.set_value(
				"Print Format",
				print_format,
				"format_data",
				json.dumps(layout),
				update_modified=False,
			)
