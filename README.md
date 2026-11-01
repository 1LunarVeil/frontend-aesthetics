# Frontend Aesthetics

An agent skill for making visual decisions that are specific to a product, and for checking them with something other than an opinion. It is built to run alongside the official `frontend-design` skill: that skill sets the stance, and this one supplies the decision rules, the precedent data and the checks.

Works in Claude Code, ZCode, Cursor, OpenAI Codex, VS Code Copilot and any agent that reads the Agent Skills format (`<skill-name>/SKILL.md`). It needs Python 3.9 or newer; the scripts use only the standard library and never touch the network.

## Why

Generated UI usually fails in one of two ways: it looks like the average of every page the model has seen, or it breaks a floor nobody checked. This skill addresses both.

- It makes the model write a brief before choosing colors, fonts and layout, and name the reason for each default it keeps.
- It ships nine complete directions with starting palettes whose contrast values were computed, not guessed.
- It ships three small programs: one to check contrast, one to look up product-type precedents, one to scan source code for generic tells and craft defects.

It does not replace `frontend-design`. Install both.

## Install

### Any agent that supports Agent Skills

Copy the skill folder so that `SKILL.md` sits directly inside a folder named after the skill:

```
git clone https://github.com/<owner>/frontend-aesthetics
cp -r frontend-aesthetics/skills/frontend-aesthetics ~/.claude/skills/
```

| Agent | Project scope | User scope |
|---|---|---|
| Claude Code | `.claude/skills/frontend-aesthetics/` | `~/.claude/skills/frontend-aesthetics/` |
| Cursor | `.cursor/skills/frontend-aesthetics/` or `.agents/skills/...` | `~/.cursor/skills/...` or `~/.agents/skills/...` |
| OpenAI Codex | `.codex/skills/frontend-aesthetics/` | `~/.codex/skills/frontend-aesthetics/` |
| VS Code Copilot | `.github/skills/frontend-aesthetics/` | `~/.copilot/skills/frontend-aesthetics/` |

The folder name must match the `name` in the frontmatter. The most common install failure is one extra directory level, so that `SKILL.md` ends up nested one level too deep.

Agents that share folders also see each other's installs: Claude Code and Copilot both read `.claude/skills/`, and Cursor, Copilot and Codex can read `.agents/skills/`. Installing once into `~/.agents/skills/` therefore covers several agents on the same machine.

With the `skills` CLI, install from this repository instead of copying:

```
npx skills add <owner>/frontend-aesthetics --skill frontend-aesthetics
```

### Claude Code plugin

```
/plugin marketplace add <owner>/frontend-aesthetics
/plugin install frontend-aesthetics@frontend-aesthetics
```

This also installs the two slash commands. Restart the session after installing.

### ZCode plugin

In Plugin Marketplace, add this repository's directory, or the local path to a clone, as a marketplace source, then install **Frontend Aesthetics**. The manifest is in `.zcode-plugin/plugin.json`.

### No install: paste and go

If you only need the rules for one task, give the agent `skills/frontend-aesthetics/SKILL.md` plus the reference file the task needs. The scripts are optional but recommended.

## Use

The skill activates from its description when you ask for UI work, or you can name it. Typical prompts:

- "Build the settings page. First write the brief and three things this must not look like, then give two directions, pick one, and show the token block."
- "Review this UI: find the generic tells and the accessibility floors it breaks."
- "The current UI looks bland. Restyle it without breaking the token contract."

With commands available:

- `/design-direction saas dashboard for a local model launcher, dark first`
- `/design-review src/pages/settings`

Expected shape of a response: a short brief, a direction with a reason, a token block, and a verification section listing the commands run and their results.

## Tools

Run from the repository root:

```
python skills/frontend-aesthetics/scripts/wcag.py "#1f2937" "#ffffff" "#556070" "#f6f7f9"
python skills/frontend-aesthetics/scripts/design_lookup.py "saas dashboard" --ux --motion
python skills/frontend-aesthetics/scripts/slop_scan.py path/to/frontend/src
```

If you installed the skill into an agent, run the same scripts from the installed skill folder, for example `~/.claude/skills/frontend-aesthetics/scripts/`.

- `wcag.py FG BG ...` prints the contrast ratio for each pair, with verdicts for AA text (4.5:1), large text and UI (3:1) and AAA text (7:1). It accepts `#hex`, `rgb()` and `oklch()`. Out-of-gamut OKLCH values are clipped to sRGB, the same way a browser clips them.
- `design_lookup.py "<English keywords>"` returns matching product types, styles, a contrast-checked palette, type pairings and reasoning rules from the vendored data. Use `--ux`, `--motion` and `--charts` for extra sections.
- `slop_scan.py PATH ...` reports generic tells and craft defects as `blocking`, `important`, `review` or `polish`. It exits with status 1 when a blocking finding exists, so it can gate CI. Use `--json` for machine output.

On Windows, use `py -3` if `python` is not on PATH.

## What is inside

```
skills/frontend-aesthetics/
  SKILL.md                  workflow, floors, taste rules, the choice test
  references/
    principles.md           decision order and the brief template
    directions.md           nine directions with verified starting tokens
    color-and-type.md       palettes, dark theme, contrast, scales, fonts, CJK
    layout-and-motion.md    spacing, density, radii, elevation, motion
    components-and-states.md  state matrix, copy rules, the break test
    desktop-app.md          WebView and desktop app rules
    anti-slop.md            tells, why they read as defaults, questions to ask
    critique.md             review procedure, nine pillars, severity, output
    sources.md              where each rule came from, and what was rejected
  scripts/                  wcag.py, design_lookup.py, slop_scan.py
  data/                     eight MIT-licensed CSV files from ui-ux-pro-max
commands/                   optional slash commands
tests/                      standard-library unit tests and fixtures
```

## Verification

```
python -B -m unittest discover -s tests -v
```

The tests cover the contrast math against published reference values, OKLCH agreement with sRGB, name-weighted product matching, and every scanner rule against a fixture that contains each defect. No tests need a network connection or a browser.

## Known limitations

- The scanner finds patterns. It cannot judge taste, and each finding needs a human decision. For example, `outline: none` only matters when nothing replaces the focus style.
- The palettes are starting points. Measured across all 192 rows, only one has a failing text pair, but 173 have a border below 3:1 and 30 have a primary fill below 3:1 against their background. Check the UI pairs before shipping.
- Visual review needs a browser tool. Without one, the review is code-only, and the skill says so instead of guessing.
- Thresholds for durations, density and breakpoints are heuristics from practice, not standards. WCAG items are marked as such in `references/sources.md`.

## Compatibility notes

- `SKILL.md` has a `description` in its frontmatter, because agents choose skills by it. Some early design skills shipped without one and were never selected automatically.
- The scripts are Python 3.9 or newer, standard library only, and print UTF-8 on all platforms.
- Nothing writes to disk, and nothing calls the network, so the tools are safe to run in a review of an untrusted repository.

## License

MIT for the plugin's code and documentation, see `LICENSE`. The CSV data is MIT-licensed by Next Level Builder; see `THIRD_PARTY_NOTICES.md`.
