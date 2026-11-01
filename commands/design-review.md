---
description: Review a UI for visual quality, accessibility and generic-default tells (read-only)
argument-hint: "<path, directory, URL or screenshot>"
---

Review this UI with the frontend-aesthetics critique procedure: $ARGUMENTS

1. Read the skill's `references/critique.md` and follow its steps in order.
2. Run the skill's `scripts/slop_scan.py` over the UI source paths. Run its `scripts/wcag.py` on the text and UI pairs in the token file.
3. If a browser tool is available, capture the main screens at desktop and narrow sizes, and list the states you captured. If not, say the review is code-only and make no claims about rendering.
4. Report findings grouped as blocking, important and polish. Each finding gives its location, its evidence and its fix. Then give the three changes that would move the design most, and what was not checked.
5. Do not edit files. Offer to apply the fixes and wait for the answer.
