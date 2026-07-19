frappe.ui.form.on('Material Request', {
    refresh: function(frm) {
        if (frm.doc.docstatus !== 0) return;

        frm.add_custom_button(__('Repair Job'), function() {
            erpnext.utils.map_current_doc({
				method: 'auto_service_management.auto_service_management.doctype.repair_job.repair_job.make_material_request',
				source_doctype: 'Repair Job',
				target: frm,
				setters: { company: frm.doc.company || undefined },
			});
		}, __('Get Items From'));

        frm.add_custom_button(__('Repair Job Service'), function() {
            erpnext.utils.map_current_doc({
                method: 'auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service.make_material_request',
                source_doctype: 'Repair Job Service',
                target: frm,
                setters: { repair_job: frm.doc.repair_job || undefined },
                get_query_filters: frm.doc.repair_job ? { repair_job: frm.doc.repair_job } : {},
            });
        }, __('Get Items From'));
    },
});
