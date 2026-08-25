frappe.query_reports["Customer LPO Vehicle Progress"] = {
	filters: [
		{ fieldname: "parent", label: __("Customer LPO"), fieldtype: "Link", options: "Customer LPO" },
		{ fieldname: "customer_vehicle", label: __("Customer Vehicle"), fieldtype: "Link", options: "Customer Vehicle" },
		{ fieldname: "repair_job", label: __("Repair Job"), fieldtype: "Link", options: "Repair Job" },
		{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nPending\nResolved\nJob Created\nIn Progress\nCompleted\nCancelled" },
	],
};
