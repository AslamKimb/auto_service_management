from auto_service_management.auto_service_management.reporting import run_report


def execute(filters=None):
	return run_report("Repair Revenue by Period", filters)
