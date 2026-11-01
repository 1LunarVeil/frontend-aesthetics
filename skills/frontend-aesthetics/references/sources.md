# Sources

Each rule in this skill was either checked against a standard, measured with the scripts, or taken from one of the sources below and rewritten. Nothing here is copied verbatim except the vendored data in `data/`, which keeps its MIT license.

## Standards

- WCAG 2.2 (W3C): the contrast minimums (1.4.3, 1.4.11), text resize and reflow (1.4.4, 1.4.10), text spacing (1.4.12), focus visibility and appearance (2.4.7, 2.4.11), target size (2.5.8), flashing (2.3.1), animation from interactions (2.3.3). The large-text definition (18pt, or 14pt bold) is from the same document.
- Color-vision safe palette: the Okabe-Ito set, from Okabe and Ito's color universal design guidance.

## Resources reviewed for this plugin

1. frontend-design, Anthropic (the official Claude Code design skill, version 1.1.1 at the time of writing). Used for the stance: commit to a direction, avoid the defaults nobody chose, plan then review then build then critique, and the AI-cluster list of defaults. Its text is not copied. Its terms are in its own LICENSE.txt.

2. ui-ux-pro-max-skill, Next Level Builder, MIT, copyright 2024 Next Level Builder. Repository: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill (HEAD bf41cbc when cloned for this plugin). Used:
   - Eight CSV data files, vendored unchanged into `data/` with the MIT notice (see `data/PROVENANCE.md`).
   - The idea of joining product types to styles, palettes and reasoning rules.
   Not used: the Python engine (we wrote a smaller lookup that adds name-weighted matching and contrast checks), the landing, app-interface, react-performance, icon and Google Fonts data, and the CLI.

3. claude-dev-kit, pillip, MIT, copyright 2025 pillip. Repository: https://github.com/pillip/claude-dev-kit. Used as a source for the critique pillars and state coverage, and for desktop items: shortcut hints with the platform modifier, focus restoration after dialogs, density judged by visible rows, and the keyboard path for resizers. Its numeric claims were checked and rewritten. Two conflicts were resolved in favour of the WCAG values: iOS target size (44pt in one file, 48pt in another) and the placeholder contrast (3:1 in one file, 4.5:1 for text in another). Its orchestration and workflow content is not relevant here and was not used.

4. buildwithclaude, davepoon, MIT, copyright 2025 davepoon. Repository: https://github.com/davepoon/buildwithclaude. Reviewed and rated low for this purpose: several contrast examples were wrong, its guidance was WCAG 2.1 only, and its font advice contradicts itself. Used only for the idea that a recipe copied from a reference becomes the next default. No text was taken.

5. "4 design skills that improved my UIs", Aridan Martin, https://aridanemartin.dev/blog/design-skills-for-developers/. Used for the framing that AI-generated UI suffers from a taste problem, for the principles of one dominant color with a sharp accent, typography carrying most of the personality, one orchestrated animation over scattered ones, and spatial surprise used sparingly, and for the practice of reading a brief document before generating. The post recommends using design skills for reviews as well as generation, and this skill does both. Impeccable's rule set is mentioned in that post, but its rules were not used; the scanner rules here were written independently.

6. "Agent Skills for Designers", AI UX Playground, https://aiuxplayground.com/skills/for-designers. A catalogue of designer-oriented skills. Used as a checklist of workflow ideas rather than content: expanding a happy path into loading, empty, error, disabled, focus, partial and recovery states; testing with worst-case data; checking spacing against a 4 and 8 grid; building palettes in OKLCH with semantic tokens; a motion frequency gate; blocking, important and polish severities; and a DESIGN.md-style brief. The catalogue's own skill descriptions were not reproduced.

7. "Make Interfaces Beautiful with LLMs and Skills", Learning AI (aiecos), https://learning.aiecos.ai/en/stage-2/frontend/llm-skills-beautiful/. Used for the five-dimension vocabulary (typography, color, layout, motion, details) in the brief, and for the principle that a named aesthetic direction beats a generic prompt. Caveats: several example templates in the chapter (Inter for body text, grey shadows, a glassmorphism recipe) are the defaults this skill warns against, so none was adopted. The URL ending in `/plugin-creator` returns 404 on the English site; the skill-creation material is in the chapter's section 6, "Create your own design system skill".

## Deliberately not used

- Icon, font-catalogue and CDN metadata, and any stack-specific code (React, Next.js, Tailwind, Figma plugin APIs). They do not match a vanilla or desktop WebView UI.
- Brand assets and brand guidelines. Any brand's logo, illustrations or proprietary typeface.
- Numeric claims that could not be verified (for example, counts of styles or palettes on marketing pages).

## Verification

- Contrast values in `directions.md` were computed with `scripts/wcag.py`, which was checked against reference values: black on white 21.00:1, #767676 on white 4.54:1, #777777 on white 4.48:1, and pure red on white 4.00:1.
- Scanner rules were checked against `tests/fixtures/` and against a real frontend, where they produced the findings they describe.
