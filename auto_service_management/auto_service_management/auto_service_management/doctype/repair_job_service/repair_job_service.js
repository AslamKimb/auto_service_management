frappe.ui.form.on('Repair Job Service', {
    setup: function(frm) {
        frm.set_query('diagnosis_report', function() {
            if (!frm.doc.repair_job) { return { filters: { name: ['=', ''] } }; }
            return { filters: { repair_job: frm.doc.repair_job } };
        });
        frm._default_labour_rate = 0;
        frm._default_warehouse = '';
        frm._settings_loaded = false;
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'Auto Service Settings',
                filters: { name: 'Auto Service Settings' },
                fieldname: ['default_labour_rate', 'default_warehouse'],
            },
            callback: function(r) {
                if (r.message) {
                    frm._default_labour_rate = r.message.default_labour_rate || 0;
                    frm._default_warehouse = r.message.default_warehouse || '';
                }
                frm._settings_loaded = true;
                sweep_labour_defaults(frm);
            },
        });
    },
    refresh: function(frm) {
        if (frm.doc.repair_job) {
            frm.add_custom_button('Open Repair Job', function() {
                frappe.set_route('Form', 'Repair Job', frm.doc.repair_job);
            });

            if (!frm.is_new()) {
                add_sales_invoice_button(frm);
                frm.add_custom_button(__('Material Request'), function() {
                    frappe.model.open_mapped_doc({
                        method: 'auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service.make_material_request',
                        frm: frm,
                    });
                }, __('Create'));
            }
        }
        sweep_labour_defaults(frm);
        calculate_service_totals(frm);
    },
    labour_add: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (!row) return;
        if (!row.billing_hours && row.hours) {
            frappe.model.set_value(cdt, cdn, 'billing_hours', row.hours);
        }
        apply_default_labour_rate(frm, cdt, cdn);
        calculate_labour_amount(frm, cdt, cdn);
    },
    parts_add: function(frm) { calculate_service_totals(frm); },
    consumables_add: function(frm) { calculate_service_totals(frm); },
    parts_remove: function(frm) { calculate_service_totals(frm); },
    consumables_remove: function(frm) { calculate_service_totals(frm); },
    labour_remove: function(frm) { calculate_service_totals(frm); },
});

function sweep_labour_defaults(frm) {
    if (!frm._settings_loaded || !frm._default_labour_rate) return;
    var rows = frm.doc.labour || [];
    for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        if (row.billable && !row.billing_rate) {
            frappe.model.set_value('Repair Job Service Labour', row.name, 'billing_rate', frm._default_labour_rate);
            if (!row.billing_hours && row.hours) {
                frappe.model.set_value('Repair Job Service Labour', row.name, 'billing_hours', row.hours);
            }
        }
    }
}

var BILLABLE_CHILDREN = ['Repair Job Service Part', 'Repair Job Service Consumable'];
BILLABLE_CHILDREN.forEach(function(cdt) {
    frappe.ui.form.on(cdt, {
        item_code: function(frm, cdt, cdn) {
            auto_fill_rate(frm, cdt, cdn);
            auto_fill_warehouse(frm, cdt, cdn);
            fetch_stock_qty(frm, cdt, cdn);
        },
        warehouse: function(frm, cdt, cdn) {
            fetch_stock_qty(frm, cdt, cdn);
        },
        quantity: function(frm, cdt, cdn) { calculate_amount(frm, cdt, cdn); },
        rate: function(frm, cdt, cdn) { calculate_amount(frm, cdt, cdn); },
        discount_percentage: function(frm, cdt, cdn) { calculate_amount(frm, cdt, cdn); },
        cost_rate: function(frm, cdt, cdn) { calculate_amount(frm, cdt, cdn); },
        billable: function(frm, cdt, cdn) {
            calculate_amount(frm, cdt, cdn);
            calculate_service_totals(frm);
        },
    });
});

function auto_fill_rate(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    if (!row.item_code) return;
    var pl = frappe.defaults.get_default('selling_price_list');
    var filters = { item_code: row.item_code };
    if (pl) filters.price_list = pl;
    frappe.call({
        method: 'frappe.client.get_value',
        args: { doctype: 'Item Price', filters: filters, fieldname: ['price_list_rate', 'currency'] },
        callback: function(r) {
            if (r.message && r.message.price_list_rate) {
                frappe.model.set_value(cdt, cdn, 'rate', r.message.price_list_rate);
                if (r.message.currency && !frm.doc.currency) frm.set_value('currency', r.message.currency);
                calculate_amount(frm, cdt, cdn);
            }
        },
    });
}

function auto_fill_warehouse(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    if (!row.item_code || row.warehouse) return;
    var wh = frm._default_warehouse || frappe.defaults.get_default('stock_warehouse');
    if (wh) {
        frappe.model.set_value(cdt, cdn, 'warehouse', wh);
    }
}

function fetch_stock_qty(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    if (!row.item_code || !row.warehouse) {
        frappe.model.set_value(cdt, cdn, 'actual_qty', 0);
        return;
    }
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Bin',
            filters: { item_code: row.item_code, warehouse: row.warehouse },
            fieldname: 'actual_qty',
        },
        callback: function(r) {
            var qty = (r.message && r.message.actual_qty) ? r.message.actual_qty : 0;
            frappe.model.set_value(cdt, cdn, 'actual_qty', qty);
        },
    });
}

function calculate_amount(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    var qty = row.quantity || 0;
    var rate = row.rate || 0;
    var dp = row.discount_percentage || 0;
    var cr = row.cost_rate || 0;
    var gross = qty * rate;
    var disc = gross * dp / 100;
    var amt = gross - disc;
    var cost = qty * cr;
    var margin = amt - cost;
    var mp = amt ? (margin / amt * 100) : 0;
    frappe.model.set_value(cdt, cdn, 'amount', amt);
    frappe.model.set_value(cdt, cdn, 'discount_amount', disc);
    frappe.model.set_value(cdt, cdn, 'cost_amount', cost);
    frappe.model.set_value(cdt, cdn, 'margin_amount', margin);
    frappe.model.set_value(cdt, cdn, 'margin_percentage', mp);
    calculate_service_totals(frm);
}

frappe.ui.form.on('Repair Job Service Labour', {
    billable: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.billable) {
            if (!row.billing_hours) {
                frappe.model.set_value(cdt, cdn, 'billing_hours', row.hours || 0);
            }
        } else {
            frappe.model.set_value(cdt, cdn, 'billing_hours', 0);
        }
        apply_default_labour_rate(frm, cdt, cdn);
        calculate_labour_amount(frm, cdt, cdn);
    },
    hours: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.billable) {
            frappe.model.set_value(cdt, cdn, 'billing_hours', row.hours || 0);
        }
        apply_default_labour_rate(frm, cdt, cdn);
        calculate_labour_amount(frm, cdt, cdn);
    },
    billing_hours: function(frm, cdt, cdn) {
        calculate_labour_amount(frm, cdt, cdn);
    },
    billing_rate: function(frm, cdt, cdn) {
        calculate_labour_amount(frm, cdt, cdn);
    },
    costing_rate: function(frm, cdt, cdn) {
        calculate_labour_amount(frm, cdt, cdn);
    },
});

function apply_default_labour_rate(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    if (!row.billable || row.billing_rate) return;
    if (frm._settings_loaded && frm._default_labour_rate) {
        frappe.model.set_value(cdt, cdn, 'billing_rate', frm._default_labour_rate);
        return;
    }
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Auto Service Settings',
            filters: { name: 'Auto Service Settings' },
            fieldname: ['default_labour_rate', 'default_warehouse'],
        },
        callback: function(r) {
            if (r.message) {
                if (r.message.default_labour_rate) {
                    frappe.model.set_value(cdt, cdn, 'billing_rate', r.message.default_labour_rate);
                    frm._default_labour_rate = r.message.default_labour_rate;
                }
                if (r.message.default_warehouse) {
                    frm._default_warehouse = r.message.default_warehouse;
                }
            }
            frm._settings_loaded = true;
        },
    });
}

function add_sales_invoice_button(frm) {
    frappe.db.get_value('Repair Job', frm.doc.repair_job, 'job_status').then(function(r) {
        frm.add_custom_button(__('Sales Invoice'), function() {
            frappe.model.open_mapped_doc({
                method: 'auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service.make_sales_invoice',
                frm: frm,
            });
        }, __('Create'));
    });
}

function calculate_labour_amount(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    var billing_hours = row.billing_hours || 0;
    var billing_rate = row.billing_rate || 0;
    var hours = row.hours || 0;
    var costing_rate = row.costing_rate || 0;
    frappe.model.set_value(cdt, cdn, 'billing_amount', billing_hours * billing_rate);
    frappe.model.set_value(cdt, cdn, 'costing_amount', hours * costing_rate);
    calculate_service_totals(frm);
}

function calculate_service_totals(frm) {
    var total = 0;
    var costTotal = 0;

    (frm.doc.parts || []).concat(frm.doc.consumables || []).forEach(function(row) {
        costTotal += flt(row.cost_amount);
        if (row.billable) total += flt(row.amount);
    });
    (frm.doc.labour || []).forEach(function(row) {
        costTotal += flt(row.costing_amount);
        if (row.billable) total += flt(row.billing_amount);
    });

    var grossMargin = total - costTotal;
    frm.set_value('total_amount', total);
    frm.set_value('cost_total', costTotal);
    frm.set_value('gross_margin', grossMargin);
    frm.set_value('margin_percentage', total ? grossMargin / total * 100 : 0);
}
