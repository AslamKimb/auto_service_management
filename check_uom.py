import frappe
frappe.init("auto-service-test.localhost", sites_path="/home/frappe/bench-home/frappe-bench/sites")
frappe.connect()
uoms = frappe.get_all("UOM", limit_page_length=10)
print("UOMs:", [u.name for u in uoms])
frappe.destroy()
