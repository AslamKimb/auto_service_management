frappe.ui.form.on("Repair Job", {
	setup(frm) {
		setup_realtime_handlers(frm);
		// A vehicle is a reusable identity; customer ownership is selected per visit.
		frm.set_query("customer_vehicle", () => ({}));
		frm.set_query("contact_person", () => ({
			query: "auto_service_management.auto_service_management.doctype.repair_job.repair_job.get_company_contacts",
			filters: { customer: frm.doc.customer },
		}));

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
		show_repair_job_id(frm);
		set_contact_field_state(frm);
		render_company_contact_details(frm);
		if (frm.doc.customer) {
			frappe.db.get_value("Customer", frm.doc.customer, "customer_type").then(({ message }) => {
				set_contact_field_state(frm, message?.customer_type);
				setup_company_contact_action(frm, message?.customer_type);
			});
		} else {
			setup_company_contact_action(frm);
		}
		sync_dom_field_value(frm, "odometer_in");
		set_business_status_indicator(frm);
		if (frm.is_new()) {
			return;
		}
		frm.set_df_property("job_status", "read_only", 1);
		add_workflow_action_buttons(frm);

		if (frappe.model.can_read("Repair Job Service Template")
			&& frappe.model.can_create("Repair Job Service")) {
			frm.add_custom_button("Create Repair Job Service", () => {
			const create_blank_service = () => new_doc_with_values("Repair Job Service", {
				repair_job: frm.doc.name, customer: frm.doc.customer,
				customer_vehicle: frm.doc.customer_vehicle, diagnosis_report: frm.doc.diagnosis_report,
				currency: frm.doc.currency,
			});
			frappe.call({
				method: "auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service.get_compatible_repair_job_service_templates",
				args: { repair_job: frm.doc.name }, type: "GET",
				callback(r) {
					const templates = r.message || [];
					if (!templates.length) {
						frappe.msgprint({
							message: __("No active service templates match this vehicle. A blank service will open for you to complete."),
							primary_action: { label: __("Create Blank Service"), action: create_blank_service },
						});
						return;
					}
					const template_names = templates.map(row => row.name);
					const dialog = new frappe.ui.Dialog({
						title: __("Create Repair Job Service"),
						fields: [{
							fieldname: "template", fieldtype: "Link", label: __("Template"),
							options: "Repair Job Service Template", reqd: 1,
							get_query: () => ({ filters: { name: ["in", template_names] } }),
						}],
						primary_action_label: __("Create"),
						primary_action(values) {
							frappe.call({
								method: "auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service.make_repair_job_service",
								args: { source_name: values.template, repair_job: frm.doc.name }, type: "POST",
								callback(result) {
									dialog.hide();
									const docs = result.message ? frappe.model.sync(result.message) : [];
									const service = docs[0];
									if (service?.name) frappe.set_route("Form", service.doctype, service.name);
								},
							});
						},
					});
					dialog.set_secondary_action_label(__("Create Blank Service"));
					dialog.set_secondary_action(create_blank_service);
					dialog.show();
				},
			});
			}, "Services");
		}

		frm.add_custom_button("Open Services", () => {
			frappe.set_route("List", "Repair Job Service", {
				repair_job: frm.doc.name,
			});
		}, "Services");

		setup_optional_widget("auto_service_billing", frm, {
			fieldname: "billing_components_html",
			method: "auto_service_management.auto_service_management.doctype.repair_job.repair_job.make_sales_invoice",
		});

		setup_optional_widget("auto_service_material_requests", frm, {
			fieldname: "material_requests_html",
			method: "auto_service_management.auto_service_management.doctype.repair_job.repair_job.make_material_request",
		});

		setup_optional_widget("auto_service_sales_orders", frm, {
			repairJob: frm.doc.name,
			fieldname: "sales_orders_html",
			method: "auto_service_management.auto_service_management.doctype.repair_job.repair_job.make_sales_order",
			title: __("Select components for Proforma Invoice (Sales Order)"),
		});
		frm.add_custom_button(__("Sales Invoices"), () => {
			frappe.set_route("List", "Sales Invoice", { repair_job: frm.doc.name });
		}, __("Related Documents"));
		frm.add_custom_button(__("Sales Orders"), () => {
			frappe.set_route("List", "Sales Order", { repair_job: frm.doc.name });
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

		if (frm.doc.quality_check || !frm.is_new()) {
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

		setup_final_release_gate_pass_button(frm);
		frm.add_custom_button(__("Create Road Test Gate Pass"), () => {
			new_doc_with_values("Gate Pass", {
				repair_job: frm.doc.name,
				purpose: "Road Test",
				customer_vehicle: frm.doc.customer_vehicle,
				recipient_name: frm.doc.customer,
			});
		}, __("Related Documents"));
	},

	before_save(frm) {
		sync_dom_field_value(frm, "odometer_in");
	},

	customer(frm) {
		if (!frm.doc.customer) {
			frm.set_value("contact_person", null);
			set_contact_field_state(frm);
			setup_company_contact_action(frm);
			render_company_contact_details(frm);
			return;
		}
		frm.set_value("contact_person", null);
		render_company_contact_details(frm);
		frappe.db.get_value("Customer", frm.doc.customer, "customer_type").then(({ message }) => {
			set_contact_field_state(frm, message?.customer_type);
			setup_company_contact_action(frm, message?.customer_type);
		});
	},

	contact_person(frm) {
		render_company_contact_details(frm);
	},

	customer_vehicle(frm) {
		// Do not overwrite the visit customer: reassociation is explicit at Check In.
	},
});

function set_contact_field_state(frm, customerType) {
	if (!frm.fields_dict.contact_person) return;
	const type = customerType || frm.doc.customer_type;
	if (!frm.doc.customer || !type) {
		frm.set_df_property("company_contact_section", "hidden", 1);
		frm.set_df_property("contact_person", "hidden", 1);
		return;
	}
	if (type === "Individual") {
		frm.set_df_property("company_contact_section", "hidden", 1);
		frm.set_df_property("contact_person", "hidden", 1);
		frm.set_df_property("contact_person", "reqd", 0);
		frm.set_df_property("contact_person", "read_only", 0);
		return;
	}
	frm.set_df_property("company_contact_section", "hidden", 0);
	frm.set_df_property("contact_person", "hidden", 0);
	frm.set_df_property("contact_person", "reqd", frm.doc.job_status !== "Draft");
	frm.set_df_property("contact_person", "read_only", frm.doc.job_status !== "Draft");
}

function setup_company_contact_action(frm, customerType) {
	const label = __("Add Company Contact Person");
	frm.remove_custom_button(label, __("Customer"));
	if (customerType !== "Company" || !frm.doc.customer || (!frm.is_new() && frm.doc.job_status !== "Draft") || !frappe.model.can_create("Contact")) {
		return;
	}
	frm.add_custom_button(label, () => show_company_contact_dialog(frm), __("Customer"));
}

function show_company_contact_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Add Company Contact Person"),
		fields: [
			{ fieldname: "salutation", fieldtype: "Data", label: __("Salutation") },
			{ fieldname: "first_name", fieldtype: "Data", label: __("First Name"), reqd: 1 },
			{ fieldname: "middle_name", fieldtype: "Data", label: __("Middle Name") },
			{ fieldname: "last_name", fieldtype: "Data", label: __("Last Name") },
			{ fieldname: "designation", fieldtype: "Data", label: __("Designation") },
			{ fieldname: "department", fieldtype: "Data", label: __("Department") },
			{ fieldname: "email_id", fieldtype: "Data", options: "Email", label: __("Email") },
			{ fieldname: "phone", fieldtype: "Data", label: __("Phone") },
			{ fieldname: "mobile_no", fieldtype: "Data", label: __("Mobile") },
		],
		primary_action_label: __("Create and Select"),
		primary_action(values) {
			frappe.call({
				method: "auto_service_management.auto_service_management.doctype.repair_job.repair_job.create_company_contact",
				type: "POST",
				args: { customer: frm.doc.customer, ...values },
				freeze: true,
				freeze_message: __("Creating company contact..."),
				callback(response) {
					if (!response.message?.name) return;
					dialog.hide();
					frm.set_value("contact_person", response.message.name);
					frappe.show_alert({ message: __("Company contact created and selected."), indicator: "green" });
				},
			});
		},
	});
	dialog.show();
}

function render_company_contact_details(frm) {
	const field = frm.fields_dict.company_contact_details_html;
	if (!field) return;
	if (!frm.doc.contact_person) {
		if (frm.doc.customer && frappe.model.can_create("Contact")) {
			field.$wrapper.html(`<button type="button" class="btn btn-xs btn-secondary js-add-company-contact">${__("Add company contact person")}</button>`);
			field.$wrapper.find(".js-add-company-contact").on("click", () => show_company_contact_dialog(frm));
		} else {
			field.$wrapper.empty();
		}
		return;
	}
	const selectedContact = frm.doc.contact_person;
	frappe.db.get_value(
		"Contact",
		selectedContact,
		["first_name", "middle_name", "last_name", "designation", "department", "email_id", "phone", "mobile_no"],
	).then(({ message }) => {
		if (!message || frm.doc.contact_person !== selectedContact) return;
		const fullName = [message.first_name, message.middle_name, message.last_name].filter(Boolean).join(" ");
		const rows = [
			[__("Name"), fullName],
			[__("Designation"), message.designation],
			[__("Department"), message.department],
			[__("Email"), message.email_id],
			[__("Phone"), message.phone],
			[__("Mobile"), message.mobile_no],
		].filter(([, value]) => value);
		field.$wrapper.html(`<div class="text-muted small">${__("Selected contact details")}</div><div class="small">${rows.map(([label, value]) => `<div><strong>${frappe.utils.escape_html(label)}:</strong> ${frappe.utils.escape_html(value)}</div>`).join("")}</div>`);
	});
}

function setup_realtime_handlers(frm) {
	if (frm.__auto_service_realtime_handlers_setup) {
		return;
	}
	frm.__auto_service_realtime_handlers_setup = true;
	frappe.realtime.on("repair_job_services_updated", (data) => {
		if (!frm.is_new() && data?.repair_job === frm.doc.name && !frm.is_dirty()) {
			frm.reload_doc();
		}
	});
	frappe.realtime.on("repair_job_related_tables_updated", (data) => {
		if (frm.is_new() || data?.repair_job !== frm.doc.name) {
			return;
		}
		if (!frm.is_dirty()) {
			frm.reload_doc();
			return;
		}
		frappe.show_alert({
			message: __("Linked invoices, payments, or services changed. Save or reload to refresh the tables."),
			indicator: "orange",
		});
	});
}

function show_repair_job_id(frm) {
		const field = frm.fields_dict.repair_job_id_html;
		if (!field) {
			return;
		}
		const label = frappe.utils.escape_html(__("Repair Job ID"));
		const value = frappe.utils.escape_html(frm.doc.name || __("Assigned on save"));
		field.$wrapper.html(`<div class="text-muted small">${label}</div><div class="font-weight-bold">${value}</div>`);
}

function add_workflow_action_buttons(frm) {
	const actions = {
		Draft: [["Check In", "check_in"]],
		Assessment: [["Complete Assessment", "complete_diagnosis"]],
		"Awaiting Approval": [["Start Work", "start_work"]],
		"In Repair": [
			["Send to QC", "hold_for_qc"],
			["Continue to Billing", "mark_ready_for_invoice"],
		],
		"Quality Check": [
			["Return to Repair", "return_to_repair"],
			["Continue to Billing", "pass_qc"],
		],
	};
	for (const [label, method] of actions[frm.doc.job_status] || []) {
		frm.add_custom_button(__(label), () => {
			if (method === "check_in") {
				check_in_with_confirmation(frm);
				return;
			}
			frm.call(method).then(() => frm.reload_doc());
		}, __("Workflow"));
	}
	if (can_override_status()) {
		frm.add_custom_button(__("Set Status"), () => show_status_override_dialog(frm), __("Workflow"));
	}
}

function check_in_with_confirmation(frm) {
	const args = {
		expected_version: frm.doc.modified,
		idempotency_key: `repair-job-check-in:${frm.doc.name}`,
		confirm_customer_association: 0,
		contact_person: frm.doc.contact_person || null,
	};
	frappe.db.get_value("Customer Vehicle", frm.doc.customer_vehicle, "customer").then(({ message }) => {
		const currentCustomer = message?.customer;
		if (currentCustomer && currentCustomer === frm.doc.customer) {
			frm.call("check_in", args).then(() => frm.reload_doc());
			return;
		}
		frappe.confirm(
			__("This vehicle is currently associated with {0}. Check it in for {1} and update the vehicle history?", [currentCustomer || __("no customer"), frm.doc.customer]),
			() => {
				args.confirm_customer_association = 1;
				frm.call("check_in", args).then(() => frm.reload_doc());
			},
		);
	});
}

function setup_optional_widget(globalName, frm, options) {
	const widget = window[globalName];
	if (widget?.setup) {
		widget.setup(frm, options);
		return;
	}
	console.warn(`${globalName} is unavailable; skipping optional Repair Job widget setup.`);
}

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

function setup_final_release_gate_pass_button(frm) {
	if (frm.doc.gate_pass || can_create_gate_pass(frm)) {
		add_final_release_gate_pass_button(frm);
		return;
	}
	if (frm.is_new()) {
		return;
	}
	frappe.call({
		method: "auto_service_management.auto_service_management.doctype.repair_job.repair_job.can_create_final_release_gate_pass",
		args: {
			repair_job_name: frm.doc.name,
		},
		type: "GET",
		callback(response) {
			if (response.message) {
				add_final_release_gate_pass_button(frm);
			}
		},
	});
}

function add_final_release_gate_pass_button(frm) {
	add_related_document_button(frm, {
		fieldname: "gate_pass",
		doctype: "Gate Pass",
		create_label: "Create Final Release Gate Pass",
		open_label: "Open Final Release Gate Pass",
		route_options: {
			repair_job: frm.doc.name,
			purpose: "Final Release",
			customer_vehicle: frm.doc.customer_vehicle,
			sales_invoice: frm.doc.sales_invoices?.[0]?.sales_invoice || "",
			recipient_name: frm.doc.customer,
		},
	});
}

function can_create_gate_pass(frm) {
	return (frm.doc.sales_invoices || []).some((row) => row.sales_invoice);
}

function can_override_status() {
	return frappe.user.has_role("Workshop Manager")
		|| frappe.user.has_role("Auto Service Admin")
		|| frappe.user.has_role("System Manager");
}

function show_status_override_dialog(frm) {
	const statuses = [
		"Draft",
		"Assessment",
		"Awaiting Approval",
		"In Repair",
		"Quality Check",
		"Billing",
		"Ready for Release",
	];
	const dialog = new frappe.ui.Dialog({
		title: __("Manual Status Override"),
		fields: [
			{
				fieldname: "target_status",
				fieldtype: "Select",
				label: __("Target Status"),
				options: statuses.join("\n"),
				default: frm.doc.job_status,
				reqd: 1,
			},
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Reason"),
				reqd: 1,
			},
		],
		primary_action_label: __("Apply"),
		primary_action(values) {
			frm.call("override_status", values).then(() => {
				dialog.hide();
				frm.reload_doc();
			});
		},
	});
	dialog.show();
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
