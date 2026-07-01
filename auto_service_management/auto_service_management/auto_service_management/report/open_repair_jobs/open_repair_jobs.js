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
   "options": "Draft\nChecked In\nWalkaround Inspection\nDiagnosis\nEstimate Prepared\nWaiting for Customer Approval\nApproved\nIn Repair\nQuality Check\nReady for Invoice\nInvoiced\nGate Pass Issued\nClosed - Diagnosis Only"
  }
 ]
};
