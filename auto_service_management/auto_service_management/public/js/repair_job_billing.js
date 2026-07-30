(function () {
	function esc(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	}

	function amount(value) {
		return frappe.format(value || 0, { fieldtype: "Currency" });
	}

	function load_data(options) {
		return frappe.call({
			method: "auto_service_management.auto_service_management.integration.erpnext.component_mapping.get_sales_invoice_components",
			type: "GET",
			args: {
				repair_job_name: options.repairJob,
				service_name: options.serviceName || undefined,
			},
		}).then((response) => response.message || { components: [], counts: {}, totals: {} });
	}

	function render_summary(frm, fieldname, data) {
		const field = frm.fields_dict[fieldname];
		if (!field) return;
		const counts = data.counts || {};
		const rows = (data.components || []).map((row) => {
			const invoice = row.sales_invoice
				? `<a href="/app/sales-invoice/${encodeURIComponent(row.sales_invoice)}">${esc(row.sales_invoice)}</a>`
				: "—";
			return `<tr><td>${esc(row.service_name)}</td><td>${esc(row.component_type)}</td><td>${esc(row.description)}</td><td>${row.quantity || 0}</td><td>${amount(row.amount)}</td><td><span class="indicator-pill ${row.invoice_state === "Invoiced" ? "green" : row.invoice_state === "Reserved" ? "orange" : row.invoice_state === "Unbilled" ? "red" : "gray"}">${esc(row.invoice_state)}</span></td><td>${invoice}</td></tr>`;
		}).join("");
		field.$wrapper.html(`<div class="text-muted small mb-2">Unbilled: <b>${counts["Unbilled"] || 0}</b> · Reserved: <b>${counts["Reserved"] || 0}</b> · Invoiced: <b>${counts["Invoiced"] || 0}</b></div><div class="table-responsive"><table class="table table-bordered table-sm"><thead><tr><th>Service</th><th>Type</th><th>Component</th><th>Qty</th><th>Amount</th><th>Billing State</th><th>Invoice</th></tr></thead><tbody>${rows || `<tr><td colspan="7" class="text-muted">No service components found.</td></tr>`}</tbody></table></div>`);
	}

	function open_dialog(frm, options, data) {
		const rows = (data.components || []).filter((row) => row.invoice_state === "Unbilled" && row.billable);
		if (!rows.length) {
			frappe.msgprint(__("There are no unbilled billable components available for invoicing."));
			return;
		}
		const html = rows.map((row, index) => `<label class="d-flex align-items-center mb-2"><input type="checkbox" class="billing-component-choice mr-2" data-index="${index}" checked><span>${esc(row.service_name)} · ${esc(row.component_type)} · ${esc(row.description)} · ${row.quantity || 0} × ${amount(row.amount)}</span></label>`).join("");
		const dialog = new frappe.ui.Dialog({
			title: options.title || __("Select components to invoice"),
			fields: [{ fieldname: "components_html", fieldtype: "HTML" }],
			primary_action_label: __("Create Draft Invoice"),
			primary_action() {
				const selected = [...dialog.fields_dict.components_html.$wrapper.find(".billing-component-choice:checked")].map((input) => rows[Number(input.dataset.index)]);
				if (!selected.length) {
					frappe.msgprint(__("Select at least one component."));
					return;
				}
				dialog.hide();
				frappe.model.open_mapped_doc({
					method: options.method,
					frm,
					args: { component_refs: JSON.stringify(selected.map((row) => ({ doctype: row.component_doctype, name: row.component_name }))) },
				});
			},
		});
		dialog.fields_dict.components_html.$wrapper.html(html);
		dialog.show();
	}

	window.auto_service_billing = {
		setup(frm, options) {
			if (frm.is_new()) return;
			const load_options = { repairJob: options.repairJob || frm.doc.name, serviceName: options.serviceName };
			load_data(load_options).then((data) => render_summary(frm, options.fieldname, data));
			frm.add_custom_button(__("Sales Invoice"), () => {
				load_data(load_options).then((data) => open_dialog(frm, options, data));
			}, __("Create"));
		},
	};

	function load_material_requests(options) {
		return frappe.call({
			method: "auto_service_management.auto_service_management.integration.erpnext.component_mapping.get_material_request_components",
			type: "GET",
			args: {
				repair_job_name: options.repairJob,
				service_name: options.serviceName || undefined,
			},
		}).then((response) => response.message || { components: [], counts: {}, material_request_types: [] });
	}

	function material_request_link(name) {
		return name
			? `<a href="/app/material-request/${encodeURIComponent(name)}">${esc(name)}</a>`
			: __("Not Requested");
	}

	function render_request_history(history) {
		if (!history?.length) return `<span class="text-muted">${__("No request history")}</span>`;
		return history.map((entry) => (
			`<div>${material_request_link(entry.material_request)} · ${esc(entry.material_request_type)} · ${esc(entry.status)}</div>`
		)).join("");
	}

	function render_material_request_summary(frm, fieldname, data) {
		const field = frm.fields_dict[fieldname];
		if (!field) return;
		const counts = data.counts || {};
		const rows = (data.components || []).map((row) => {
			const indicator = row.request_state === "Active" ? "orange" : row.request_state === "Completed" ? "green" : "gray";
			return `<tr><td>${esc(row.service_name)}</td><td>${esc(row.component_type)}</td><td>${esc(row.description)}</td><td>${row.quantity || 0}</td><td>${esc(row.warehouse || "—")}</td><td>${row.actual_qty || 0}</td><td><span class="indicator-pill ${indicator}">${esc(row.request_state)}</span></td><td>${material_request_link(row.material_request)}</td><td>${render_request_history(row.history)}</td></tr>`;
		}).join("");
		field.$wrapper.html(`<div class="text-muted small mb-2">${__("Not Requested")}: <b>${counts["Not Requested"] || 0}</b> · ${__("Active")}: <b>${counts.Active || 0}</b> · ${__("Completed")}: <b>${counts.Completed || 0}</b></div><div class="table-responsive"><table class="table table-bordered table-sm"><thead><tr><th>${__("Service")}</th><th>${__("Type")}</th><th>${__("Component")}</th><th>${__("Qty")}</th><th>${__("Warehouse")}</th><th>${__("Available")}</th><th>${__("Request State")}</th><th>${__("Current Request")}</th><th>${__("Request History")}</th></tr></thead><tbody>${rows || `<tr><td colspan="9" class="text-muted">${__("No Parts or Consumables found.")}</td></tr>`}</tbody></table></div>`);
	}

	function open_material_request_dialog(frm, options, data) {
		const rows = data.components || [];
		if (!rows.some((row) => row.selectable)) {
			frappe.msgprint(__("Every Part and Consumable in scope already has an active Material Request."));
			return;
		}
		const dialog = new frappe.ui.Dialog({
			title: options.title || __("Create Material Request for Repair Job"),
			fields: [
				{
					fieldname: "material_request_type",
					fieldtype: "Select",
					label: __("Material Request Purpose"),
					options: data.material_request_types || [],
					default: "Material Issue",
					reqd: 1,
				},
				{ fieldname: "components_html", fieldtype: "HTML" },
			],
			primary_action_label: __("Create Draft Material Request"),
			primary_action(values) {
				const selected = [...dialog.fields_dict.components_html.$wrapper.find(".material-request-component-choice:checked")]
					.map((input) => rows[Number(input.dataset.index)]);
				if (!selected.length) {
					frappe.msgprint(__("Select at least one Part or Consumable."));
					return;
				}
				dialog.hide();
				frappe.model.open_mapped_doc({
					method: options.method,
					frm,
					args: {
						component_refs: JSON.stringify(selected.map((row) => ({
							doctype: row.component_doctype,
							name: row.component_name,
						}))),
						material_request_type: values.material_request_type,
					},
				});
			},
		});
		const html = rows.map((row, index) => {
			const disabled = row.selectable ? "" : "disabled";
			const checked = row.selectable ? "checked" : "";
			return `<div class="border rounded p-2 mb-2"><label class="d-flex align-items-start mb-1"><input type="checkbox" class="material-request-component-choice mr-2 mt-1" data-index="${index}" ${checked} ${disabled}><span><b>${esc(row.service_name)}</b> · ${esc(row.component_type)} · ${esc(row.description)}<br><span class="text-muted">${__("Quantity")}: ${row.quantity || 0} · ${__("Warehouse")}: ${esc(row.warehouse || "—")} · ${__("Available stock")}: ${row.actual_qty || 0} · ${__("State")}: ${esc(row.request_state)}</span></span></label><div class="small ml-4">${render_request_history(row.history)}</div></div>`;
		}).join("");
		dialog.fields_dict.components_html.$wrapper.html(html);
		dialog.show();
	}

	window.auto_service_material_requests = {
		setup(frm, options) {
			if (frm.is_new()) return;
			const load_options = { repairJob: options.repairJob || frm.doc.name, serviceName: options.serviceName };
			load_material_requests(load_options)
				.then((data) => render_material_request_summary(frm, options.fieldname, data));
			frm.add_custom_button(__("Material Request"), () => {
				load_material_requests(load_options)
					.then((data) => open_material_request_dialog(frm, options, data));
			}, __("Create"));
		},
	};
})();
