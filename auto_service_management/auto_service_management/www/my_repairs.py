import frappe
from frappe import _

from auto_service_management.portal import get_portal_repair_job, get_portal_repair_jobs


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = True
	context.title = _("My Repairs")
	name = frappe.form_dict.get("name")
	if name:
		context.update(get_portal_repair_job(name))
		context.is_detail = True
	else:
		context.update(get_portal_repair_jobs(page=frappe.form_dict.get("page")))
		context.is_detail = False
	return context
