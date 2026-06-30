frappe.query_reports["Vehicle Service History"] = {
 "filters": [
  {
   "fieldname": "customer_vehicle",
   "label": "Vehicle",
   "fieldtype": "Link",
   "options": "Customer Vehicle"
  },
  {
   "fieldname": "from_date",
   "label": "From Date",
   "fieldtype": "Date"
  },
  {
   "fieldname": "to_date",
   "label": "To Date",
   "fieldtype": "Date"
  }
 ]
};
