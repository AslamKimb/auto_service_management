"""Backfill one immutable initial customer interval for existing vehicles."""

import frappe


def execute():
	from auto_service_management.auto_service_management.doctype.customer_vehicle_customer_association.customer_vehicle_customer_association import (
		create_initial_association,
	)

	for vehicle in frappe.get_all("Customer Vehicle", fields=["name", "customer"], limit_page_length=0):
		if vehicle.customer:
			create_initial_association(vehicle.name, vehicle.customer, source_name=vehicle.name)
