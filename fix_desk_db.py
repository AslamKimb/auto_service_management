import frappe
frappe.init("auto-service.localhost", sites_path="/home/frappe/bench-home/frappe-bench/sites")
frappe.connect()

from auto_service_management.auto_service_management.desktop import setup_desktop
setup_desktop()

frappe.db.commit()
print("setup_desktop() completed successfully")

# Verify
print("\n=== Verification ===")
icon = frappe.db.sql("SELECT name, link_type, link_to, app FROM `tabDesktop Icon` WHERE app='auto_service_management'", as_dict=True)
print("Desktop Icons:", icon)

ws = frappe.db.sql("SELECT name, app, type FROM `tabWorkspace` WHERE name='Workshop Management'", as_dict=True)
print("Workspace:", ws)

sidebar = frappe.db.sql("SELECT name, app FROM `tabWorkspace Sidebar` WHERE name='Workshop Management'", as_dict=True)
print("Sidebar:", sidebar)

sidebar_items = frappe.db.sql("SELECT label, link_type, link_to FROM `tabWorkspace Sidebar Item` WHERE parent='Workshop Management'", as_dict=True)
print("Sidebar Items:", sidebar_items)

frappe.destroy()
