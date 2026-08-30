frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		if (frm.doc.docstatus === 2 || !frappe.model.can_read("Repair Job")) return;
		frm.add_custom_button(__("Repair Job"), () => open_repair_job_items_dialog(frm), __("Get Items From"));
		frm.add_custom_button(__("Repair Job Service"), () => open_repair_job_items_dialog(frm, "service"), __("Get Items From"));
	},
});

function open_repair_job_items_dialog(frm, initialSource) {
	const dialog = new frappe.ui.Dialog({
		title: __("Get Items From Repair Job"),
		fields: [
			{
				fieldname: "source_type", fieldtype: "Select", label: __("Source"),
				options: "Repair Job\nRepair Job Service", default: initialSource === "service" ? "Repair Job Service" : "Repair Job", reqd: 1,
			},
			{fieldname: "repair_job", fieldtype: "Link", label: __("Repair Job"), options: "Repair Job", reqd: 1},
			{fieldname: "service_name", fieldtype: "Link", label: __("Repair Job Service"), options: "Repair Job Service"},
			{fieldname: "preview", fieldtype: "HTML", label: __("Items")},
		],
	});
	dialog.__frm = frm;
	dialog.set_df_property("service_name", "hidden", initialSource !== "service");
	dialog.fields_dict.repair_job.get_query = () => ({});
	dialog.fields_dict.service_name.get_query = () => ({filters: {repair_job: dialog.get_value("repair_job") || ""}});
	dialog.fields_dict.source_type.$input.on("change", () => {
		const service = dialog.get_value("source_type") === "Repair Job Service";
		dialog.set_df_property("service_name", "hidden", !service);
		dialog.set_df_property("service_name", "reqd", service);
	});
	dialog.set_primary_action(__("Load Items"), () => load_repair_job_items(dialog));
	dialog.show();
}

function load_repair_job_items(dialog) {
	const values = dialog.get_values();
	if (!values) return;
	if (values.source_type === "Repair Job Service" && !values.service_name) {
		frappe.msgprint(__("Select a Repair Job Service."));
		return;
	}
	dialog.fields_dict.preview.$wrapper.html(`<div class="text-muted">${__("Loading eligible items…")}</div>`);
	frappe.call({
		method: "auto_service_management.auto_service_management.integration.erpnext.component_mapping.get_sales_order_components",
		args: {repair_job_name: values.repair_job, service_name: values.service_name || null},
		type: "GET", freeze: true,
	}).then((response) => {
		const payload = response.message || {};
		dialog.__sourcePayload = payload;
		dialog.__sourceValues = values;
		render_repair_job_items(dialog, payload);
		dialog.set_primary_action(__("Add Selected"), () => add_repair_job_items(dialog));
	});
}

function render_repair_job_items(dialog, payload) {
	const escape = frappe.utils.escape_html;
	const rows = payload.components || [];
	const selectable = rows.filter((row) => row.selectable);
	const heading = `<div class="text-muted mb-2">${__("Source status")}: ${escape(payload.source_state || "")} · ${__("Available")}: ${selectable.length}</div>`;
	if (!payload.source_selectable) {
		dialog.fields_dict.preview.$wrapper.html(`${heading}<div class="alert alert-warning">${__("This Repair Job is still before Assessment. Items can be reviewed after Check In.")}</div>`);
		return;
	}
	if (!rows.length || !selectable.length) {
		dialog.fields_dict.preview.$wrapper.html(`${heading}<div class="text-muted">${__("No eligible billable items are available.")}</div>`);
		return;
	}
	const body = rows.map((row) => {
		const disabled = row.selectable ? "" : "disabled";
		const checked = row.selectable ? "checked" : "";
		return `<tr><td><input type="checkbox" class="repair-job-component" data-doctype="${escape(row.component_doctype)}" data-name="${escape(row.component_name)}" ${checked} ${disabled}></td><td>${escape(row.service_name || "")}</td><td>${escape(row.description || "")}</td><td>${escape(String(row.quantity || 0))}</td><td>${escape(row.order_state || "")}</td></tr>`;
	}).join("");
	dialog.fields_dict.preview.$wrapper.html(`${heading}<div style="max-height:35vh;overflow:auto"><table class="table table-bordered table-sm"><thead><tr><th></th><th>${__("Service")}</th><th>${__("Description")}</th><th>${__("Qty")}</th><th>${__("State")}</th></tr></thead><tbody>${body}</tbody></table></div>`);
}

function add_repair_job_items(dialog) {
	const values = dialog.__sourceValues;
	const refs = Array.from(dialog.fields_dict.preview.$wrapper[0].querySelectorAll(".repair-job-component:checked"))
		.map((input) => ({doctype: input.dataset.doctype, name: input.dataset.name}));
	if (!refs.length) {
		frappe.msgprint(__("Select at least one eligible item."));
		return;
	}
	const frm = dialog.__frm;
	const request = () => frappe.call({
		method: "auto_service_management.auto_service_management.integration.erpnext.component_mapping.get_items_from_repair_job",
		args: {
			repair_job_name: values.repair_job,
			service_name: values.service_name || null,
			target_doc: frm.doc,
			component_refs: JSON.stringify(refs),
			expected_version: frm.doc.modified || null,
		},
		type: "POST", freeze: true,
	});
	const responsePromise = frm.is_dirty() ? frm.save().then(request) : request();
	responsePromise.then((response) => {
		dialog.hide();
		if (response.message) frappe.model.sync(response.message);
		frm.refresh_fields();
		if (frm.doc.docstatus === 1) frm.reload_doc();
	});
}
