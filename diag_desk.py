import frappe
frappe.init("auto-service.localhost", sites_path="/home/frappe/bench-home/frappe-bench/sites")
frappe.connect()

print("=== Module Map ===")
print(frappe.local.app_modules.get("auto_service_management"))

print("\n=== DocType Count ===")
print(frappe.db.count("DocType", {"module": "Auto Service Management"}))

print("\n=== Desktop Icons (all columns) ===")
try:
    icons = frappe.db.sql("SELECT * FROM `tabDesktop Icon`", as_dict=True)
    if icons:
        print("Columns:", list(icons[0].keys()))
        for i in icons:
            print({k: v for k, v in i.items() if v and k in ('name', 'link_type', 'link_to', 'module_name', 'app', 'color', 'icon')})
    else:
        print("  (none)")
except Exception as e:
    print("Error:", e)

print("\n=== Workspaces ===")
ws = frappe.db.sql("SELECT name, app, module, type FROM `tabWorkspace` WHERE module='Auto Service Management'", as_dict=True)
for w in ws:
    print(w)
if not ws:
    print("  (none found)")

print("\n=== All Workspaces (any module) ===")
all_ws = frappe.db.sql("SELECT name, app, module FROM `tabWorkspace`", as_dict=True)
for w in all_ws:
    print(w)

print("\n=== Workspace Sidebar ===")
try:
    sidebar = frappe.db.sql("SELECT name, app FROM `tabWorkspace Sidebar`", as_dict=True)
    for s in sidebar:
        print(s)
    if not sidebar:
        print("  (none found)")
except Exception as e:
    print("Error:", e)

print("\n=== Workspace Sidebar Items ===")
try:
    items = frappe.db.sql("SELECT label, link_type, link_to, parent FROM `tabWorkspace Sidebar Item`", as_dict=True)
    for i in items:
        print(i)
    if not items:
        print("  (none found)")
except Exception as e:
    print("Error:", e)

frappe.destroy()
