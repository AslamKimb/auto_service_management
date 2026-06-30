frappe.query_reports["Jobs Waiting for Parts"] = {
 "filters": [
  {
   "fieldname": "item_code",
   "label": "Item",
   "fieldtype": "Link",
   "options": "Item"
  },
  {
   "fieldname": "status",
   "label": "Line Status",
   "fieldtype": "Select",
   "options": "Pending\nApproved"
  }
 ]
};
