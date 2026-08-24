"""Native Desk navigation for the Car Workshop application."""

import json

import frappe

from auto_service_management.auto_service_management.workspace_dashboard import WORKSPACE_HUBS

WORKSPACE_NAME = "Workshop Management"
WORKSPACE_LABEL = "Car Workshop"
APP_NAME = "auto_service_management"
APP_LOGO_URL = "/assets/auto_service_management/icons/desktop_icons/solid/car_workshop.svg"
ICON_NAME = "car-front"
LEGACY_NAVIGATION_LABELS = (WORKSPACE_NAME, "Auto Service Management")
WORKSPACE_ICON_LABELS = tuple(hub["label"] for hub in WORKSPACE_HUBS.values())
WORKSPACE_RECORD_NAMES = tuple(hub["workspace_name"] for hub in WORKSPACE_HUBS.values())
WORKSHOP_ROLES = frozenset(
	{
		"Workshop Manager",
		"Service Advisor",
		"Parts Interpreter",
		"Cashier",
		"Security Gate Officer",
		"Workshop Technician",
		"Accounts Manager",
		"Auto Service Admin",
		"System Manager",
	}
)


def check_app_permission():
	"""Return whether the current user may see the Car Workshop app launcher."""
	if frappe.session.user == "Administrator":
		return True
	return bool(WORKSHOP_ROLES.intersection(frappe.get_roles(frappe.session.user)))


def _ensure_workspace_record(workspace_name, hub):
	"""Keep app-owned Workspace routing fields compatible with native Desk."""
	if not frappe.db.exists("Workspace", workspace_name):
		return

	workspace = frappe.get_doc("Workspace", workspace_name)
	workspace.app = APP_NAME
	workspace.type = "Workspace"
	workspace.title = workspace_name
	workspace.label = hub["label"]
	workspace.icon = hub["icon"]
	workspace.flags.ignore_links = True
	workspace.save(ignore_permissions=True)


def _remove_legacy_navigation():
	"""Remove old direct/module navigation while retaining Workspace records."""
	for icon in frappe.get_all(
		"Desktop Icon",
		filters={"label": ["in", [*LEGACY_NAVIGATION_LABELS, *WORKSPACE_RECORD_NAMES]]},
		fields=["name", "standard", "app", "parent_icon"],
	):
		if icon.name == WORKSPACE_LABEL or icon.name in WORKSPACE_ICON_LABELS:
			continue
		if icon.name in LEGACY_NAVIGATION_LABELS or icon.standard or icon.app == APP_NAME:
			frappe.delete_doc("Desktop Icon", icon.name, ignore_permissions=True)

	for sidebar in (*LEGACY_NAVIGATION_LABELS, WORKSPACE_LABEL):
		if frappe.db.exists("Workspace Sidebar", sidebar):
			frappe.delete_doc("Workspace Sidebar", sidebar, ignore_permissions=True)


def _build_sidebar_link(item, idx, *, child=1):
	sidebar_item = {
		"label": item["label"],
		"type": "Link",
		"link_type": item["link_type"],
		"link_to": item["link_to"],
		"idx": idx,
		"child": child,
		"icon": item["icon"],
	}
	if item.get("is_query_report"):
		sidebar_item["is_query_report"] = item["is_query_report"]
	if item.get("route_options") is not None:
		sidebar_item["route_options"] = json.dumps(item["route_options"])
	return sidebar_item


def _ensure_workspace_sidebar(hub):
	"""Create one concise, app-owned sidebar for a workflow hub."""
	sidebar_name = hub["sidebar_name"]
	if frappe.db.exists("Workspace Sidebar", sidebar_name):
		sidebar = frappe.get_doc("Workspace Sidebar", sidebar_name)
	else:
		sidebar = frappe.new_doc("Workspace Sidebar")
		sidebar.name = sidebar_name

	sidebar.title = sidebar_name
	sidebar.app = APP_NAME
	sidebar.standard = 1
	sidebar.set("items", [])
	sidebar.append(
		"items",
		{
			"label": "Home",
			"type": "Link",
			"link_type": "Workspace",
			"link_to": hub["workspace_name"],
			"idx": 1,
			"child": 0,
			"icon": "house",
		},
	)
	sidebar.append(
		"items",
		{
			"label": hub["label"],
			"type": "Section Break",
			"idx": 2,
			"child": 0,
			"icon": hub["icon"],
		},
	)
	for idx, item in enumerate(hub["links"], start=3):
		sidebar.append("items", _build_sidebar_link(item, idx))

	if sidebar.is_new():
		sidebar.insert(ignore_permissions=True)
	else:
		sidebar.save(ignore_permissions=True)


def _ensure_parent_icon():
	"""Ensure Car Workshop is a native parent App icon."""
	if frappe.db.exists("Desktop Icon", WORKSPACE_LABEL):
		icon = frappe.get_doc("Desktop Icon", WORKSPACE_LABEL)
	else:
		icon = frappe.new_doc("Desktop Icon")
		icon.name = WORKSPACE_LABEL
		icon.label = WORKSPACE_LABEL

	icon.label = WORKSPACE_LABEL
	icon.icon_type = "App"
	icon.link_type = "External"
	icon.link = "/desk/workshop-management"
	icon.link_to = None
	icon.parent_icon = None
	icon.app = APP_NAME
	icon.logo_url = APP_LOGO_URL
	icon.icon = ICON_NAME
	icon.hidden = 0
	icon.standard = 1
	icon.idx = 0
	icon.save(ignore_permissions=True)


def _ensure_child_icon(hub, idx):
	"""Ensure a hub is a child Workspace Sidebar icon under Car Workshop."""
	label = hub["label"]
	if frappe.db.exists("Desktop Icon", label):
		icon = frappe.get_doc("Desktop Icon", label)
	else:
		icon = frappe.new_doc("Desktop Icon")
		icon.name = label
		icon.label = label

	icon.label = label
	icon.icon_type = "Link"
	icon.link_type = "Workspace Sidebar"
	icon.link = None
	icon.link_to = hub["sidebar_name"]
	icon.parent_icon = WORKSPACE_LABEL
	icon.app = APP_NAME
	icon.icon = hub["icon"]
	icon.logo_url = hub["logo_url"]
	icon.hidden = 0
	icon.standard = 1
	icon.idx = idx
	icon.set("roles", [])
	for role in hub["roles"]:
		icon.append("roles", {"role": role})
	icon.save(ignore_permissions=True)


def create_workspace_desktop_icon():
	"""Converge the parent App and eight child icons idempotently."""
	_ensure_parent_icon()

	# Frappe's standard workspace sync may create icons named after Workspace
	# records. Remove only those app-owned/standard duplicates; the Workspace
	# records themselves remain the authoritative routes.
	for stale in frappe.get_all(
		"Desktop Icon",
		filters={"label": ["in", WORKSPACE_RECORD_NAMES]},
		fields=["name", "standard", "app"],
	):
		if stale.name not in WORKSPACE_ICON_LABELS and (stale.standard or stale.app == APP_NAME):
			frappe.delete_doc("Desktop Icon", stale.name, ignore_permissions=True)

	for idx, hub in enumerate(WORKSPACE_HUBS.values(), start=1):
		_ensure_child_icon(hub, idx)

	# Remove the retired direct Link icon if it survived a previous release.
	for icon in frappe.get_all(
		"Desktop Icon",
		filters={"label": WORKSPACE_LABEL, "icon_type": "Link"},
		pluck="name",
	):
		frappe.delete_doc("Desktop Icon", icon, ignore_permissions=True)

	frappe.cache.delete_key("desktop_icons")
	frappe.clear_cache()


def setup_desktop():
	"""Sync app-owned Workspaces, sidebars, and native desktop hierarchy."""
	for hub in WORKSPACE_HUBS.values():
		_ensure_workspace_record(hub["workspace_name"], hub)
		_ensure_workspace_sidebar(hub)
	_remove_legacy_navigation()
	create_workspace_desktop_icon()


def remove_auto_generated_sidebar(bootinfo):
	"""Keep generated module sidebars out of the Car Workshop boot payload."""
	for sidebar in ("auto service management", "workshop management"):
		bootinfo.workspace_sidebar_item.pop(sidebar, None)
