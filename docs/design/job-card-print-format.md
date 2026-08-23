# Job Card Print Format Design Contract

Status: approved direction for implementation from Aslam's selected plan options on 2026-08-23.

## Intent and audience

The Job Card is an A4 workshop intake and work-control record used by Service Advisors, technicians, workshop managers, customers, and quality staff. It must make the customer and vehicle identity obvious at a glance, leave room for practical workshop notes, and provide a clear vehicle-condition marking area.

## Reference direction

The supplied Motorcare photographs are structural references only: dense customer and vehicle information at the top, a work-to-be-carried-out area in the middle, and a bottom band split between a vehicle diagram and acceptance terms. Do not copy Motorcare branding, legal wording, or artwork.

## Visual principles

- Clean, utilitarian, compact, and photocopy-friendly.
- Information hierarchy comes from section labels, rules, and spacing rather than decoration.
- DMS branding remains visible but never competes with customer, vehicle, or work data.
- Printed output must remain useful when handwritten with a pen.

## Color and contrast

- White page background; yellow paper remains a physical stationery choice.
- Use the existing DMS dark teal and orange accent for headings and rules.
- Use near-black text for body copy and very light fills only for section labels.
- All essential text and rules must retain strong grayscale contrast.

## Typography

- Use the existing print font stack: Inter with Arial fallback.
- Job number and document title are the strongest hierarchy.
- Section labels are uppercase, compact, and bold.
- Body text must remain legible at ordinary A4 PDF and photocopy size; no tiny disclaimer text.

## Layout and density

- A4 portrait with stable print margins and table-based structure for PDF reliability.
- Header: company identity, Job Card title, job number, and status.
- First information band: customer and vehicle details in two balanced columns.
- Middle: customer concern followed by complete service/component work instructions.
- Final page: an unbroken two-column block with the top-down vehicle diagram on the left and terms/signatures on the right.
- Long work lists may continue onto additional pages; the final block moves together to the final page.

## Shape, surface, imagery, and diagram

- Use thin rectangular rules and restrained corners; avoid heavy cards and gradients.
- The vehicle diagram uses Aslam's approved supplied vector asset `Downloads/vectorised-bb109a99.svg`, published as the versioned `vectorised-bb109a99.svg` project asset so immutable browser/Nginx caching cannot retain the superseded diagram.
- The blank diagram is always printable for handwritten marks.
- Existing Walkaround damage marks may appear as numbered markers with a compact legend.
- Do not embed the supplied photos or reproduce proprietary Motorcare artwork.

## Motion and interaction

There is no motion. Print View and generated PDF are the interaction surfaces. Links and controls are out of scope for the paper artifact.

## Responsive and print behavior

- Optimize for A4 portrait PDF and browser Print View.
- Keep tables and the final diagram/terms block together where possible.
- Do not allow customer or vehicle values to clip, overflow, or render as `None`.
- Preserve readable pagination for short, medium, and long work lists.

## Accessibility and data safety

- Use semantic headings, table headers, labels, and meaningful image alternative text.
- Escape customer-provided text and render configurable terms as plain text.
- Missing optional values render blank, not placeholder noise.
- Snapshot customer and vehicle identity at Check In for historical output; older jobs use a controlled live-data fallback.

## Required states

- Normal populated Job Card.
- Missing optional customer/contact/vehicle values.
- No linked Walkaround Inspection.
- Walkaround with one or multiple damage marks.
- Short work list with unused writing space.
- Long work list spanning pages.
- Empty configurable terms with signature lines still present.
