frappe.query_reports["Customer LPO Utilization"] = {
	filters: [
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer" },
		{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nDraft\nActive\nExhausted\nCompleted\nExpired\nCancelled" },
		{ fieldname: "ceiling_basis", label: __("Ceiling Basis"), fieldtype: "Select", options: "\nTax Inclusive\nTax Exclusive" },
	],
};
