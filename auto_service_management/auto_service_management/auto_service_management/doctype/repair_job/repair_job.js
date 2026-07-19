frappe.ui.form.on("Repair Job", {
	setup(frm) {
		frm.set_query("customer_vehicle", () => {
			if (!frm.doc.customer) {
				return {};
			}
			return { filters: { customer: frm.doc.customer } };
		});

		for (const [fieldname] of [
			["walkaround_inspection"],
			["diagnosis_report"],
			["customer_authorization"],
			["quality_check"],
			["gate_pass"],
		]) {
			frm.set_query(fieldname, () => {
				if (!frm.doc.name) {
					return { filters: { name: ["=", ""] } };
				}
				return { filters: { repair_job: frm.doc.name } };
			});
		}
	},

	refresh(frm) {
		sync_dom_field_value(frm, "odometer_in");
		set_business_status_indicator(frm);
		if (frm.is_new()) {
			return;
		}
		frm.set_df_property("job_status", "read_only", 1);

		frm.add_custom_button("Create Service", () => {
			new_doc_with_values("Repair Job Service", {
				repair_job: frm.doc.name,
				customer: frm.doc.customer,
				customer_vehicle: frm.doc.customer_vehicle,
				diagnosis_report: frm.doc.diagnosis_report,
				currency: frm.doc.currency,
			});
		}, "Services");

		frm.add_custom_button("Open Services", () => {
			frappe.set_route("List", "Repair Job Service", {
				repair_job: frm.doc.name,
			});
		}, "Services");

		if (["Billing", "Ready for Invoice", "Ready for Release"].includes(frm.doc.job_status)) {
			frm.add_custom_button(__("Sales Invoice"), () => {
				frappe.model.open_mapped_doc({
					method: "auto_service_management.auto_service_management.doctype.repair_job.repair_job.make_sales_invoice",
					frm,
				});
			}, __("Create"));
		}

		if (["In Repair", "Quality Check", "Billing", "Ready for Release"].includes(frm.doc.job_status)) {
			frm.add_custom_button(__("Material Request"), () => {
				frappe.model.open_mapped_doc({
					method: "auto_service_management.auto_service_management.doctype.repair_job.repair_job.make_material_request",
					frm,
				});
			}, __("Create"));
		}

		frm.add_custom_button(__("Sales Invoices"), () => {
			frappe.set_route("List", "Sales Invoice", { repair_job: frm.doc.name });
		}, __("Related Documents"));
		frm.add_custom_button(__("Material Requests"), () => {
			frappe.set_route("List", "Material Request", { repair_job: frm.doc.name });
		}, __("Related Documents"));

		add_related_document_button(frm, {
			fieldname: "walkaround_inspection",
			doctype: "Walkaround Inspection",
			create_label: "Create Walkaround Inspection",
			open_label: "Open Walkaround Inspection",
			route_options: {
				repair_job: frm.doc.name,
				customer_vehicle: frm.doc.customer_vehicle,
				inspection_date: frappe.datetime.now_datetime(),
				odometer_reading: frm.doc.odometer_in,
				fuel_level: frm.doc.fuel_level,
			},
		});

		add_related_document_button(frm, {
			fieldname: "diagnosis_report",
			doctype: "Diagnosis Report",
			create_label: "Create Diagnosis Report",
			open_label: "Open Diagnosis Report",
			route_options: {
				repair_job: frm.doc.name,
				customer_vehicle: frm.doc.customer_vehicle,
				diagnosis_date: frappe.datetime.now_datetime(),
				customer_complaint: frm.doc.customer_concern,
			},
		});

		add_related_document_button(frm, {
			fieldname: "customer_authorization",
			doctype: "Customer Authorization",
			create_label: "Create Customer Authorization",
			open_label: "Open Customer Authorization",
			route_options: {
				repair_job: frm.doc.name,
				customer: frm.doc.customer,
				currency: frm.doc.currency,
				approved_amount: frm.doc.total_amount,
				authorization_date: frappe.datetime.now_datetime(),
			},
		});

		if (["In Repair", "Quality Check", "Billing"].includes(frm.doc.job_status) || frm.doc.quality_check) {
			add_related_document_button(frm, {
				fieldname: "quality_check",
				doctype: "Quality Check",
				create_label: "Create Quality Check",
				open_label: "Open Quality Check",
				route_options: {
					repair_job: frm.doc.name,
					customer_vehicle: frm.doc.customer_vehicle,
					qc_date: frappe.datetime.now_datetime(),
					checked_by: frappe.session.user,
				},
			});
		}

		if (frm.doc.gate_pass || can_create_gate_pass(frm)) {
			add_related_document_button(frm, {
				fieldname: "gate_pass",
				doctype: "Gate Pass",
				create_label: "Create Gate Pass",
				open_label: "Open Gate Pass",
				route_options: {
					repair_job: frm.doc.name,
					customer_vehicle: frm.doc.customer_vehicle,
					sales_invoice: frm.doc.sales_invoices?.[0]?.sales_invoice || "",
					recipient_name: frm.doc.customer,
				},
			});
		}
	},

	before_save(frm) {
		sync_dom_field_value(frm, "odometer_in");
	},

	customer(frm) {
		if (!frm.doc.customer || !frm.doc.customer_vehicle) {
			return;
		}
		frappe.db.get_value("Customer Vehicle", frm.doc.customer_vehicle, "customer").then(({ message }) => {
			if (message?.customer && message.customer !== frm.doc.customer) {
				frm.set_value("customer_vehicle", null);
			}
		});
	},

	customer_vehicle(frm) {
		if (!frm.doc.customer_vehicle) {
			return;
		}
		frappe.db.get_value("Customer Vehicle", frm.doc.customer_vehicle, "customer").then(({ message }) => {
			if (message?.customer && frm.doc.customer !== message.customer) {
				frm.set_value("customer", message.customer);
			}
		});
	},
});

function add_related_document_button(frm, options) {
	if (frm.doc[options.fieldname]) {
		frm.add_custom_button(options.open_label, () => {
			frappe.set_route("Form", options.doctype, frm.doc[options.fieldname]);
		}, "Related Documents");
		return;
	}

	frm.add_custom_button(options.create_label, () => {
		new_doc_with_values(options.doctype, options.route_options);
	}, "Related Documents");
}

function new_doc_with_values(doctype, values) {
	frappe.model.with_doctype(doctype, () => {
		const doc = frappe.model.get_new_doc(doctype);
		for (const [fieldname, value] of Object.entries(values || {})) {
			if (value !== undefined && value !== null && value !== "") {
				doc[fieldname] = value;
			}
		}
		frappe.set_route("Form", doctype, doc.name);
	});
}

function can_create_gate_pass(frm) {
	if (frm.doc.job_status !== "Ready for Release") {
		return false;
	}
	return (frm.doc.sales_invoices || []).some((row) => row.sales_invoice);
}

function set_business_status_indicator(frm) {
	if (!frm.doc.job_status || !frm.page?.set_indicator) {
		return;
	}
	const colors = {
		Draft: "gray",
		Assessment: "orange",
		"Awaiting Approval": "orange",
		Approved: "blue",
		"In Repair": "blue",
		"Quality Check": "purple",
		Billing: "orange",
		"Ready for Invoice": "orange",
		"Ready for Release": "green",
		Closed: "green",
		Cancelled: "red",
	};
	frm.page.set_indicator(__(frm.doc.job_status), colors[frm.doc.job_status] || "gray");
}

function sync_dom_field_value(frm, fieldname) {
	const field = frm.fields_dict[fieldname];
	if (!field || frm.doc[fieldname]) {
		return;
	}
	const value = field.$input?.val?.();
	if (value !== undefined && value !== null && value !== "") {
		frm.doc[fieldname] = value;
	}
}
