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
})();
