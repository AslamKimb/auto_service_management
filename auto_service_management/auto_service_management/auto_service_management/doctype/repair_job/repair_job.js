frappe.ui.form.on("Repair Job", {
	setup(frm) {
		setup_realtime_handlers(frm);
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
		show_repair_job_id(frm);
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
			frm.call(method).then(() => frm.reload_doc());
		}, __("Workflow"));
	}
	if (can_override_status()) {
		frm.add_custom_button(__("Set Status"), () => show_status_override_dialog(frm), __("Workflow"));
	}
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
