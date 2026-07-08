import pathlib

path = pathlib.Path(r'C:\Users\user\Documents\Coded\DMS\auto_service_management\auto_service_management\auto_service_management\doctype\repair_job\repair_job.py')
content = path.read_text(encoding='utf-8')

# 1. Replace calculate_totals to include labour summary computation
old = '	def calculate_totals(self):\n\t\ttotal = 0\n\t\tfor line in self.service_lines or []:\n\t\t\tline.calculate_amount()\n\t\t\ttotal += line.amount or 0\n\t\tself.total_amount = total'

new = """\tdescribe calculate_totals(self):
\t\ttotal = 0
\t\tlabour_hours = 0
\t\tlabour_amount = 0
\t\tfor line in self.service_lines or []:
\t\t\tline.calculate_amount()
\t\t\ttotal += line.amount or 0
\t\t\tif line.service_type == "Labour":
\t\t\t\tlabour_hours += line.quantity or 0
\t\t\t\tlabour_amount += line.amount or 0
\t\tself.total_amount = total
\t\tself.labour_total_hours = labour_hours
\t\tself.labour_total_amount = labour_amount

\tdef get_labour_summary(self):
\t\t\"\"\"Return structured labour summary grouped by technician.\"\"\"
\t\tlines = []
\t\ttotal_hours = 0
\t\ttotal_amount = 0
\t\tfor line in self.service_lines or []:
\t\t\tif line.service_type != "Labour":
\t\t\t\tcontinue
\t\t\tentry = {
\t\t\t\t"technician": line.assigned_to,
\t\t\t\t"description": line.service_description,
\t\t\t\t"hours": line.quantity or 0,
\t\t\t\t"amount": line.amount or 0,
\t\t\t}
\t\t\tlines.append(entry)
\t\t\ttotal_hours += entry["hours"]
\t\t\ttotal_amount += entry["amount"]
\t\treturn {"lines": lines, "total_hours": total_hours, "total_amount": total_amount}"""

new = new.replace('describe ', 'def ')
content = content.replace(old, new)
path.write_text(content, encoding='utf-8')
print("Step 1 done")
