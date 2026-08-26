# Copyright (c) 2026, Aslam Kimbugwe and contributors
# For license information, please see license.txt

"""Explicit cache boundary for stable Auto Service Management settings reads."""

import frappe

SETTINGS_DOCTYPE = "Auto Service Settings"


def get_settings(*, frappe_module=frappe):
	"""Return the cached Auto Service Settings document.

	Only this stable configuration document is cached here. Transactional job,
	stock, billing, and payment reads must continue to use their live query paths.
	"""
	# Keeping the Frappe dependency injectable preserves lightweight adapter
	# tests, while production always uses the real v16 document cache.
	if getattr(frappe_module, "__name__", None) != "frappe":
		return frappe_module.get_single(SETTINGS_DOCTYPE)
	return frappe_module.get_cached_doc(SETTINGS_DOCTYPE)


def clear_settings_cache(*, frappe_module=frappe):
	"""Invalidate the settings document cache after a settings mutation."""
	frappe_module.clear_document_cache(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE)
