frappe.query_reports["Discount and Price Change Audit"] = {
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
   "fieldname": "docname",
   "label": "Repair Job",
   "fieldtype": "Link",
   "options": "Repair Job"
  },
  {
   "fieldname": "owner",
   "label": "Changed By",
   "fieldtype": "Link",
   "options": "User"
  }
 ]
};
