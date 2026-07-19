frappe.query_reports["Open Repair Jobs"] = {
 "filters": [
  {
   "fieldname": "customer",
   "label": "Customer",
   "fieldtype": "Link",
   "options": "Customer"
  },
  {
   "fieldname": "customer_vehicle",
   "label": "Vehicle",
   "fieldtype": "Link",
   "options": "Customer Vehicle"
  },
  {
   "fieldname": "job_status",
   "label": "Status",
   "fieldtype": "Select",
   "options": "Draft\nAssessment\nAwaiting Approval\nIn Repair\nQuality Check\nBilling\nReady for Release\nClosed\nCancelled"
  }
 ]
};
