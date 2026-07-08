import frappe
frappe.init("auto-service.localhost", sites_path="/home/frappe/bench-home/frappe-bench/sites")
frappe.connect()

print("=== Desktop Icons ===")
icons = frappe.db.sql("SELECT name, link_type, link_to, app, icon_type FROM `tabDesktop Icon` WHERE app='auto_service_management'", as_dict=True)
for i in icons:
    print(i)
if not icons:
    print("  (NONE!)")

print("\n=== All Desktop Icons with auto_service in any field ===")
all_icons = frappe.db.sql("SELECT name, link_type, link_to, app, icon_type FROM `tabDesktop Icon` WHERE name LIKE '%Auto%' OR app LIKE '%auto%'", as_dict=True)
for i in all_icons:
    print(i)
if not all_icons:
    print("  (none)")

print("\n=== Workspace ===")
ws = frappe.db.sql("SELECT name, app, type FROM `tabWorkspace` WHERE name='Workshop Management'", as_dict=True)
for w in ws:
    print(w)

print("\n=== Sidebar ===")
sb = frappe.db.sql("SELECT name, app FROM `tabWorkspace Sidebar` WHERE name='Workshop Management'", as_dict=True)
for s in sb:
    print(s)
if not sb:
    print("  (none)")

frappe.destroy()
