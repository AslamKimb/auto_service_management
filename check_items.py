import frappe
frappe.connect()
groups = frappe.get_all("Item Group", limit_page_length=5)
print("Item Groups:", [g.name for g in groups])
items = frappe.get_all("Item", limit_page_length=5)
print("Items:", [i.name for i in items])
frappe.destroy()
