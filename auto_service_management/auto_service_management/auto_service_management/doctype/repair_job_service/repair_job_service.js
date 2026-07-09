frappe.ui.form.on("Repair Job Service", {
	setup(frm) {
		frm.set_query("diagnosis_report", () => {
			if (!frm.doc.repair_job) {
				return { filters: { name: ["=", ""] } };
			}
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
