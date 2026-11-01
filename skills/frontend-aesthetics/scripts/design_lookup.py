"""Product-type precedents for a UI brief, from the vendored ui-ux-pro-max data.

Usage: python design_lookup.py "saas dashboard dark" [--top N] [--ux] [--motion] [--charts]

Use English keywords. The output is evidence to weigh, not a finished design:
every palette is contrast-checked here, and the final palette still needs
checking with wcag.py.
"""

import argparse
import csv
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep the plugin tree free of __pycache__
import wcag  # noqa: E402  (sibling module in this scripts/ directory)

DATA = Path(__file__).resolve().parent.parent / "data"
STOPWORDS = {
    "a", "an", "and", "the", "for", "of", "with", "to", "in", "on", "by",
    "my", "our", "your", "design", "ui", "interface",
}

# (foreground column, background column, kind, required ratio)
PAIRS = [
    ("Foreground", "Background", "text", wcag.AA_TEXT),
    ("Card Foreground", "Card", "text", wcag.AA_TEXT),
    ("On Primary", "Primary", "text", wcag.AA_TEXT),
    ("On Accent", "Accent", "text", wcag.AA_TEXT),
    ("On Destructive", "Destructive", "text", wcag.AA_TEXT),
    ("Muted Foreground", "Background", "text", wcag.AA_TEXT),
    ("Muted Foreground", "Muted", "text", wcag.AA_TEXT),
    ("Primary", "Background", "UI", wcag.AA_LARGE_OR_UI),
    ("Ring", "Background", "UI", wcag.AA_LARGE_OR_UI),
    ("Border", "Background", "UI", wcag.AA_LARGE_OR_UI),
]
PALETTE_FIELDS = [
    "Primary", "Secondary", "Accent", "Background", "Card", "Foreground",
    "Muted", "Muted Foreground", "Border", "Ring", "Destructive",
]


def _tokens(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    result = set()
    for word in words:
        if word in STOPWORDS:
            continue
        result.add(word[:-1] if len(word) > 4 and word.endswith("s") else word)
    return result


def _load(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as handle:
        return [
            {key.strip(): (value or "").strip() for key, value in row.items() if key}
            for row in csv.DictReader(handle)
        ]


def _trim(text, limit=260):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _split_styles(text):
    parts = re.split(r"[+,]", text)
    return [part.strip() for part in parts if part.strip()]


def _find_style(styles, name):
    exact = [row for row in styles if row["Style Category"].lower() == name.lower()]
    if exact:
        return exact[0], name
    scored = [(len(_tokens(name) & _tokens(row["Style Category"])), row) for row in styles]
    scored = [item for item in scored if item[0] > 0]
    if not scored:
        return None, None
    best = max(scored, key=lambda item: item[0])[1]
    return best, best["Style Category"]


def _print_styles(product, styles):
    print("## Style")
    style_rows = []
    for name in _split_styles(product["Primary Style Recommendation"]) + _split_styles(
        product["Secondary Styles"]
    ):
        row, matched = _find_style(styles, name)
        if row is None or any(row is seen for seen in style_rows):
            print(f"- {name}: no row in styles.csv")
            continue
        style_rows.append(row)
        note = "" if matched.lower() == name.lower() else f" (closest row: {matched})"
        status = " [deprecated in data]" if row["Status"] == "deprecated" else ""
        print(f"- {row['Style Category']}{note}{status}")
        print(f"    keywords: {_trim(row['Keywords'], 180)}")
        print(f"    best for: {_trim(row['Best For'], 180)}")
        print(f"    avoid for: {_trim(row['Do Not Use For'], 180)}")
        print(f"    light/dark: {row['Light Mode ✓'] or '-'} / {row['Dark Mode ✓'] or '-'}"
              f"  complexity: {row['Complexity'] or '-'}")
        print(f"    effects: {_trim(row['Effects & Animation'], 160)}")
    print()
    return style_rows


def _print_palette(product_type, colors):
    print("## Palette (contrast checked, sRGB)")
    row = next((item for item in colors if item["Product Type"].lower() == product_type.lower()), None)
    if row is None:
        print("- no palette row for this product type\n")
        return
    for field in PALETTE_FIELDS:
        print(f"- {field}: {row.get(field) or '-'}")
    tally = {"text": [0, 0], "UI": [0, 0]}  # kind -> [failing, checked]
    for fg_field, bg_field, kind, required in PAIRS:
        fg, bg = row.get(fg_field, ""), row.get(bg_field, "")
        try:
            ratio = wcag.contrast_ratio(fg, bg)
        except ValueError:
            print(f"  skipped {fg_field} on {bg_field}: not a hex/rgb/oklch value")
            continue
        verdict = "PASS" if ratio >= required else "FAIL"
        tally[kind][0] += verdict == "FAIL"
        tally[kind][1] += 1
        label = f"{fg_field} on {bg_field}"
        if fg_field == "Border":
            label += " (needed only as the sole edge of a control)"
        print(f"  {verdict} {kind:<4} {label}: {ratio:.2f}:1 (need {required:g})")
    text_failing, text_checked = tally["text"]
    ui_failing, ui_checked = tally["UI"]
    print(f"  text pairs failing: {text_failing} of {text_checked}; "
          f"UI pairs failing: {ui_failing} of {ui_checked}.")
    if text_failing:
        print("  Fix the text pairs before using this palette.")
    if row.get("Notes"):
        print(f"- notes: {_trim(row['Notes'], 200)}")
    print()


def _print_typography(query, style_rows, typography):
    print("## Typography pairings")
    keywords = set(query)
    for row in style_rows[:1]:
        keywords |= _tokens(row["Keywords"])
    scored = []
    for row in typography:
        overlap = len(keywords & _tokens(
            row["Font Pairing Name"] + " " + row["Mood/Style Keywords"] + " " + row["Best For"]
        ))
        if overlap:
            scored.append((overlap, row))
    scored.sort(key=lambda item: -item[0])
    if not scored:
        print("- no pairing matched; choose from references/color-and-type.md\n")
        return
    for _, row in scored[:3]:
        print(f"- {row['Font Pairing Name']}: heading {row['Heading Font']} / body {row['Body Font']}")
        print(f"    mood: {_trim(row['Mood/Style Keywords'], 140)}")
    print("  Google Fonts URLs in the data are for reference: self-host or use system fonts.\n")


def _print_reasoning(product_type, reasoning):
    print("## Reasoning rules")
    row = next((item for item in reasoning if item["UI_Category"].lower() == product_type.lower()), None)
    if row is None:
        print("- no reasoning row for this product type\n")
        return
    for field in [
        "Recommended_Pattern", "Style_Priority", "Color_Mood", "Typography_Mood",
        "Key_Effects", "Decision_Rules", "Anti_Patterns", "Severity",
    ]:
        if row.get(field):
            print(f"- {field.replace('_', ' ').lower()}: {_trim(row[field], 300)}")
    print()


def _print_ux(query, limit=6):
    print("## UX guideline matches (web and all-platform rows)")
    rows = [row for row in _load("ux-guidelines.csv") if row["Platform"] in ("All", "Web")]
    scored = []
    for row in rows:
        overlap = len(query & _tokens(row["Category"] + " " + row["Issue"] + " " + row["Description"]))
        if overlap:
            scored.append((overlap, row))
    scored.sort(key=lambda item: -item[0])
    if not scored:
        print("- no rule matched the keywords\n")
        return
    for _, row in scored[:limit]:
        avoid = row["Don't"]
        print(f"- {row['Category']} / {row['Issue']} [{row['Severity'] or 'n/a'}]")
        print(f"    do: {_trim(row['Do'], 200)}")
        print(f"    don't: {_trim(avoid, 200)}")
    print()


def _print_motion():
    print("## Motion tiers")
    for row in _load("motion.csv"):
        avoid = row["Don't"]
        print(f"- {row['Category']} ({row['Intensity Tier']}): {row['Duration']}, {row['Easing']}")
        print(f"    do: {_trim(row['Do'], 160)}")
        print(f"    don't: {_trim(avoid, 120)}")
    print()


def _print_charts(query, limit=3):
    print("## Chart guidance")
    scored = []
    for row in _load("charts.csv"):
        overlap = len(query & _tokens(row["Data Type"] + " " + row["Keywords"]))
        if overlap:
            scored.append((overlap, row))
    scored.sort(key=lambda item: -item[0])
    if not scored:
        print("- no chart rule matched the keywords\n")
        return
    for _, row in scored[:limit]:
        print(f"- {row['Data Type']}: {row['Best Chart Type']}")
        print(f"    accessibility: {_trim(row['A11y Fallback'], 180)}")
    print()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Product-type precedents for a UI brief.")
    parser.add_argument("query", help="English keywords, e.g. 'saas dashboard dark'")
    parser.add_argument("--top", type=int, default=1, help="product types to detail (default 1)")
    parser.add_argument("--ux", action="store_true", help="add matching UX guideline rules")
    parser.add_argument("--motion", action="store_true", help="add the motion duration tiers")
    parser.add_argument("--charts", action="store_true", help="add matching chart guidance")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    query = _tokens(args.query)
    if not query:
        parser.error("use English keywords such as 'saas dashboard' or 'portfolio'")

    products = _load("products.csv")
    ranked = []
    for row in products:
        in_name = len(query & _tokens(row["Product Type"]))
        in_keywords = len(query & _tokens(row["Keywords"]))
        if in_name or in_keywords:
            # A match on the product name outranks a match on its keyword list.
            ranked.append((3 * in_name + in_keywords, in_name + in_keywords, row))
    ranked.sort(key=lambda item: (-item[0], int(item[2]["No"] or 0)))
    if not ranked:
        print("No product type matched. Try broader keywords. Product types in the data:")
        print("; ".join(row["Product Type"] for row in products))
        return 1

    print("# Product types matched")
    for _, matched, row in ranked[: max(args.top, 1)]:
        print(f"- {row['Product Type']} (matched {matched} keyword{'s' if matched != 1 else ''})")
    print()

    product = ranked[0][2]
    product_type = product["Product Type"]
    print(f"# Detail: {product_type}")
    print(f"- key considerations: {_trim(product['Key Considerations'], 300)}")
    print(f"- landing pattern: {product['Landing Page Pattern'] or '-'}")
    print(f"- dashboard style: {product['Dashboard Style (if applicable)'] or '-'}")
    print(f"- color palette focus: {product['Color Palette Focus'] or '-'}")
    print()

    styles = _load("styles.csv")
    style_rows = _print_styles(product, styles)
    _print_palette(product_type, _load("colors.csv"))
    _print_typography(query, style_rows, _load("typography.csv"))
    _print_reasoning(product_type, _load("ui-reasoning.csv"))
    if args.ux:
        _print_ux(query)
    if args.motion:
        _print_motion()
    if args.charts:
        _print_charts(query)

    print("Evidence, not a verdict: choose a direction on purpose, then run wcag.py on the final palette and slop_scan.py on the code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
