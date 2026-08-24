frappe.ui.form.on("Repair Job Service Template", {
	setup(frm) {
		frm.set_query("vehicle_model", () => {
			if (!frm.doc.vehicle_make) {
				return { filters: { name: ["=", ""] } };
			}
			return { filters: { vehicle_make: frm.doc.vehicle_make } };
		});
	},
	vehicle_make(frm) {
		if (frm.doc.vehicle_model) {
			frm.set_value("vehicle_model", "");
		}
	},
	refresh(frm) {
		if (frm.is_new() || !frappe.model.can_create("Repair Job Service")) return;
		frm.add_custom_button(__("Create Repair Job Service"), () => {
			frappe.call({
				method: "auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service.make_repair_job_service",
				args: { source_name: frm.doc.name },
				 type: "POST",
				callback(r) {
					const docs = r.message ? frappe.model.sync(r.message) : [];
					const service = docs[0];
					if (service?.name) frappe.set_route("Form", service.doctype, service.name);
				},
			});
		}, __("Actions"));
	},
});
