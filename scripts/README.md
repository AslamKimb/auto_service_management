# Maintainer scripts

This directory contains reusable, reviewable maintenance tooling for the DMS
repository. Scripts that inspect or change a live Frappe site must document
their site/permission assumptions and be invoked explicitly with a named site.

Current supported utility:

- `validate_fitment_import.py` — validates the fitment import payload before it
  is loaded into a site.

One-off SQL snippets, exploratory patches, browser captures, credentials, and
generated diagnostics are not repository tooling. Keep those outside the
checkout so they cannot be mistaken for supported deployment or migration
steps.
