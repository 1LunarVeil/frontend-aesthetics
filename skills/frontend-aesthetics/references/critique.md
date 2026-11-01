# Critique procedure

Use this when someone asks for a review, and as the last check before reporting a visual change. A review is read-only: report findings and offer fixes, and edit files only when asked.

## 1. Scope and brief

State the target: a file, a directory, a URL or screenshots. Read the project's brief or contract if one exists. If none exists, write three lines of brief from the product and the screen, and say they are assumptions.

## 2. Capture

- If a browser tool is available (for example Playwright MCP or the browser-use plugin), capture the main screens at the app's default window size and at a narrow size (800 by 600 for desktop, 390 by 844 for web). Capture the dark theme too when the app has one. List the states you captured: default, empty, error, loading.
- If no browser tool is available, say that the review is code-only, and make no claims about rendering, spacing as seen, or colour as seen.

## 3. Mechanical checks

- `python scripts/slop_scan.py <paths>` over the UI source. Exit status 1 means blocking findings exist.
- `python scripts/wcag.py FG BG ...` for each text and UI pair in the token file.
- The break test from `components-and-states.md`, run against the code paths for long or empty data, or in the browser with real data.

The scanner finds patterns. Each hit still needs a judgement: `outline: none` is a problem only when no focus style replaces it, and an all-caps label can be right.

## 4. Pillar review

Check each pillar. Skip none, but write "no issues" where that is true.

1. Direction: one idea is visible; the screen could not be mistaken for a different product; one signature element appears once; the three refusals are honoured.
2. Hierarchy: the first three things seen match the job; one primary action per region; grouping by proximity holds.
3. Color: roles follow the token set; the accent covers about 10% or less; semantic colors match across screens; the dark theme is a ladder, not an inversion; no meaning is carried by color alone.
4. Typography: at most two families plus a mono face; one scale ratio; prose measure 45 to 75 characters; tabular numerals in numeric columns; no text under 12px; no all-caps except short labels.
5. Space and density: spacing from one scale; density fits how often the screen is used; no equal gaps everywhere; no card inside a card.
6. Shape and detail: radii from one scale and nested correctly; at most three elevation levels, tinted; one icon family, optically aligned beside text; no doubled borders.
7. Motion: each animation has a purpose from `layout-and-motion.md`; durations sit in their tiers; only transform and opacity animate; reduced motion is handled; nothing flashes.
8. States and copy: every state from the matrix exists; the break test passes; errors say what happened and what to do; action names match their results; no placeholder or invented data.
9. Accessibility floor: text and UI contrast; visible focus; labelled controls; keyboard order; target sizes; the layout survives 200% zoom (WCAG 1.4.4) and 320 CSS pixels of width (1.4.10); text spacing does not clip (1.4.12).

## 5. Severity

- Blocking: fails a floor. Contrast below the minimum, no visible focus, unlabelled controls, clipping with realistic data, lost user input, or a state that hides an error.
- Important: a visible inconsistency, a generic default in a prominent place, a missing state, or a motion problem that distracts.
- Polish: refinement that improves the screen but does not fix a defect.

## 6. Output format

Group findings by severity. Each finding is one line:

```
Blocking
- [Accessibility floor] settings.css:211 - focus outline removed on .toggle with no replacement; add a 2px focus ring at 3:1 against the surface.

Important
- [Typography] panel.css:88 - 11px labels in a data table; raise to 12px minimum and check the row height still fits.

Polish
- [Shape] cards.css:40 - four different radii on sibling cards; use the nearest step from the scale.
```

After the list, give:

- Top three changes, ordered by how much they would move the design.
- What was not checked, and why (for example, no browser available, or no dark-theme capture).

Do not list praise. Do not list more than about 30 findings; if there are more, say so and group them by file.

## 7. Before reporting

Read the findings once more against the nine pillars. Remove any finding you cannot support with a location and evidence. Keep blocking findings; they are not optional.
