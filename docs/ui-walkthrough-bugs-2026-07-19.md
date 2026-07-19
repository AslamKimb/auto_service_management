# UI Walkthrough Bug Report

**Date:** 2026-07-19
**Walkthrough script:** [role_ui_walkthrough_2026-06-30.md](role_ui_walkthrough_2026-06-30.md)
**Environment:** Docker dev stack, uto-service.localhost:8000, Administrator login

## Bugs Found

### BUG-01 — CRITICAL: Repair Job list view has no Create button

**Module:** Repair Job
**Reproduction:** Navigate to Auto Service > Repair Job list view
**Expected:** Create button visible to initiate a new Repair Job
**Actual:** No Create button. List view shows "No Data" with no creation affordance. The get_list method in epair_job.py blocks listing with "Permission required on Repair Job to list".
**Workaround:** Use the global search bar to open the Repair Job form directly.
**Impact:** Users cannot discover or create Repair Jobs from the list view, which is the primary entry point for the core workflow.

### BUG-02 — HIGH: Sales Invoice item table uses non-link Data field

**Module:** Sales Invoice (within Repair Job billing flow)
**Reproduction:** Open a Repair Job > create Sales Invoice > attempt to add line items
**Expected:** Item field should be a Link field allowing selection from existing Items in the system
**Actual:** The "Select an item" field is a plain Data (text) field, not a Link field. Users must type item names manually with no dropdown or lookup.
**Impact:** Prevents proper item selection from inventory; increases risk of typos and orphaned items.

### BUG-03 — MEDIUM: Quality Check form lacks field guidance

**Module:** Quality Check
**Reproduction:** Open a Quality Check document
**Expected:** "Check Result" and "Status" fields should have clear defaults, dropdown options, or validation hints
**Actual:** Both fields default empty with no guidance on valid values. Users must guess acceptable inputs.
**Impact:** Poor UX; risk of inconsistent data entry.

### BUG-04 — MEDIUM: Gate Pass timestamps do not auto-populate

**Module:** Gate Pass
**Reproduction:** Create or open a Gate Pass document
**Expected:** "Check In" and "Check Out" timestamps should auto-populate or have workflow buttons to trigger them
**Actual:** Both timestamp fields remain empty. Status transitions work when set manually, but there are no buttons or automation to populate them.
**Impact:** Manual timestamp entry is error-prone and defeats the purpose of a gate pass tracking system.

### BUG-05 — HIGH: Workspace sidebar links load blank pages

**Module:** Workshop Management Workspace
**Reproduction:** Click sidebar links in the Workshop Management workspace
**Expected:** Each link navigates to the corresponding list view, report, or page
**Actual:** Some sidebar links load a blank page with no error message and no content. Suggests missing or misconfigured Page/Report DocTypes behind those links.
**Impact:** Broken navigation; users cannot access certain workspace features.

## Summary

| ID | Severity | Module | Status |
|---|---|---|---|
| BUG-01 | CRITICAL | Repair Job | Open |
| BUG-02 | HIGH | Sales Invoice | Open |
| BUG-03 | MEDIUM | Quality Check | Open |
| BUG-04 | MEDIUM | Gate Pass | Open |
| BUG-05 | HIGH | Workspace | Open |

**Bugs fixed:** 0 — this walkthrough was test-and-document only.
