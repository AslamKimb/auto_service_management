(function () {
	const CAMPAIGN_CONTROLLER =
		"auto_service_management.auto_service_management.doctype.fleet_service_campaign.fleet_service_campaign";
	const COMPONENT_CONTROLLER =
		"auto_service_management.auto_service_management.integration.erpnext.component_mapping";

	function esc(value) {
		return frappe.utils.escape_html(String(value ?? ""));
	}

	function money(value, currency) {
		return frappe.format(value || 0, { fieldtype: "Currency", options: currency });
	}

	function date(value) {
		return value ? frappe.datetime.str_to_user(value) : "—";
	}

	function can_write(frm) {
		return Boolean(frm.perm?.[0]?.write);
	}

	function can_read(doctype) {
		return frappe.model.can_read(doctype);
	}

	function route_to_list(doctype, campaign) {
		frappe.route_options = { fleet_service_campaign: campaign };
		frappe.set_route("List", doctype);
	}

	function indicator_class(state) {
		if (["Submitted", "Paid", "Completed", "Available"].includes(state)) return "green";
		if (["Draft", "Unpaid", "Overdue", "Reserved", "Ordered"].includes(state)) return "orange";
		if (["Cancelled", "Closed", "Invoiced", "Not Billable"].includes(state)) return "gray";
		return "blue";
	}

	function status_pill(state) {
		const label = state || __("Unknown");
		return `<span class="indicator-pill ${indicator_class(label)}">${esc(label)}</span>`;
	}

	function set_field_html(frm, fieldname, html) {
		const field = frm.fields_dict[fieldname];
		if (field) field.$wrapper.html(html);
	}

	function render_tracking_loading(frm) {
		const loading = `<div class="text-muted small" role="status">${__("Loading campaign sales documents…")}</div>`;
		set_field_html(frm, "sales_orders_html", loading);
		set_field_html(frm, "sales_invoices_html", loading);
	}

	function render_tracking_error(frm) {
		const error = `<div class="text-danger small" role="alert">${__("Unable to load campaign sales documents. Refresh to try again.")}</div>`;
		set_field_html(frm, "sales_orders_html", error);
		set_field_html(frm, "sales_invoices_html", error);
	}

	function document_link(doctype, name) {
		return frappe.utils.get_form_link(doctype, name, true, esc(name));
	}

	function render_sales_orders(frm, rows) {
		if (!can_read("Sales Order")) {
			set_field_html(frm, "sales_orders_html", `<div class="text-muted small">${__("Sales Orders are not available for your role.")}</div>`);
			return;
		}
		const body = (rows || []).map((row) => `<tr>
			<td>${document_link("Sales Order", row.name)}</td>
			<td>${date(row.transaction_date)}</td>
			<td>${date(row.delivery_date)}</td>
			<td>${status_pill(row.status)}</td>
			<td class="text-right">${money(row.grand_total, row.currency)}</td>
			<td class="text-right">${frappe.format(row.per_billed || 0, { fieldtype: "Percent" })}</td>
		</tr>`).join("");
		set_field_html(frm, "sales_orders_html", `<div class="table-responsive"><table class="table table-bordered table-sm">
			<thead><tr><th scope="col">${__("Sales Order")}</th><th scope="col">${__("Date")}</th><th scope="col">${__("Delivery")}</th><th scope="col">${__("Status")}</th><th scope="col" class="text-right">${__("Total")}</th><th scope="col" class="text-right">${__("Billed")}</th></tr></thead>
			<tbody>${body || `<tr><td colspan="6" class="text-muted">${__("No Sales Orders have been created for this campaign.")}</td></tr>`}</tbody>
		</table></div>`);
	}

	function render_sales_invoices(frm, rows) {
		if (!can_read("Sales Invoice")) {
			set_field_html(frm, "sales_invoices_html", `<div class="text-muted small">${__("Sales Invoices are not available for your role.")}</div>`);
			return;
		}
		const body = (rows || []).map((row) => `<tr>
			<td>${document_link("Sales Invoice", row.name)}</td>
			<td>${date(row.posting_date)}</td>
			<td>${status_pill(row.status)}</td>
			<td class="text-right">${money(row.grand_total, row.currency)}</td>
			<td class="text-right">${money(row.outstanding_amount, row.currency)}</td>
		</tr>`).join("");
		set_field_html(frm, "sales_invoices_html", `<div class="table-responsive"><table class="table table-bordered table-sm">
			<thead><tr><th scope="col">${__("Sales Invoice")}</th><th scope="col">${__("Posting Date")}</th><th scope="col">${__("Status")}</th><th scope="col" class="text-right">${__("Total")}</th><th scope="col" class="text-right">${__("Outstanding")}</th></tr></thead>
			<tbody>${body || `<tr><td colspan="5" class="text-muted">${__("No Sales Invoices have been created for this campaign.")}</td></tr>`}</tbody>
		</table></div>`);
	}

	function load_tracking(frm) {
		if (frm.is_new()) return;
		render_tracking_loading(frm);
		frappe.call({
			method: `${CAMPAIGN_CONTROLLER}.get_campaign_sales_document_summary`,
			type: "GET",
			args: { campaign_name: frm.doc.name },
		}).then((response) => {
			const data = response.message || {};
			render_sales_orders(frm, data.sales_orders || []);
			render_sales_invoices(frm, data.sales_invoices || []);
		}).catch(() => render_tracking_error(frm));
	}

	function component_state(row, kind) {
		return kind === "order"
			? row.sales_order_state || row.order_state || "Available"
			: row.invoice_state || "Unbilled";
	}

	function component_description(row) {
		return row.description || row.item_code || row.component_name || "—";
	}

	function grouped_component_html(rows, kind) {
		if (!rows.length) {
			return `<div class="text-muted small">${__("No eligible components or campaign service components were found.")}</div>`;
		}
		const groups = new Map();
		rows.forEach((row, index) => {
			const job_key = row.repair_job || __("Repair Job not set");
			const service_key = row.repair_job_service || row.service_name || __("Service not set");
			if (!groups.has(job_key)) groups.set(job_key, new Map());
			const services = groups.get(job_key);
			if (!services.has(service_key)) services.set(service_key, []);
			services.get(service_key).push({ row, index });
		});

		return [...groups.entries()].map(([repair_job, services]) => {
			const first = [...services.values()][0]?.[0]?.row || {};
			const vehicle = first.registration_number || first.customer_vehicle || __("Vehicle not set");
			const service_blocks = [...services.entries()].map(([service, entries]) => {
				const body = entries.map(({ row, index }) => {
					const selectable = row.selectable === true;
					const state = component_state(row, kind);
					const disabled = selectable ? "" : " disabled";
					const checked = selectable ? " checked" : "";
					const aria = __("Select {0} from {1}", [component_description(row), service]);
					return `<tr class="${selectable ? "" : "text-muted"}">
						<td><label class="d-flex align-items-start mb-0"><input type="checkbox" class="campaign-component-choice mr-2 mt-1" data-index="${index}" aria-label="${esc(aria)}"${checked}${disabled}><span>${esc(component_description(row))}</span></label></td>
						<td>${esc(row.component_type || "—")}</td><td>${row.quantity || 0}</td><td class="text-right">${money(row.amount, row.currency)}</td><td>${status_pill(state)}</td>
					</tr>`;
				}).join("");
				return `<div class="mb-3"><div class="small font-weight-bold mb-1">${esc(service)}</div><div class="table-responsive"><table class="table table-bordered table-sm mb-0"><thead><tr><th scope="col">${__("Component")}</th><th scope="col">${__("Type")}</th><th scope="col">${__("Qty")}</th><th scope="col" class="text-right">${__("Amount")}</th><th scope="col">${__("State")}</th></tr></thead><tbody>${body}</tbody></table></div></div>`;
			}).join("");
			return `<section class="border rounded p-3 mb-3" aria-label="${esc(repair_job)}"><h6 class="mb-1">${esc(repair_job)}</h6><div class="text-muted small mb-3">${__("Vehicle")}: ${esc(vehicle)}</div>${service_blocks}</section>`;
		}).join("");
	}

	function open_component_dialog(frm, config) {
		const dialog = new frappe.ui.Dialog({
			title: config.title,
			size: "extra-large",
			fields: [{ fieldname: "components_html", fieldtype: "HTML" }],
			primary_action_label: config.primary_label,
			primary_action() {
				const selected = [...dialog.fields_dict.components_html.$wrapper.find(".campaign-component-choice:checked:not(:disabled)")]
					.map((input) => config.rows[Number(input.dataset.index)]);
				if (!selected.length) {
					frappe.msgprint(__("Select at least one eligible component."));
					return;
				}
				dialog.hide();
				frappe.model.open_mapped_doc({
					method: config.mapper,
					frm,
					args: {
						component_refs: JSON.stringify(selected.map((row) => ({
							doctype: row.component_doctype,
							name: row.component_name,
						}))),
					},
				});
			},
		});
		dialog.show();
		dialog.disable_primary_action();
		dialog.fields_dict.components_html.$wrapper.html(`<div class="text-muted small" role="status">${__("Loading campaign components…")}</div>`);
		frappe.call({
			method: config.selector,
			type: "GET",
			args: { campaign_name: frm.doc.name },
		}).then((response) => {
			config.rows = response.message?.components || [];
			dialog.fields_dict.components_html.$wrapper.html(grouped_component_html(config.rows, config.kind));
			if (config.rows.some((row) => row.selectable === true)) dialog.enable_primary_action();
		}).catch(() => {
			dialog.fields_dict.components_html.$wrapper.html(`<div class="text-danger small" role="alert">${__("Unable to load campaign components. Close this dialog and try again.")}</div>`);
		});
	}

	function add_create_actions(frm) {
		if (!can_write(frm)) return;
		const active_for_jobs = ["Draft", "Ongoing"].includes(frm.doc.status || "Draft");
		const active_for_billing = frm.doc.status !== "Cancelled";
		if (active_for_jobs && frappe.model.can_create("Repair Job")) {
			frm.add_custom_button(__("Repair Job"), () => frappe.model.open_mapped_doc({
				method: `${CAMPAIGN_CONTROLLER}.make_repair_job`, frm,
			}), __("Create"));
		}
		if (active_for_billing && frappe.model.can_create("Sales Order")) {
			frm.add_custom_button(__("Proforma Invoice (Sales Order)"), () => open_component_dialog(frm, {
				title: __("Select campaign components for Proforma Invoice"),
				primary_label: __("Create Draft Sales Order"),
				selector: `${COMPONENT_CONTROLLER}.get_campaign_sales_order_components`,
				mapper: `${CAMPAIGN_CONTROLLER}.make_sales_order`,
				kind: "order",
				rows: [],
			}), __("Create"));
		}
		if (active_for_billing && frappe.model.can_create("Sales Invoice")) {
			frm.add_custom_button(__("Sales Invoice"), () => open_component_dialog(frm, {
				title: __("Select campaign components for Sales Invoice"),
				primary_label: __("Create Draft Sales Invoice"),
				selector: `${COMPONENT_CONTROLLER}.get_campaign_sales_invoice_components`,
				mapper: `${CAMPAIGN_CONTROLLER}.make_sales_invoice`,
				kind: "invoice",
				rows: [],
			}), __("Create"));
		}
	}

	function add_related_actions(frm) {
		if (can_read("Repair Job")) {
			frm.add_custom_button(__("Repair Jobs"), () => route_to_list("Repair Job", frm.doc.name), __("Related Documents"));
		}
		if (can_read("Sales Order")) {
			frm.add_custom_button(__("Sales Orders"), () => route_to_list("Sales Order", frm.doc.name), __("Related Documents"));
		}
		if (can_read("Sales Invoice")) {
			frm.add_custom_button(__("Sales Invoices"), () => route_to_list("Sales Invoice", frm.doc.name), __("Related Documents"));
		}
	}

	frappe.ui.form.on("Fleet Service Campaign", {
		setup(frm) {
			frm.set_query("repair_job", "fleet_jobs", () => ({
				filters: { customer: frm.doc.customer },
			}));
		},

		refresh(frm) {
			if (frm.is_new()) return;
			add_create_actions(frm);
			add_related_actions(frm);
			load_tracking(frm);
		},
	});
})();
