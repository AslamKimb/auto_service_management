(function () {
	const CONTROLLER =
		"auto_service_management.auto_service_management.doctype.customer_lpo.customer_lpo";

	function can_write(frm) {
		return Boolean(frm.perm?.[0]?.write);
	}

	function esc(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	}

	function money(value, currency) {
		return frappe.format(value || 0, { fieldtype: "Currency", options: currency });
	}

	function refresh_summary(frm) {
		if (frm.is_new()) return;
		const field = frm.fields_dict.summary_html;
		if (field) field.$wrapper.html(`<div class="text-muted small" role="status">${__("Loading LPO utilization…")}</div>`);
		frappe.call({ method: `${CONTROLLER}.get_lpo_summary`, type: "GET", args: { lpo_name: frm.doc.name } })
			.then((response) => {
				const data = response.message || {};
				const currency = frm.doc.currency;
				frm.set_value("effective_authorized_amount", data.authorized_amount || 0);
				frm.set_value("invoiced_amount", data.used_amount || 0);
				frm.set_value("remaining_amount", Math.max((data.authorized_amount || 0) - (data.used_amount || 0), 0));
				frm.set_value("vehicle_count", (data.vehicles || []).length);
				frm.set_value("completed_vehicle_count", (data.vehicles || []).filter((row) => ["Closed", "Cancelled"].includes(row.repair_job?.job_status)).length);
				const vehicle_rows = (data.vehicles || []).map((row) => `<tr><td>${esc(row.registration_number)}</td><td>${esc(row.repair_job?.name || row.repair_job || "—")}</td><td>${esc(row.repair_job?.job_status || row.status || "Pending")}</td></tr>`).join("");
				if (field) field.$wrapper.html(`<div class="table-responsive"><table class="table table-bordered table-sm"><caption class="sr-only">${__("Customer LPO utilization")}</caption><thead><tr><th scope="col">${__("Vehicle")}</th><th scope="col">${__("Repair Job")}</th><th scope="col">${__("Status")}</th></tr></thead><tbody>${vehicle_rows || `<tr><td colspan="3" class="text-muted">${__("No vehicle rows")}</td></tr>`}</tbody></table><p class="text-muted small mb-0">${__("Effective authority")}: ${money(data.authorized_amount, currency)} · ${__("Used")}: ${money(data.used_amount, currency)} · ${__("Remaining")}: ${money(Math.max((data.authorized_amount || 0) - (data.used_amount || 0), 0), currency)}</p></div>`);
			})
			.catch(() => {
				if (field) field.$wrapper.html(`<div class="text-danger small" role="alert">${__("Unable to load LPO utilization. Refresh to try again.")}</div>`);
			});
	}

	function import_dialog(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Import LPO Vehicles"),
			fields: [
				{ fieldname: "file_url", fieldtype: "Attach", label: __("CSV file"), description: __("Choose a CSV file, or paste its contents below.") },
				{ fieldname: "csv_text", fieldtype: "Long Text", label: __("CSV content"), description: __("Header: registration_number,customer_vehicle,requested_work,planned_date,allocated_ceiling,remarks") },
			],
			primary_action_label: __("Import"),
			primary_action(values) {
				if (!values.file_url && !values.csv_text) {
					frappe.msgprint(__("Choose a CSV file or paste CSV content first."));
					return;
				}
				dialog.disable_primary_action();
				frappe.call({ method: `${CONTROLLER}.import_vehicle_csv`, type: "POST", args: { lpo_name: frm.doc.name, file_url: values.file_url, csv_text: values.csv_text } })
					.then(() => { dialog.hide(); frm.reload_doc(); })
					.catch(() => dialog.enable_primary_action());
			},
		});
		dialog.show();
	}

	function preview_dialog(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Preview LPO Vehicle CSV"),
			fields: [{ fieldname: "csv_text", fieldtype: "Long Text", label: __("CSV content"), reqd: 1 }],
			primary_action_label: __("Preview"),
			primary_action(values) {
				dialog.disable_primary_action();
				frappe.call({ method: `${CONTROLLER}.preview_vehicle_csv`, type: "GET", args: { lpo_name: frm.doc.name, csv_text: values.csv_text } })
					.then((response) => {
						const rows = response.message?.rows || [];
						const body = rows.map((row) => `<tr><td>${esc(row.registration_number)}</td><td>${esc(row.customer_vehicle || "—")}</td><td>${esc(row.resolution)}</td><td>${row.duplicate ? __("Duplicate") : ""}</td></tr>`).join("");
						dialog.fields_dict.csv_text.$wrapper.after(`<div class="table-responsive mt-3"><table class="table table-bordered table-sm"><thead><tr><th>${__("Registration")}</th><th>${__("Customer Vehicle")}</th><th>${__("Resolution")}</th><th>${__("Error")}</th></tr></thead><tbody>${body}</tbody></table></div>`);
						dialog.enable_primary_action();
					})
					.catch(() => dialog.enable_primary_action());
			},
		});
		dialog.show();
	}

	function add_actions(frm) {
		if (frm.is_new()) return;
		const writable = can_write(frm);
		if (frm.doc.docstatus === 0 && writable) {
			frm.add_custom_button(__("Preview CSV"), () => preview_dialog(frm), __("Vehicles"));
			frm.add_custom_button(__("Import Vehicles"), () => import_dialog(frm), __("Vehicles"));
			frm.add_custom_button(__("Resolve Vehicles"), () => frappe.call({ method: `${CONTROLLER}.resolve_vehicle_rows`, type: "POST", args: { lpo_name: frm.doc.name } }).then(() => frm.reload_doc()), __("Vehicles"));
			frm.add_custom_button(__("Create Missing Vehicles"), () => frappe.confirm(__("Create minimal Customer Vehicle records for every unresolved registration?"), () => frappe.call({ method: `${CONTROLLER}.resolve_vehicle_rows`, type: "POST", args: { lpo_name: frm.doc.name, create_confirmed: 1 } }).then(() => frm.reload_doc())), __("Vehicles"));
		}
		if (frm.doc.docstatus === 1 && !frm.doc.fleet_service_campaign && writable) {
			frm.add_custom_button(__("Create Campaign & Jobs"), () => frappe.call({ method: `${CONTROLLER}.create_campaign_and_repair_jobs`, type: "POST", args: { lpo_name: frm.doc.name } }).then(() => frm.reload_doc()), __("Workflow"));
		}
		if (frm.doc.docstatus === 1 && frm.doc.fleet_service_campaign) {
			if (frappe.model.can_create("Customer LPO Amendment")) {
				frm.add_custom_button(__("Add Amendment"), () => frappe.new_doc("Customer LPO Amendment", { customer_lpo: frm.doc.name }), __("Workflow"));
			}
			if (frappe.model.can_create("Sales Order")) frm.add_custom_button(__("Create Proforma"), () => frappe.model.open_mapped_doc({ method: `${CONTROLLER}.make_sales_order`, frm, source_name: frm.doc.name }), __("Billing"));
			if (frappe.model.can_create("Sales Invoice")) frm.add_custom_button(__("Create Invoice"), () => frappe.model.open_mapped_doc({ method: `${CONTROLLER}.make_sales_invoice`, frm, source_name: frm.doc.name }), __("Billing"));
			if (writable) frm.add_custom_button(__("Close LPO"), () => frappe.confirm(__("Close this LPO after checking all linked jobs?"), () => frappe.call({ method: `${CONTROLLER}.close_lpo`, type: "POST", args: { lpo_name: frm.doc.name } }).then(() => frm.reload_doc())), __("Workflow"));
		}
	}

	frappe.ui.form.on("Customer LPO", {
		refresh(frm) {
			add_actions(frm);
			refresh_summary(frm);
		},
	});
})();
