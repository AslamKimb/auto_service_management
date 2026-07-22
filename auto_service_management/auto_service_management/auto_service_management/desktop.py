"""Desk desktop visibility for the Car Workshop entry."""

import json

import frappe

from auto_service_management.auto_service_management.workspace_dashboard import (
	WORKSPACE_LINK_CARDS,
	WORKSPACE_SIDEBAR_HOME,
	WORKSPACE_SIDEBAR_SECTIONS,
)

WORKSPACE_NAME = "Workshop Management"
WORKSPACE_LABEL = "Car Workshop"
APP_NAME = "auto_service_management"
ICON_NAME = "car-front"


def _ensure_workspace_app_field():
	"""Set the ``app`` field on the Workspace if it is NULL.

	Required for Frappe v16 desk routing — without it, the workspace
	doesn't appear in any app's workspace list and the SPA 404s.
	"""
	frappe.db.set_value(
		"Workspace",
		WORKSPACE_NAME,
		"app",
		APP_NAME,
		update_modified=False,
	)


def _ensure_workspace_type_field():
	"""Set the ``type`` field on the Workspace if it is NULL.

	Required for Frappe v16 — ``type`` is a required field on Workspace.
	"""
	frappe.db.set_value(
		"Workspace",
		WORKSPACE_NAME,
		"type",
		"Workspace",
		update_modified=False,
	)


def _ensure_workspace_label():
	"""Keep the underlying workspace doc stable but expose a shorter label."""
	workspace = frappe.get_doc("Workspace", WORKSPACE_NAME)
	workspace.title = WORKSPACE_LABEL
	workspace.label = WORKSPACE_LABEL
	workspace.icon = ICON_NAME
	workspace.save(ignore_permissions=True)


def _ensure_workspace_sidebar():
	"""Rebuild the app-owned Workspace Sidebar for the workshop workspace.

	Frappe v16's desk loads workspace route resolution from Workspace
	Sidebar records. Without it, clicking the app icon gives a 404.
	The app owns this sidebar explicitly so migrate/tests converge existing
	sites to the approved grouped navigation.
	"""
	sidebar_name = WORKSPACE_LABEL
	module_sidebar_name = "Auto Service Management"
	legacy_sidebar_name = WORKSPACE_NAME
	if not frappe.db.exists("Workspace Sidebar", sidebar_name) and frappe.db.exists(
		"Workspace Sidebar", module_sidebar_name
	):
		frappe.rename_doc("Workspace Sidebar", module_sidebar_name, sidebar_name, force=True)
	if not frappe.db.exists("Workspace Sidebar", sidebar_name) and frappe.db.exists(
		"Workspace Sidebar", legacy_sidebar_name
	):
		frappe.rename_doc("Workspace Sidebar", legacy_sidebar_name, sidebar_name, force=True)
	if frappe.db.exists("Workspace Sidebar", sidebar_name):
		sidebar = frappe.get_doc("Workspace Sidebar", sidebar_name)
	else:
		sidebar = frappe.new_doc("Workspace Sidebar")
		sidebar.name = sidebar_name

	sidebar.title = sidebar_name
	sidebar.app = APP_NAME
	sidebar.standard = 1
	sidebar.set("items", [])

	for item in _get_workspace_sidebar_items():
		sidebar.append("items", item)

	if sidebar.is_new():
		sidebar.insert(ignore_permissions=True)
	else:
		sidebar.save(ignore_permissions=True)

	frappe.clear_cache()


def _build_sidebar_link(item, idx, *, child=0):
	sidebar_item = {
		"label": item["label"],
		"type": "Link",
		"link_type": item["link_type"],
		"link_to": item["link_to"],
		"idx": idx,
		"child": child,
	}
	if item.get("is_query_report"):
		sidebar_item["is_query_report"] = item["is_query_report"]
	if item.get("route_options") is not None:
		sidebar_item["route_options"] = json.dumps(item["route_options"])
	return sidebar_item


def _get_workspace_sidebar_items():
	items = [_build_sidebar_link(WORKSPACE_SIDEBAR_HOME, 1)]
	idx = 2

	for section_label in WORKSPACE_LINK_CARDS:
		items.append({"label": section_label, "type": "Section Break", "idx": idx})
		idx += 1
		for item in WORKSPACE_SIDEBAR_SECTIONS[section_label]:
			items.append(_build_sidebar_link(item, idx, child=1))
			idx += 1

	return items


def create_workspace_desktop_icon():
	"""Expose Car Workshop as one directly routed Desk icon.

	Called from ``after_install``, ``after_migrate``, and ``before_tests``
	hooks so fresh installs and existing deployments converge automatically.
	"""
	for stale in frappe.get_all("Desktop Icon", filters={"icon_type": "App", "app": APP_NAME}, pluck="name"):
		frappe.delete_doc("Desktop Icon", stale, ignore_permissions=True)
	for stale in frappe.get_all(
		"Desktop Icon",
		filters={"label": ["in", [WORKSPACE_NAME, WORKSPACE_LABEL]], "app": APP_NAME},
		fields=["name", "icon_type"],
	):
		if stale.icon_type != "Link" or stale.name != WORKSPACE_LABEL:
			frappe.delete_doc("Desktop Icon", stale.name, ignore_permissions=True)

	existing = frappe.db.exists(
		"Desktop Icon",
		{"label": WORKSPACE_LABEL, "icon_type": "Link"},
	)
	if existing:
		frappe.db.set_value(
			"Desktop Icon",
			existing,
			{
				"app": APP_NAME,
				"label": WORKSPACE_LABEL,
				"hidden": 0,
				"icon": ICON_NAME,
				"link_type": "Workspace Sidebar",
				"link_to": WORKSPACE_LABEL,
				"parent_icon": None,
				"standard": 1,
			},
			update_modified=False,
		)
	else:
		icon = frappe.new_doc("Desktop Icon")
		icon.label = WORKSPACE_LABEL
		icon.icon = ICON_NAME
		icon.icon_type = "Link"
		icon.link_type = "Workspace Sidebar"
		icon.link_to = WORKSPACE_LABEL
		icon.app = APP_NAME
		icon.standard = 1
		icon.idx = 0
		icon.insert(ignore_if_duplicate=True, ignore_links=True)

	frappe.cache.delete_key("desktop_icons")
	frappe.clear_cache()


def setup_desktop():
	"""Run all desktop setup steps: icon, workspace fields, sidebar.

	Called from ``after_install``, ``after_migrate``, and ``before_tests``
	/hooks so fresh installs, existing deployments, and test runs all get
	the full desk setup automatically.

	Order matters: the workspace and sidebar must exist before their icon.
	"""
	_ensure_workspace_app_field()
	_ensure_workspace_type_field()
	_ensure_workspace_label()
	_ensure_workspace_sidebar()
	create_workspace_desktop_icon()


def remove_auto_generated_sidebar(bootinfo):
	"""Keep Frappe's generated module sidebar out of the DMS Desk boot payload."""
	bootinfo.workspace_sidebar_item.pop("auto service management", None)
