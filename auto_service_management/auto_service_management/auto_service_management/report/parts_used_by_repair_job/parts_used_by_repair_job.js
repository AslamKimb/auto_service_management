frappe.query_reports["Parts Used by Repair Job"] = {
 "filters": [
  {
   "fieldname": "parent",
   "label": "Repair Job",
   "fieldtype": "Link",
   "options": "Repair Job"
  },
  {
   "fieldname": "item_code",
   "label": "Item",
   "fieldtype": "Link",
   "options": "Item"
  }
 ]
};
