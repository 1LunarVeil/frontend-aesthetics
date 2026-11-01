# Changelog

All notable changes to this project are recorded here. The format follows Keep a Changelog, and versions follow Semantic Versioning.

## [0.1.1] - 2026-11-01

This is a correction to the 0.1.0 release, not a feature jump. It closes a gap the first release documented instead of implementing, and it makes the plugin's limits and lineage explicit before public release.

### Fixed

- **The visual loop existed in the sources and not in the plugin.** 0.1.0 read Anthropic's `frontend-design` ("taking screenshots to review"), claude-dev-kit's capture scripts and pixel-diff threshold, and several AI UX Playground skills that verify in a headless browser, then wrote the loop as an optional aside — "screenshots when a browser tool is available". That gave a model a legitimate reason to skip visual review. The loop is now a required step with a tool that runs it.

### Added

- `scripts/visual_capture.py`: headless capture with a Chromium-family browser found by absolute path only. Shoots repeatedly until two consecutive frames are identical, so a half-rendered shell is not mistaken for a design; reports colour counts, attempt counts, console errors and blank frames as JSON.
- `scripts/image_diff.py`: PNG decoding and pixel comparison with the standard library only, giving changed pixels, ratio and a bounding box. Decodes non-interlaced 8-bit PNG and reports anything else as unsupported instead of comparing it wrongly.
- `references/visual-review.md`: the render, look, change, look-again procedure, including the measured reasons behind the tool's design.

### Changed

- `SKILL.md` verification step now starts with rendering and looking, and requires re-capture plus diff after a change. A review with no capture must say "not visually verified".
- `critique.md` replaced the conditional screenshot step with a mandatory capture step, and added a "close the loop" section after applying fixes.
- `/design-review` now captures first and reports a Visual section in the findings.
- The README states what the plugin is for, what it can do, and what it explicitly cannot do; before, "cannot" was scattered across limitations.

### Documented

- `references/sources.md` now names, per source, where the visual loop came from and that 0.1.0 dropped it. It also adds "What this plugin does and does not do" and a "Lineage and honesty" section.
- README credits section lists every source used and links to the per-item record.

### Known limitations

- Capture reaches landed states only. Hover, focus rings, open menus and mid-transition frames need a driving browser tool.
- `image_diff.py` is not a regression gate: a deliberate redesign may change every pixel.
- No browser installed means no visual step; the review must then say so.
- The plugin has not been benchmarked against `frontend-design` alone. Its verifiable claims are tested; "does it look better" is not.

## [0.1.0] - 2026-11-01

First release.

### Added

- `frontend-aesthetics` skill: an eight-step workflow (read the project's rules, brief, precedents, direction, tokens, build, verify, report) with hard accessibility floors and a test for whether each default was chosen.
- Nine reference documents: principles and the brief template, nine directions with contrast-verified starting palettes, color and type, layout and motion, components and states, desktop app rules, the anti-slop catalogue, the critique procedure, and sources.
- `scripts/wcag.py`: WCAG contrast calculation for `#hex`, `rgb()` and `oklch()`, with reference values in the tests.
- `scripts/design_lookup.py`: product-type precedents from vendored data, with name-weighted matching and per-palette contrast checks that separate text failures from UI failures.
- `scripts/slop_scan.py`: read-only scan for generic-default tells and craft defects, with blocking, important, review and polish severities and a non-zero exit status when a blocking finding exists.
- `commands/design-direction.md` and `commands/design-review.md` for agents that support slash commands.
- Manifests for Claude Code (`.claude-plugin/`) and ZCode (`.zcode-plugin/`), plus plain `skills/` layout for Cursor, Codex, Copilot and any agent that reads Agent Skills.
- Eight MIT-licensed CSV data files from ui-ux-pro-max, with provenance and a list of data caveats.
- Unit tests using only the standard library, and a GitHub Actions workflow that runs them.

### Known limitations

- The scanner finds patterns, not taste. Every finding needs a human judgement.
- Palettes in the data are starting points: 173 of 192 rows have a border below 3:1, and 30 have a primary fill below 3:1, so UI pairs must be checked before use.
- Reference screenshots are not included. Visual review needed a browser tool; the skill described it as optional.

### Added

- `frontend-aesthetics` skill: an eight-step workflow (read the project's rules, brief, precedents, direction, tokens, build, verify, report) with hard accessibility floors and a test for whether each default was chosen.
- Nine reference documents: principles and the brief template, nine directions with contrast-verified starting palettes, color and type, layout and motion, components and states, desktop app rules, the anti-slop catalogue, the critique procedure, and sources.
- `scripts/wcag.py`: WCAG contrast calculation for `#hex`, `rgb()` and `oklch()`, with reference values in the tests.
- `scripts/design_lookup.py`: product-type precedents from vendored data, with name-weighted matching and per-palette contrast checks that separate text failures from UI failures.
- `scripts/slop_scan.py`: read-only scan for generic-default tells and craft defects, with blocking, important, review and polish severities and a non-zero exit status when a blocking finding exists.
- `commands/design-direction.md` and `commands/design-review.md` for agents that support slash commands.
- Manifests for Claude Code (`.claude-plugin/`) and ZCode (`.zcode-plugin/`), plus plain `skills/` layout for Cursor, Codex, Copilot and any agent that reads Agent Skills.
- Eight MIT-licensed CSV data files from ui-ux-pro-max, with provenance and a list of data caveats.
- Unit tests using only the standard library, and a GitHub Actions workflow that runs them.

### Known limitations

- The scanner finds patterns, not taste. Every finding needs a human judgement.
- Palettes in the data are starting points: 173 of 192 rows have a border below 3:1, and 30 have a primary fill below 3:1, so UI pairs must be checked before use.
- Reference screenshots are not included. Visual review needs a browser tool; without one the review is code-only.
