# Layout, density, shape and motion

## Reading order first

Before adjusting spacing, check what is seen first, second and third. Squint or blur the screenshot: the three most prominent shapes should match the job the screen exists for. If they do not, fix hierarchy before anything else.

## Grid and structure

- Web: a 12-column grid for page layout, with an 8px rhythm for vertical spacing.
- Desktop: a sidebar of about 200 to 260px, a toolbar of about 40px, a status bar of about 24px, and content panes that scroll on their own. These are starting values; set them as tokens.
- Prose inside a wide pane needs a maximum measure. Do not stretch paragraphs to the full window width.
- Break the grid on purpose, once per screen at most, and only when the break carries meaning.

## Spacing

Use a single scale, for example 4, 8, 12, 16, 24, 32, 48 and 64px. Take the smallest value that works. Group by proximity: the gap inside a group should be at most half the gap between groups. If every gap is equal, nothing is grouped.

## Density follows frequency

- Compact (desktop tables, logs, lists): rows 28 to 32px, inner padding about 8px, one line of text per row.
- Comfortable (forms, settings, inspectors): controls 32 to 40px tall, padding 12 to 16px.
- Spacious (marketing, reading, onboarding): section padding 64 to 120px.

Choose density by how often the screen is used. A screen used forty times a day should be compact. A screen used once should explain itself with more room.

## Alignment

- Left-align text by default. Center only short, one-off blocks.
- Align each region to one edge. Mixing left, centered and right in one column reads as an accident.
- Right-align numeric columns and use tabular numerals.
- Optically align icons with the text beside them. A 16px icon usually needs its box nudged to match the x-height.

## Hierarchy costs

Create hierarchy with size, weight, color and space, in that order of cheapness. Borders and boxes are the most expensive tools: they add noise to every screen they touch. Remove a border before adding a second one.

Cards are for discrete objects a person acts on, such as a model, a session or a file. Do not wrap every piece of content in a card, and never put a card inside a card. A region gets at most one divider level.

## Radius

- One small scale for the whole product, for example 0, 2, 4, 6, 8, 12, 16 and pill (999). Controls and containers differ by at most one step.
- Nested radius: inner radius = outer radius minus padding, with a floor of 0. A 12px card with 8px padding gets a 4px inner radius.
- A single radius on everything, regardless of hierarchy, is a tell (see `anti-slop.md`).

## Elevation

Three levels at most:

- 0, flat: the default for content.
- 1, raised: menus, popovers, a panel that floats over content.
- 2, overlay: dialogs and drawers, with a scrim only when the content is large.

Tint shadows to the palette: a low-alpha shadow in the accent or neutral hue, not a generic `rgba(0,0,0,.1)` under everything. Border plus shadow together belongs to overlays only.

## Breakpoints and window sizes

- Web: 360 or 390px for phones, 768px for tablets, 1024 to 1280px for desktop, and a wide layout from about 1440px.
- Desktop windows: test the app's minimum window size, 1366 by 768 and 1920 by 1080, at 100%, 125% and 150% display scaling. A layout that fits at 100% and clips at 150% is broken.

## Motion: purpose first

Animation earns its place when it does one of four jobs: shows what changed and where it came from, confirms an action, guides attention to a new element, or covers latency that cannot be removed. Anything else is decoration. Remove it.

Frequency gate: an action the user repeats many times a session (toggling, moving through a list, keyboard navigation) gets no animation, or at most 100ms. A rare, meaningful transition (opening a panel, first load, finishing a long task) may carry more.

## Durations and easing

| Use | Duration |
|---|---|
| Hover, press, toggle | 100 to 150ms |
| State change (expand, tab switch) | 150 to 250ms |
| Overlay (dialog, drawer, popover) | 200 to 300ms |
| Section or page reveal | 300 to 500ms, once per screen at most |

- Entering or responding: ease-out. Exiting: ease-in, at about 60 to 75 percent of the enter duration.
- Moving between two on-screen states: ease-in-out.
- Linear only for progress and continuous loops.

These durations are heuristics from common practice, not a standard. Keep them as tokens and tune them on the real screens.

## What to animate

- Animate transform and opacity. Avoid width, height, top, left, margin and padding, which force layout on every frame.
- For expanding content, prefer the `grid-template-rows` from `0fr` to `1fr` transition over animating `max-height`.
- Stagger siblings by 30 to 50ms, to 300 to 400ms in total, and only in one place per screen.
- Hover changes color, background or border. A lift plus a shadow on every card is a generic tell.
- An interaction in progress must be interruptible: a new click reverses or redirects the transition.

## Reduced motion and flashing

- Honour `prefers-reduced-motion: reduce`. Remove decorative transforms and parallax. Keep state changes, using an instant change or a short opacity fade.
- Progress indicators convey status, so keep them, but make them steady rather than pulsing.
- Never flash content more than three times per second (WCAG 2.3.1). Prefer no blinking indicators at all.
- Live data updates change content, not motion.

```css
:root {
  --dur-micro: 120ms;
  --dur-state: 180ms;
  --dur-overlay: 240ms;
  --ease-out: cubic-bezier(0.2, 0, 0, 1);
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
}

@media (prefers-reduced-motion: reduce) {
  :root {
    --dur-micro: 0ms;
    --dur-state: 0ms;
    --dur-overlay: 0ms;
  }
  .panel-enter { transform: none; }
}
```

## Loading feedback

- Skeletons for shapes the layout already knows, such as a table with its header.
- A spinner with a label when the duration is unknown.
- Delay the indicator 200 to 300ms, so fast responses do not flicker.
- Progress bars show a number when the total is known.
- Never leave a blank panel.
