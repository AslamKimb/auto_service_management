import pathlib

path = pathlib.Path(r'C:\Users\user\Documents\Coded\DMS\auto_service_management\auto_service_management\auto_service_management\integration\erpnext\adapters.py')
content = path.read_text(encoding='utf-8')

# 1. Replace create_material_request to track quantities
old_mr = '''def create_material_request(repair_job):
\t"""Create a Material Request for parts needed by this Repair Job.

\tReturns the Material Request name.
\t"""
\tsettings = get_settings()
\titems = []
\tfor line in repair_job.service_lines:
\t\tif line.service_type == "Parts" and line.item_code:
\t\t\titems.append(
\t\t\t\t{
\t\t\t\t\t"item_code": line.item_code,
\t\t\t\t\t"qty": line.quantity,
\t\t\t\t\t"warehouse": getattr(settings, "source_warehouse", None),
\t\t\t\t\t"schedule_date": frappe.utils.today(),
\t\t\t\t}
\t\t\t)

\tif not items:
\t\tfrappe.throw(_("No parts service lines to request."))

\tmr = frappe.get_doc(
\t\t{
\t\t\t"doctype": "Material Request",
\t\t\t"material_request_type": "Material Issue",
\t\t\t"company": settings.company,
\t\t\t"items": items,
\t\t}
\t)
\tmr.insert(ignore_permissions=True)
\treturn mr.name'''

new_mr = '''def create_material_request(repair_job):
\t"""Create a Material Request for parts needed by this Repair Job.

\tTracks requested quantities on each Parts service line.
\tReturns the Material Request name.
\t"""
\tsettings = get_settings()
\titems = []
\teligible_lines = []
\tfor line in repair_job.service_lines:
\t\tif line.service_type == "Parts" and line.item_code:
\t\t\titems.append(
\t\t\t\t{
\t\t\t\t\t"item_code": line.item_code,
\t\t\t\t\t"qty": line.quantity,
\t\t\t\t\t"warehouse": getattr(settings, "source_warehouse", None),
\t\t\t\t\t"schedule_date": frappe.utils.today(),
\t\t\t\t}
\t\t\t)
\t\t\teligible_lines.append(line)

\tif not items:
\t\tfrappe.throw(_("No parts service lines to request."))

\tmr = frappe.get_doc(
\t\t{
\t\t\t"doctype": "Material Request",
\t\t\t"material_request_type": "Material Issue",
\t\t\t"company": settings.company,
\t\t\t"items": items,
\t\t}
\t)
\tmr.insert(ignore_permissions=True)

\t# Track requested quantities on child lines
\tfor line in eligible_lines:
\t\tfrappe.db.set_value(
\t\t\t"Repair Service Line",
\t\t\tline.name,
\t\t\t{
\t\t\t\t"requested_qty": line.quantity,
\t\t\t\t"material_request": mr.name,
\t\t\t\t"stock_request_status": "Requested",
\t\t\t},
\t\t)

\treturn mr.name'''

content = content.replace(old_mr, new_mr)

# 2. Add create_stock_entry_for_material_issue before on_invoice_submit
old_hook = '''# ---------------------------------------------------------------------------
# Invoice Hook (called from doc_events)
# ---------------------------------------------------------------------------'''

new_se = '''# ---------------------------------------------------------------------------
# Stock Entry (Material Issue)
# ---------------------------------------------------------------------------


def create_stock_entry_for_material_issue(repair_job):
\t"""Create a Stock Entry (Material Issue) for requested Parts lines.

\tOnly covers lines where stock_request_status == "Requested".
\tUpdates issued_qty and stock_request_status on each line.
\tReturns the Stock Entry name.
\t"""
\tsettings = get_settings()
\titems = []
\teligible_lines = []
\tfor line in repair_job.service_lines:
\t\tif (
\t\t\tline.service_type == "Parts"
\t\t\tand line.item_code
\t\t\tand line.stock_request_status == "Requested"
\t\t):
\t\t\titems.append(
\t\t\t\t{
\t\t\t\t\t"item_code": line.item_code,
\t\t\t\t\t"qty": line.quantity,
\t\t\t\t\t"warehouse": getattr(settings, "source_warehouse", None),
\t\t\t\t}
\t\t\t)
\t\t\teligible_lines.append(line)

\tif not items:
\t\tfrappe.throw(_("No requested Parts lines to issue."))

\tse = frappe.get_doc(
\t\t{
\t\t\t"doctype": "Stock Entry",
\t\t\t"stock_entry_type": "Material Issue",
\t\t\t"company": settings.company,
\t\t\t"items": items,
\t\t}
\t)
\tse.insert(ignore_permissions=True)

\t# Update issued quantities on child lines
\tfor line in eligible_lines:
\t\tfrappe.db.set_value(
\t\t\t"Repair Service Line",
\t\t\tline.name,
\t\t\t{
\t\t\t\t"issued_qty": line.quantity,
\t\t\t\t"stock_entry": se.name,
\t\t\t\t"stock_request_status": "Fully Issued",
\t\t\t},
\t\t)

\treturn se.name


# ---------------------------------------------------------------------------
# Invoice Hook (called from doc_events)
# ---------------------------------------------------------------------------'''

content = content.replace(old_hook, new_se)

path.write_text(content, encoding='utf-8')
print("Adapters updated: MR tracking + Stock Entry adapter added")
