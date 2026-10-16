# Greybox preview

A greybox shows structure only, so the user can confirm layout before real implementation.

- One self-contained HTML file per blueprint (pages as sections or a simple page switcher). No external dependencies, no build step.
- Neutral greys, system font, 1px borders. No brand color, imagery, shadows, or animation.
- Every node renders as a labeled box: `Type#id` in small monospace at the top-left, followed by its text or a short props summary. Layout primitives render with their real flow (`Stack` vertical, `Row` horizontal, `Grid` columns, `Split` side panel) so proportions are roughly right.
- Expand pattern pages with their documented defaults and `Changes` before rendering; label the page section with its pattern name.
- Data components show two or three placeholder rows using the declared columns or fields.
- One section per `page.md`, titled with its route; layouts wrap their pages once at the top rather than repeating per section.
- Overlays render as separate boxes below the page under an "Overlays" heading, labeled with type, placement, and `onClose` outcomes, not as working modals.
- `navigate(...)` actions become in-file links between route sections; `open(#...)` links jump to the overlay box; other actions appear as text.
- Responsive rules may be shown with a width toggle (e.g. 1280 / 768 / 375). Skip this unless the blueprint defines responsive overrides.
- Mark nodes flagged `# assumed` with a dashed border.

Write the file next to the blueprint (for example `blueprint/preview.html`) or to the location the user specifies. It is disposable; regenerate it from the blueprint rather than editing it by hand.
