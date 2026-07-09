frappe.ui.form.on("Repair Job Service", {
	setup(frm) {
		frm.set_query("diagnosis_report", () => {
			if (!frm.doc.repair_job) { return { filters: { name: ["=", ""] } }; }
			return { filters: { repair_job: frm.doc.repair_job } };
		});
	},
	refresh(frm) {
		if (frm.doc.repair_job) {
			frm.add_custom_button("Open Repair Job", () => {
				frappe.set_route("Form", "Repair Job", frm.doc.repair_job);
			});
		}
	},
});

const BILLABLE_CHILDREN = ["Repair Job Service Part", "Repair Job Service Consumable"];
BILLABLE_CHILDREN.forEach((cdt) => {
	frappe.ui.form.on(cdt, {
		item_code(frm, cdt, cdn) { auto_fill_rate(frm, cdt, cdn); },
		quantity(frm, cdt, cdn) { calculate_amount(frm, cdt, cdn); },
		rate(frm, cdt, cdn) { calculate_amount(frm, cdt, cdn); },
		discount_percentage(frm, cdt, cdn) { calculate_amount(frm, cdt, cdn); },
	});
});

function auto_fill_rate(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (!row.item_code) return;
	let pl = frappe.defaults.get_default("selling_price_list");
	let filters = { item_code: row.item_code };
	if (pl) filters.price_list = pl;
	frappe.call({
		method: "frappe.client.get_value",
		args: { doctype: "Item Price", filters: filters, fieldname: ["price_list_rate", "currency"] },
		callback(r) {
			if (r.message && r.message.price_list_rate) {
				frappe.model.set_value(cdt, cdn, "rate", r.message.price_list_rate);
				if (r.message.currency && !frm.doc.currency) frm.set_value("currency", r.message.currency);
				calculate_amount(frm, cdt, cdn);
			}
		},
	});
}

function calculate_amount(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let qty = row.quantity || 0; let rate = row.rate || 0;
	let dp = row.discount_percentage || 0; let cr = row.cost_rate || 0;
	let gross = qty * rate; let disc = gross * dp / 100; let amt = gross - disc;
	let cost = qty * cr; let margin = amt - cost; let mp = amt ? (margin / amt * 100) : 0;
	frappe.model.set_value(cdt, cdn, "amount", amt);
	frappe.model.set_value(cdt, cdn, "discount_amount", disc);
	frappe.model.set_value(cdt, cdn, "cost_amount", cost);
	frappe.model.set_value(cdt, cdn, "margin_amount", margin);
	frappe.model.set_value(cdt, cdn, "margin_percentage", mp);
}