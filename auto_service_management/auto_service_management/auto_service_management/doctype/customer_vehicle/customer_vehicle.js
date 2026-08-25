frappe.ui.form.on("Customer Vehicle", {
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
