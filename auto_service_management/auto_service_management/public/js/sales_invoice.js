frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        if (frm.doc.docstatus !== 0) return;

        frm.add_custom_button(__('Repair Job'), function() {
            erpnext.utils.map_current_doc({
                method: 'auto_service_management.auto_service_management.doctype.repair_job.repair_job.make_sales_invoice',
                source_doctype: 'Repair Job',
                target: frm,
                setters: { customer: frm.doc.customer || undefined },
                get_query_filters: {
                    job_status: ['in', ['Approved', 'Ready for Invoice']],
                    customer: frm.doc.customer || undefined,
                },
            });
        }, __('Get Items From'));

        frm.add_custom_button(__('Repair Job Service'), function() {
            erpnext.utils.map_current_doc({
                method: 'auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service.make_sales_invoice',
                source_doctype: 'Repair Job Service',
                target: frm,
                setters: { repair_job: frm.doc.repair_job || undefined },
                get_query_filters: {
                    ...(frm.doc.repair_job ? { repair_job: frm.doc.repair_job } : {}),
                    status: ['in', ['Approved', 'Completed']],
                },
            });
        }, __('Get Items From'));
    },
});
