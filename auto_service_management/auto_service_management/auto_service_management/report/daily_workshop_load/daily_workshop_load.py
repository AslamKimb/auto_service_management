import frappe
from frappe import _
from frappe.utils import today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not frappe.has_permission("Repair Job", "read") and not frappe.has_permission("Repair Job", "report"):
		frappe.throw(_("You are not permitted to read this report."), frappe.PermissionError)
	conditions = ["1=1"]
	values = {"report_date": filters.get("report_date") or today()}
	if filters.get("workshop_bay"):
		conditions.append("wb.name = %(workshop_bay)s")
		values["workshop_bay"] = filters.workshop_bay
	if filters.get("technician"):
		conditions.append("(rjs.assigned_technician = %(technician)s OR labour.assigned_to = %(technician)s)")
		values["technician"] = filters.technician
	if filters.get("completion_state") == "Open":
		conditions.append("COALESCE(rjs.is_completed, 0) = 0")
	elif filters.get("completion_state") == "Completed":
		conditions.append("COALESCE(rjs.is_completed, 0) = 1")

	columns = [
		{"label": _("Workshop Bay"), "fieldname": "workshop_bay", "fieldtype": "Link", "options": "Workshop Bay", "width": 150},
		{"label": _("Repair Job"), "fieldname": "repair_job", "fieldtype": "Link", "options": "Repair Job", "width": 145},
		{"label": _("Service"), "fieldname": "service_name", "fieldtype": "Data", "width": 190},
		{"label": _("Vehicle"), "fieldname": "customer_vehicle", "fieldtype": "Link", "options": "Customer Vehicle", "width": 130},
		{"label": _("Technicians"), "fieldname": "technicians", "fieldtype": "Data", "width": 220},
		{"label": _("Completed"), "fieldname": "is_completed", "fieldtype": "Check", "width": 90},
		{"label": _("Completed On"), "fieldname": "completed_on", "fieldtype": "Datetime", "width": 150},
		{"label": _("Closed Today"), "fieldname": "closed_today", "fieldtype": "Check", "width": 100},
	]
	data = frappe.db.sql(
		f"""
		SELECT wb.name AS workshop_bay, rjs.repair_job, rjs.service_name,
			rj.customer_vehicle, rjs.is_completed, rjs.completed_on,
			GROUP_CONCAT(DISTINCT technician ORDER BY technician SEPARATOR ', ') AS technicians,
			CASE WHEN DATE(rjs.completed_on) = %(report_date)s THEN 1 ELSE 0 END AS closed_today
		FROM `tabWorkshop Bay` wb
		LEFT JOIN `tabRepair Job Service` rjs ON rjs.workshop_bay = wb.name AND rjs.docstatus < 2
		LEFT JOIN `tabRepair Job` rj ON rj.name = rjs.repair_job
		LEFT JOIN (
			SELECT repair_job_service, assigned_to AS technician FROM `tabRepair Job Service Labour`
			WHERE assigned_to IS NOT NULL AND assigned_to != ''
			UNION ALL
			SELECT name AS repair_job_service, assigned_technician AS technician FROM `tabRepair Job Service`
			WHERE assigned_technician IS NOT NULL AND assigned_technician != ''
		) labour ON labour.repair_job_service = rjs.name
		WHERE {' AND '.join(conditions)}
		GROUP BY wb.name, rjs.name
		ORDER BY wb.name, rjs.modified DESC
		""",
		values,
		as_dict=True,
	)
	active = sum(not row.is_completed for row in data if row.repair_job)
	closed_today = sum(row.closed_today for row in data)
	return columns, data, None, {
		"data": {"labels": [_('Active'), _('Closed Today')], "datasets": [{"name": _('Services'), "values": [active, closed_today]}]},
		"type": "bar",
	}, [
		{"label": _("Active Services"), "value": active, "indicator": "blue"},
		{"label": _("Closed Today"), "value": closed_today, "indicator": "green"},
	]
