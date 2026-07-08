import pathlib

path = pathlib.Path(r'C:\Users\user\Documents\Coded\DMS\auto_service_management\auto_service_management\auto_service_management\doctype\repair_job\repair_job.py')
content = path.read_text(encoding='utf-8')

# 2. Add double-billing guard to create_sales_invoice
old_si = """\t@frappe.whitelist()
\tdef create_sales_invoice(self):
\t\tself._require_write_permission()
\t\tfrom auto_service_management.auto_service_management.integration.erpnext.adapters import (
\t\t\tcreate_sales_invoice,
\t\t)

\t\tsi_name = create_sales_invoice(self)
\t\tself.reload()
\t\tif self.job_status != "Invoiced":
\t\t\tself._transition_to("Invoiced")
\t\t\tself.save()
\t\tself.reload()
\t\treturn si_name"""

new_si = """\t@frappe.whitelist()
\tdef create_sales_invoice(self):
\t\t\"\"\"Create Sales Invoice. Blocks double-billing.\"\"\"
\t\tself._require_write_permission()
\t\t# Guard: prevent double-billing
\t\tif self.sales_invoice:
\t\t\tfrappe.throw(
\t\t\t\t_(
\t\t\t\t\t"Sales Invoice '{0}' already exists for this Repair Job. "
\t\t\t\t\t"Cannot create a duplicate invoice."
\t\t\t\t).format(self.sales_invoice)
\t\t\t)

\t\tfrom auto_service_management.auto_service_management.integration.erpnext.adapters import (
\t\t\tcreate_sales_invoice,
\t\t)

\t\tsi_name = create_sales_invoice(self)
\t\tself.reload()
\t\tif self.job_status != "Invoiced":
\t\t\tself._transition_to("Invoiced")
\t\t\tself.save()
\t\tself.reload()
\t\treturn si_name"""

content = content.replace(old_si, new_si)

# 3. Add duplicate MR guard to create_material_request
old_mr = """\t@frappe.whitelist()
\tdef create_material_request(self):
\t\tself._require_write_permission()
\t\tfrom auto_service_management.auto_service_management.integration.erpnext.adapters import (
\t\t\tcreate_material_request,
\t\t)

\t\tmr_name = create_material_request(self)
\t\treturn mr_name"""

new_mr = """\t@frappe.whitelist()
\tdef create_material_request(self):
\t\t\"\"\"Create Material Request for Parts lines. Blocks duplicate requests.\"\"\"
\t\tself._require_write_permission()
\t\t# Guard: block if any eligible Parts line already has an active MR
\t\tfor line in self.service_lines or []:
\t\t\tif (
\t\t\t\tline.service_type == "Parts"
\t\t\t\tand line.item_code
\t\t\t\tand line.status in ("Approved", "Completed")
\t\t\t\tand line.stock_request_status == "Requested"
\t\t\t):
\t\t\t\tfrappe.throw(
\t\t\t\t\t_(
\t\t\t\t\t\t"Material Request already exists for line '{0}' (status: Requested). "
\t\t\t\t\t\t"Cancel the existing request before creating a new one."
\t\t\t\t\t).format(line.service_description or line.name)
\t\t\t\t)

\t\tfrom auto_service_management.auto_service_management.integration.erpnext.adapters import (
\t\t\tcreate_material_request,
\t\t)

\t\tmr_name = create_material_request(self)
\t\treturn mr_name"""

content = content.replace(old_mr, new_mr)

# 4. Add create_stock_entry method after create_material_request
new_se = """

\t@frappe.whitelist()
\tdef create_stock_entry(self):
\t\t\"\"\"Create Stock Entry (Material Issue) for requested Parts lines.\"\"\"
\t\tself._require_write_permission()
\t\tfrom auto_service_management.auto_service_management.integration.erpnext.adapters import (
\t\t\tcreate_stock_entry_for_material_issue,
\t\t)

\t\tse_name = create_stock_entry_for_material_issue(self)
\t\tself.reload()
\t\treturn se_name"""

content = content.replace(new_mr, new_mr + new_se)

# 5. Add get_shortage_report helper before internal helpers
old_helpers = """\t# ------------------------------------------------------------------ #
\t#  Internal helpers                                                    #
\t# ------------------------------------------------------------------ #"""

new_helpers = """\t# ------------------------------------------------------------------ #
\t#  Reporting helpers                                                   #
\t# ------------------------------------------------------------------ #

\tdef get_shortage_report(self):
\t\t\"\"\"Return Parts lines where issued_qty < quantity (shortage).\"\"\"
\t\tshortages = []
\t\tfor line in self.service_lines or []:
\t\t\tif line.service_type != "Parts":
\t\t\t\tcontinue
\t\t\tissued = line.issued_qty or 0
\t\t\tneeded = line.quantity or 0
\t\t\tif needed > 0 and issued < needed:
\t\t\t\tshortages.append({
\t\t\t\t\t"line_name": line.name,
\t\t\t\t\t"description": line.service_description,
\t\t\t\t\t"item_code": line.item_code,
\t\t\t\t\t"requested_qty": line.requested_qty or 0,
\t\t\t\t\t"issued_qty": issued,
\t\t\t\t\t"needed_qty": needed,
\t\t\t\t\t"shortage_qty": needed - issued,
\t\t\t\t})
\t\treturn shortages

\t# ------------------------------------------------------------------ #
\t#  Internal helpers                                                    #
\t# ------------------------------------------------------------------ #"""

content = content.replace(old_helpers, new_helpers)

path.write_text(content, encoding='utf-8')
print("Steps 2-5 done: all controller guards and methods added")
