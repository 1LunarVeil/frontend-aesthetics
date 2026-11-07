# Anti-slop: tells, reasons and questions

A "tell" is a choice that shows up on almost every generated interface because nobody made it for the brief. This list is not a ban list. A flagged default is fine once it has been chosen, and the question in each row is how to make that choice.

The rule ID column matches `scripts/slop_scan.py`. Rows without a rule ID are judgement calls the scanner cannot see. Severities follow the floors: only accessibility-floor violations are blocking, craft defects are important, taste tells are review — a decision, not a defect.

| Tell | Why it reads as a default | Ask instead | Rule |
|---|---|---|---|
| Inter, Roboto, Arial or Open Sans as the main face | the statistically safest choice | Which face says something about this subject? Would a system stack do the job? | TYPE-DEFAULT-PRIMARY |
| Purple-to-blue gradient accent | the most common generated accent | What hue comes from the subject's own world? One flat accent may be enough. | COLOR-PURPLE-GRADIENT |
| Warm cream background with a terracotta accent | a widely copied "warm" recipe | What does warmth mean here: paper, wood, or nothing at all? | |
| Near-black with one acid-green or vermilion accent | a widely copied "edgy" recipe | Does the product need night use or glare control? | |
| Hero, three feature cards, call to action | a template, not a structure | What must the first screen do, in one sentence? | |
| Equal cards in a grid, one radius, one shadow | no hierarchy is encoded | Which item matters most? Make it larger, or drop the card. | |
| The same soft grey shadow under every card | the default elevation | How many elevation levels does this product need? | COLOR-GREY-SHADOW |
| Fade and slide up on every section | a generic entrance | Which single moment should happen on load? | MOTION-GENERIC-ENTRANCE |
| `transition: all` | every property animates, often by accident | Which properties actually change? | MOTION-ALL |
| All-caps eyebrow label above every heading | template chrome | Does the label tell the reader anything the heading does not? | TYPE-CAPS |
| Middle-dot metadata, "A · B · C" | template chrome | Are all those fields needed? Give each a label. | COPY-MIDDOT-META |
| "WORD — fragment" labels with a spaced em dash | template chrome | Is this a name or a sentence? Write it as one of the two. | |
| An arrow after every button or link | template chrome | Does the control need an arrow, or a plain verb? | COPY-ARROW-CTA |
| "Submit", "Oops", "Something went wrong" | says nothing about the result | Name the action. Say what happened and what to do. | COPY-SUBMIT, COPY-GENERIC-ERROR |
| 01, 02, 03 markers on content with no sequence | structure without a sequence | Is there really an order? | |
| One headline word in italic or another color | emphasis for its own sake | Which single element deserves the emphasis? | |
| Monospace for every small label | a technical flavour by default | Is this value code-like? Then mono; if not, sans. | |
| Emoji as icons | inconsistent, unlabeled, platform-dependent | One icon family, labelled controls | EMOJI-ICON |
| Text under 12px, gray on gray | low-effort contrast | Run `wcag.py` on the pair. | TYPE-TINY |
| Raw hex, px or rgba values inside components | bypasses the tokens | Move the value into the token file. | RAW-LEAK (token_lint) |
| Lorem ipsum or invented metrics | placeholder left in | Use real data, or sample data that is labelled as sample. | COPY-LOREM |
| Pure `#000` surfaces | a harsh default | A tinted near-black, unless the brief is brutalist. | COLOR-PURE-BLACK |
| One duration for every transition | no motion decisions were made | Set a tier for each interaction. | MOTION-UNIFORM |
| Lift and shadow on every hover | a generic interaction | Change color or border only. | HOVER-LIFT |
| Glassmorphism, neon glow or bento grids for any product | trend picks | Does the trend help the job, or only the picture? | |
| Layout-property transitions | jank and surprise | Animate transform or opacity. | MOTION-LAYOUT |

## Structural tells the scanner cannot see

- The same section rhythm on every page: hero, features, testimonial, call to action. Vary the structure per page, so two briefs never share a template.
- Stat rows built from a large number, a small label and a gradient accent, used as the default treatment.
- Everything centred and symmetric, with equal padding everywhere.
- Copy that could belong to any product.

## Two tests

- Self-similarity test: strip the product nouns from the screen. If the layout, palette and type still read the same, the design is a template.
- Refusal test: check the three refusals from the brief. Each one should be visibly avoided.

## Recipes become defaults

A recipe copied from a reference becomes the next default. Keep the reasons a reference gives, such as "a dense table needs tabular numerals", and adapt its values to this brief.
