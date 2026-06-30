frappe.query_reports["Gate Pass Register"] = {
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
   "fieldname": "status",
   "label": "Status",
   "fieldtype": "Select",
   "options": "Pending\nIssued\nUsed\nCancelled"
  }
 ]
};
