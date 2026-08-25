# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

from auto_service_management.auto_service_management.doctype.repair_job_service.repair_job_service import (
	RepairJobServiceComponent,
)


class RepairJobServicePart(RepairJobServiceComponent):
	component_type = "Part"

	def validate(self):
		from auto_service_management.auto_service_management.item_fitment_compatibility import (
			apply_fitment_snapshot,
		)

		apply_fitment_snapshot(self)
