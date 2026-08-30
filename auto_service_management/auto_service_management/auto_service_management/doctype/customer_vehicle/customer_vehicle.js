frappe.ui.form.on("Customer Vehicle", {
	refresh(frm) {
		load_customer_association_history(frm);
	},

	setup(frm) {
		frm.set_query("model", () => {
			if (!frm.doc.make) {
				return { filters: { name: ["=", ""] } };
			}
			return { filters: { vehicle_make: frm.doc.make } };
		});
		frm.set_query("engine_model", () => ({}));
	},

	make(frm) {
		if (frm.doc.model) {
			frm.set_value("model", "");
		}
	},
});

function load_customer_association_history(frm) {
	const field = frm.fields_dict.customer_association_history;
	if (!field) return;
	if (frm.is_new()) {
		field.$wrapper.html(`<div class="text-muted">${__("Save the vehicle to view customer history.")}</div>`);
		return;
	}
	field.$wrapper.html(`<div class="text-muted">${__("Loading customer history…")}</div>`);
	frappe.call({
		method: "auto_service_management.auto_service_management.doctype.customer_vehicle.customer_vehicle.get_customer_vehicle_association_history",
		args: { customer_vehicle: frm.doc.name }, type: "GET",
		callback(response) {
			const rows = response.message?.history || [];
			if (!rows.length) {
				field.$wrapper.html(`<div class="text-muted">${__("No customer association history yet.")}</div>`);
				return;
			}
			const escape = frappe.utils.escape_html;
			const body = rows.map((row) => `<tr><td>${escape(row.customer || "")}</td><td>${escape(row.valid_from || "")}</td><td>${escape(row.valid_to || __("Current"))}</td></tr>`).join("");
			field.$wrapper.html(`<div class="table-responsive"><table class="table table-bordered table-sm"><thead><tr><th>${__("Customer")}</th><th>${__("From")}</th><th>${__("To")}</th></tr></thead><tbody>${body}</tbody></table></div>`);
		},
	});
}
