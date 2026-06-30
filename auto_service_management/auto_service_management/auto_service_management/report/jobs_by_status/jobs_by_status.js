frappe.query_reports["Jobs by Status"] = {
 "filters": [
  {
   "fieldname": "from_date",
   "label": "From Date",
   "fieldtype": "Date"
  },
  {
   "fieldname": "to_date",
   "label": "To Date",
   "fieldtype": "Date"
  },
  {
   "fieldname": "customer",
   "label": "Customer",
   "fieldtype": "Link",
   "options": "Customer"
  }
 ]
};
