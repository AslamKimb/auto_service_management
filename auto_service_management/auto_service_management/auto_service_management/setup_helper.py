import frappe, json, os


def setup_workspace():
    """Create workspace from JSON, with forced module map rebuild."""
    # Flush ALL Redis caches to force fresh rebuild
    frappe.cache.flushall()
    
    # Force rebuild the module_app map
    frappe.client_cache.delete_value("installed_app_modules")
    frappe.cache.delete_value("app_modules")
    frappe.cache.delete_value("all_apps")
    
    # Rebuild module_app directly by reading files
    module_app = {}
    apps_file = os.path.join(frappe.local.sites_path, "apps.txt")
    all_apps = [line.strip() for line in open(apps_file) if line.strip()]
    print("All apps from apps.txt:", all_apps)
    
    for app in all_apps:
        modules_file = os.path.join(frappe.local.sites_path, "..", "apps", app, app, "modules.txt")
        if not os.path.exists(modules_file):
            # Try the bench path
            modules_file = f"/home/frappe/bench-home/frappe-bench/apps/{app}/{app}/modules.txt"
        if os.path.exists(modules_file):
            modules = [line.strip() for line in open(modules_file) if line.strip()]
            for mod in modules:
                scrubbed = frappe.scrub(mod)
                module_app[scrubbed] = app
                print(f"  Module: {mod} -> {scrubbed} -> {app}")
        else:
            print(f"  modules.txt not found for {app}: {modules_file}")
    
    frappe.local.module_app = module_app
    print("Module map:", list(module_app.keys()))
    
    if frappe.db.exists("Workspace", "Workshop Management"):
        print("Workspace already exists")
        return

    ws_path = "/home/frappe/bench-home/frappe-bench/apps/auto_service_management/auto_service_management/auto_service_management/workspace/workshop_management/workshop_management.json"
    with open(ws_path) as f:
        ws_data = json.load(f)

    # Filter out shortcuts/links/roles referencing non-existent entities
    valid_shortcuts = []
    for s in ws_data.get("shortcuts", []):
        link_to = s.get("link_to", "")
        stype = s.get("type", "")
        if stype == "DocType" and not frappe.db.exists("DocType", link_to):
            continue
        if stype == "Report" and not frappe.db.exists("Report", link_to):
            continue
        valid_shortcuts.append(s)
    ws_data["shortcuts"] = valid_shortcuts

    valid_links = []
    for l in ws_data.get("links", []):
        link_to = l.get("link_to", "")
        if l.get("link_type") == "DocType" and not frappe.db.exists("DocType", link_to):
            continue
        valid_links.append(l)
    ws_data["links"] = valid_links

    valid_roles = []
    for r in ws_data.get("roles", []):
        role_name = r.get("role", "")
        if not frappe.db.exists("Role", role_name):
            continue
        valid_roles.append(r)
    ws_data["roles"] = valid_roles

    doc = frappe.new_doc("Workspace")
    doc.update(ws_data)
    doc.insert(ignore_if_duplicate=True)
    frappe.db.commit()
    print("Workspace created:", doc.name)

    from auto_service_management.auto_service_management.desktop import create_app_desktop_icon
    create_app_desktop_icon()
    frappe.db.commit()
    print("Desktop icon ensured")

    frappe.clear_cache()
    print("Done!")
