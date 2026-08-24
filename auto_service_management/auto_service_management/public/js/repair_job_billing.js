(function () {
	function esc(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	}

	function amount(value) {
		return frappe.format(value || 0, { fieldtype: "Currency" });
	}

	function form_link(doctype, name, fallback) {
		if (!name) {
			return fallback || "—";
		}
		return frappe.utils.get_form_link(doctype, name, true, esc(name));
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
			const invoice = form_link("Sales Invoice", row.sales_invoice);
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

	function load_sales_order_components(options) {
		return frappe.call({
			method: "auto_service_management.auto_service_management.integration.erpnext.component_mapping.get_sales_order_components",
			type: "GET",
			args: {
				repair_job_name: options.repairJob,
				service_name: options.serviceName || undefined,
			},
		}).then((response) => response.message || { components: [], counts: {}, totals: {} });
	}

	function sales_order_state(row) {
		return row.sales_order_state || row.order_state || row.component_state || row.invoice_state || "Unordered";
	}

	function sales_order_link(name) {
		return form_link("Sales Order", name, `<span class="text-muted">${__("Not created")}</span>`);
	}

	function render_sales_order_summary(frm, fieldname, data) {
		const field = frm.fields_dict[fieldname];
		if (!field) return;
		const counts = data.counts || {};
		const rows = (data.components || []).map((row) => {
			const state = sales_order_state(row);
			const indicator = state === "Submitted" || state === "Billed" || state === "Available" ? "green"
				: state === "Draft" || state === "Reserved" ? "orange"
				: state === "Cancelled" || state === "Invoiced" ? "gray" : "red";
			return `<tr><td>${esc(row.service_name || "—")}</td><td>${esc(row.component_type || row.service_type || "—")}</td><td>${esc(row.description || row.service_description || row.item_code || "—")}</td><td>${row.quantity || row.invoice_quantity || 0}</td><td>${amount(row.amount || row.invoice_amount)}</td><td><span class="indicator-pill ${indicator}">${esc(state)}</span></td><td>${sales_order_link(row.sales_order)}</td></tr>`;
		}).join("");
		field.$wrapper.html(`<div class="text-muted small mb-2">${__("Available")}: <b>${counts.Available || counts.Unordered || 0}</b> · ${__("Invoiced")}: <b>${counts.Invoiced || 0}</b> · ${__("Not Billable")}: <b>${counts["Not Billable"] || 0}</b></div><div class="table-responsive"><table class="table table-bordered table-sm"><thead><tr><th>${__("Service")}</th><th>${__("Type")}</th><th>${__("Component")}</th><th>${__("Qty")}</th><th>${__("Amount")}</th><th>${__("Proforma State")}</th><th>${__("Sales Order")}</th></tr></thead><tbody>${rows || `<tr><td colspan="7" class="text-muted">${__("No service components found.")}</td></tr>`}</tbody></table></div>`);
	}

	function render_sales_order_loading(frm, fieldname) {
		const field = frm.fields_dict[fieldname];
		if (field) field.$wrapper.html(`<div class="text-muted small">${__("Loading Proforma Invoice components…")}</div>`);
	}

	function render_sales_order_error(frm, fieldname) {
		const field = frm.fields_dict[fieldname];
		if (field) field.$wrapper.html(`<div class="text-danger small">${__("Unable to load Sales Order component status. Refresh to try again.")}</div>`);
	}

	function open_sales_order_dialog(frm, options, data) {
		const rows = (data.components || []).filter((row) => {
			const state = sales_order_state(row);
			return row.selectable !== false && row.billable !== false && state !== "Invoiced";
		});
		if (!rows.length) {
			frappe.msgprint(__("There are no selectable billable components available for a Proforma Invoice."));
			return;
		}
		const html = rows.map((row, index) => {
			const state = sales_order_state(row);
			const existing = row.sales_order ? ` · ${__("Existing")}: ${sales_order_link(row.sales_order)}` : "";
			return `<label class="d-flex align-items-start mb-2"><input type="checkbox" class="sales-order-component-choice mr-2 mt-1" data-index="${index}" checked><span><b>${esc(row.service_name || "—")}</b> · ${esc(row.component_type || row.service_type || "—")} · ${esc(row.description || row.service_description || row.item_code || "—")}<br><span class="text-muted">${__("Quantity")}: ${row.quantity || row.invoice_quantity || 0} · ${__("Amount")}: ${amount(row.amount || row.invoice_amount)} · ${__("State")}: ${esc(state)}${existing}</span></span></label>`;
		}).join("");
		const dialog = new frappe.ui.Dialog({
			title: options.title || __("Select components for Proforma Invoice (Sales Order)"),
			fields: [{ fieldname: "components_html", fieldtype: "HTML" }],
			primary_action_label: __("Create Draft Sales Order"),
			primary_action() {
				const selected = [...dialog.fields_dict.components_html.$wrapper.find(".sales-order-component-choice:checked")]
					.map((input) => rows[Number(input.dataset.index)]);
				if (!selected.length) {
					frappe.msgprint(__("Select at least one component."));
					return;
				}
				dialog.hide();
				frappe.model.open_mapped_doc({
					method: options.method,
					frm,
					args: {
						component_refs: JSON.stringify(selected.map((row) => ({
							doctype: row.component_doctype || row.row_doctype || row.doctype,
							name: row.component_name || row.row_name || row.name,
						}))),
					},
				});
			},
		});
		dialog.fields_dict.components_html.$wrapper.html(html);
		dialog.show();
	}

	window.auto_service_sales_orders = {
		setup(frm, options) {
			if (frm.is_new()) return;
			const load_options = { repairJob: options.repairJob || frm.doc.name, serviceName: options.serviceName };
			render_sales_order_loading(frm, options.fieldname);
			load_sales_order_components(load_options)
				.then((data) => render_sales_order_summary(frm, options.fieldname, data))
				.catch(() => render_sales_order_error(frm, options.fieldname));
			frm.add_custom_button(__("Proforma Invoice (Sales Order)"), () => {
				render_sales_order_loading(frm, options.fieldname);
				load_sales_order_components(load_options)
					.then((data) => open_sales_order_dialog(frm, options, data))
					.catch(() => frappe.msgprint(__("Unable to load components. Refresh and try again.")));
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
		return form_link("Material Request", name, __("Not Requested"));
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
