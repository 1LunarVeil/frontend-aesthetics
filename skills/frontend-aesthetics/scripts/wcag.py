"""WCAG 2.x contrast checks for #hex, rgb() and oklch() colors.

Usage: python wcag.py FG BG [FG BG ...]

Alpha channels are ignored: composite a translucent color onto its real
background before checking it. Out-of-gamut oklch values are clipped to sRGB.
"""

import argparse
import math
import re
import sys

AA_TEXT = 4.5
AA_LARGE_OR_UI = 3.0
AAA_TEXT = 7.0

_HEX = re.compile(r"#([0-9a-f]{3}|[0-9a-f]{6})")
_RGB = re.compile(r"rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)")
_OKLCH = re.compile(
    r"oklch\(\s*([\d.]+%?)\s+([\d.]+)\s+([\d.]+)(?:deg)?(?:\s*/\s*[\d.]+%?)?\s*\)"
)


def _to_linear(channel):
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def _to_srgb(channel):
    channel = min(max(channel, 0.0), 1.0)
    if channel <= 0.0031308:
        return 12.92 * channel
    return 1.055 * channel ** (1 / 2.4) - 0.055


def parse_color(value):
    """Return (r, g, b) with each channel in 0..1."""
    text = value.strip().lower()
    match = _HEX.fullmatch(text)
    if match:
        digits = match.group(1)
        if len(digits) == 3:
            digits = "".join(ch * 2 for ch in digits)
        return tuple(int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4))

    match = _RGB.match(text)
    if match:
        return tuple(min(max(float(part) / 255, 0.0), 1.0) for part in match.groups())

    match = _OKLCH.fullmatch(text)
    if match:
        lightness_text, chroma_text, hue_text = match.groups()
        if lightness_text.endswith("%"):
            lightness = float(lightness_text[:-1]) / 100
        else:
            lightness = float(lightness_text)
        chroma = float(chroma_text)
        hue = math.radians(float(hue_text))
        a = chroma * math.cos(hue)
        b = chroma * math.sin(hue)
        l_ = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
        m_ = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
        s_ = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
        red = 4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
        green = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
        blue = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
        return tuple(_to_srgb(channel) for channel in (red, green, blue))

    raise ValueError(f"unsupported color {value!r}; use #hex, rgb() or oklch()")


def relative_luminance(rgb):
    red, green, blue = (_to_linear(channel) for channel in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(fg, bg):
    lighter, darker = sorted(
        (relative_luminance(parse_color(fg)), relative_luminance(parse_color(bg))),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def _verdict(ratio, threshold):
    return "pass" if ratio >= threshold else "FAIL"


def main(argv=None):
    parser = argparse.ArgumentParser(description="WCAG contrast check for FG BG color pairs.")
    parser.add_argument("colors", nargs="+", metavar="COLOR", help="FG BG pairs, e.g. '#1f2937' '#ffffff'")
    args = parser.parse_args(argv)
    if len(args.colors) % 2:
        parser.error("colors must come in FG BG pairs")

    pairs = list(zip(args.colors[::2], args.colors[1::2]))
    try:
        ratios = [contrast_ratio(fg, bg) for fg, bg in pairs]
    except ValueError as exc:
        parser.error(str(exc))

    sys.stdout.reconfigure(encoding="utf-8")
    for (fg, bg), ratio in zip(pairs, ratios):
        print(
            f"{fg} on {bg}: {ratio:.2f}:1  "
            f"text AA {_verdict(ratio, AA_TEXT)}  "
            f"large text / UI AA {_verdict(ratio, AA_LARGE_OR_UI)}  "
            f"text AAA {_verdict(ratio, AAA_TEXT)}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
