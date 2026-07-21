frappe.query_reports["Workshop Bay View"] = {
	filters: [
		{ fieldname: "report_date", label: __("Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "workshop_bay", label: __("Workshop Bay"), fieldtype: "Link", options: "Workshop Bay" },
		{ fieldname: "technician", label: __("Technician"), fieldtype: "Link", options: "User" },
		{ fieldname: "completion_state", label: __("Completion"), fieldtype: "Select", options: "\nOpen\nCompleted" },
	],
};
