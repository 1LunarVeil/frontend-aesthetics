# Changelog

All notable changes to this project are recorded here. The format follows Keep a Changelog, and versions follow Semantic Versioning.

## [0.1.0] - 2026-11-01

First public release.

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
