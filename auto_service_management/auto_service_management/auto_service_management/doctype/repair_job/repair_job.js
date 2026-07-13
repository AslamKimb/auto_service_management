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
			["road_test_report"],
			["gate_pass"],
			["repair_job_service"],
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
		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button("Create Service", () => {
			frappe.new_doc("Repair Job Service", {
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

		if (["Approved", "Ready for Invoice"].includes(frm.doc.job_status)) {
			frm.add_custom_button(__("Sales Invoice"), () => {
				frappe.model.open_mapped_doc({
					method: "auto_service_management.auto_service_management.doctype.repair_job.repair_job.make_sales_invoice",
					frm,
				});
			}, __("Create"));
		}

		if (["Approved", "In Repair", "Quality Check", "Ready for Invoice"].includes(frm.doc.job_status)) {
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

		add_related_document_button(frm, {
			fieldname: "road_test_report",
			doctype: "Road Test Report",
			create_label: "Create Road Test Report",
			open_label: "Open Road Test Report",
			route_options: {
				repair_job: frm.doc.name,
				customer_vehicle: frm.doc.customer_vehicle,
				test_date: frappe.datetime.now_datetime(),
				tested_by: frappe.session.user,
				odometer_start: frm.doc.odometer_in,
			},
		});

		add_related_document_button(frm, {
			fieldname: "gate_pass",
			doctype: "Gate Pass",
			create_label: "Create Gate Pass",
			open_label: "Open Gate Pass",
			route_options: {
				repair_job: frm.doc.name,
				customer_vehicle: frm.doc.customer_vehicle,
				sales_invoice: frm.doc.sales_invoice,
				recipient_name: frm.doc.customer,
			},
		});

		add_related_document_button(frm, {
			fieldname: "repair_job_service",
			doctype: "Repair Job Service",
			create_label: "Create Repair Job Service",
			open_label: "Open Repair Job Service",
			route_options: {
				repair_job: frm.doc.name,
				customer: frm.doc.customer,
				customer_vehicle: frm.doc.customer_vehicle,
				currency: frm.doc.currency,
			},
		});
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
		frappe.new_doc(options.doctype, options.route_options);
	}, "Related Documents");
}
