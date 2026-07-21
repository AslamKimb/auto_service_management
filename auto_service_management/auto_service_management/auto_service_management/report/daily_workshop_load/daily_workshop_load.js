frappe.query_reports["Daily Workshop Load"] = {
 "filters": [
  {"fieldname": "report_date", "label": "Date", "fieldtype": "Date", "default": frappe.datetime.get_today()},
  {
   "fieldname": "workshop_bay",
   "label": "Workshop Bay",
   "fieldtype": "Link",
   "options": "Workshop Bay"
  },
  {
   "fieldname": "technician",
   "label": "Technician",
   "fieldtype": "Link",
   "options": "User"
  },
  {
   "fieldname": "completion_state",
   "label": "Completion",
   "fieldtype": "Select",
   "options": "\nOpen\nCompleted"
  }
 ]
};
