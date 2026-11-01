"""Scan UI source for generic-default ("AI slop") tells and craft defects.

Usage: python slop_scan.py PATH [PATH ...] [--json] [--include-tests] [--limit N]

Read-only. Findings are prompts for a decision, not verdicts: a default is
fine when it was chosen for the brief. Rule IDs map to references/anti-slop.md.
Exit status is 1 when any blocking finding exists, otherwise 0.
"""

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

MAX_FILE_BYTES = 1_000_000
SEVERITY_ORDER = {"blocking": 0, "important": 1, "review": 2, "polish": 3}
SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", "target", "out", ".next", "vendor",
    "__pycache__", ".venv", "venv", "coverage", "release", "_internal",
    "webview2-data", "logs",
}
TEST_DIRS = {"tests", "test", "__tests__", "spec", "fixtures", "mocks"}
TOKEN_FILE = re.compile(r"token|theme|variable|design", re.IGNORECASE)
HEX = re.compile(r"(?<![\w&-])#[0-9a-fA-F]{3,8}(?![\w-])")
FOCUS_REMOVED = re.compile(r"outline\s*:\s*(?:none|0)\b", re.IGNORECASE)
FOCUS_REPLACEMENT = re.compile(r"focus-visible|:focus\b|focus-within|\bfocus:", re.IGNORECASE)
MOTION_USE = re.compile(r"transition\s*:|animation\s*:|@keyframes|transition-|animate-", re.IGNORECASE)
REDUCED_MOTION = re.compile(r"prefers-reduced-motion", re.IGNORECASE)

MARKUP = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro"}
STYLE = {".css", ".scss", ".sass", ".less", ".styl"}
SCRIPT = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".astro"}
CODE = MARKUP | STYLE | SCRIPT
ANY = CODE


@dataclass
class Rule:
    id: str
    severity: str
    extensions: set
    pattern: re.Pattern
    message: str
    below: float = None  # for numeric rules: report only values below this


def _rule(rule_id, severity, extensions, pattern, message, below=None):
    return Rule(rule_id, severity, extensions, re.compile(pattern, re.IGNORECASE), message, below)


RULES = [
    _rule("A11Y-ZOOM", "blocking", MARKUP,
          r"user-scalable\s*=\s*(?:no|0)\b|maximum-scale\s*=\s*1(?:\.0+)?(?![\d.])",
          "zoom is disabled, so users cannot enlarge text (WCAG 1.4.4)"),
    _rule("A11Y-IMG-ALT", "blocking", MARKUP | SCRIPT,
          r"<img\b(?![^>]*\balt\s*=)[^>]*>",
          'img without alt; use alt="" when the image is decorative (WCAG 1.1.1)'),
    _rule("A11Y-TABINDEX", "important", MARKUP | SCRIPT,
          r"tabindex\s*=\s*[\"']?[1-9]\d*",
          "positive tabindex overrides the natural focus order (WCAG 2.4.3)"),
    _rule("TYPE-TINY", "important", CODE,
          r"(?:font-size\s*:\s*|text-\[)(\d+(?:\.\d+)?)px",
          "text under 12px; body copy should be 14px or larger on desktop and 16px on the web",
          below=12),
    _rule("MOTION-ALL", "important", CODE,
          r"transition\s*:\s*all\b|transition-all\b",
          "transition: all animates every property; list the properties that change"),
    _rule("MOTION-LAYOUT", "review", CODE,
          r"transition\s*:[^;{}]*\b(?:width|height|top|left|right|bottom|margin|padding)\b",
          "transitions a layout property; prefer transform and opacity unless this is a deliberate reveal"),
    _rule("MOTION-GENERIC-ENTRANCE", "review", CODE,
          r"fade-?in-?up|slide-?up|fade-?up\b|rise-?in\b|animate-fade-in",
          "generic fade-and-slide entrance; motion should show what changed or be one orchestrated moment"),
    _rule("TYPE-DEFAULT-PRIMARY", "review", CODE,
          r"font-family\s*:\s*[\"']?(?:Inter|Roboto|Arial|Open Sans)\b",
          "a common default is the primary family; keep it only if it was chosen for this brief"),
    _rule("TYPE-CAPS", "review", CODE,
          r"text-transform\s*:\s*uppercase",
          "all-caps text; keep it for short labels that have enough letter-spacing"),
    _rule("COLOR-PURPLE-GRADIENT", "review", CODE,
          r"gradient\([^;{}]*#(?:7c3aed|8b5cf6|a855f7|6366f1|9333ea|7e22ce|6d28d9|4f46e5|667eea|764ba2|c084fc)\b",
          "purple-to-blue gradient, the most common generated accent; confirm it is a deliberate choice"),
    _rule("COLOR-PURE-BLACK", "polish", CODE,
          r"(?:background|color|border)[\w-]*\s*:[^;{}]*#0{3}(?:0{3})?\b",
          "pure black; a tinted near-black usually reads better"),
    _rule("COLOR-GREY-SHADOW", "review", CODE,
          r"box-shadow\s*:[^;{}]*rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0?\.\d+\s*\)",
          "generic black shadow; tint it to the palette or drop it"),
    _rule("COPY-LOREM", "important", ANY,
          r"lorem ipsum",
          "placeholder copy left in the UI"),
    _rule("COPY-GENERIC-ERROR", "review", MARKUP | SCRIPT,
          r"something went wrong|\boops\b|no results found|please try again later",
          "generic error or empty copy; say what happened and what to do next"),
    _rule("COPY-SUBMIT", "review", MARKUP | SCRIPT,
          r">\s*submit\s*<|value\s*=\s*[\"']submit[\"']",
          "'Submit' does not say what happens; name the action, such as 'Save changes'"),
    _rule("COPY-ARROW-CTA", "review", MARKUP | SCRIPT,
          r"(?:<button\b|<a\b|role\s*=\s*[\"']button).*→|→.*</(?:button|a)>",
          "arrow glyph on a control; a plain verb reads better"),
    _rule("COPY-MIDDOT-META", "review", MARKUP | SCRIPT,
          r"[A-Za-z0-9)]\s+·\s+[A-Za-z0-9(]",
          "middle-dot separated metadata, a common template tell"),
]


@dataclass
class Finding:
    rule: str
    severity: str
    file: str
    line: int
    snippet: str
    message: str


def _snippet(line):
    text = " ".join(line.split())
    return text if len(text) <= 140 else text[:137] + "..."


def _is_comment(line):
    stripped = line.strip()
    if stripped.startswith(("//", "/*", "<!--")):
        return True
    return stripped.startswith("*") and "{" not in stripped


def _code_lines(lines):
    return [(number, line) for number, line in enumerate(lines, start=1) if not _is_comment(line)]


def _display(path):
    try:
        relative = os.path.relpath(path)
    except ValueError:
        return str(path)
    return str(path) if relative.startswith("..") else relative


def iter_files(paths, include_tests):
    for raw in paths:
        root = Path(raw)
        if root.is_file():
            yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                name for name in dirnames
                if name not in SKIP_DIRS and (include_tests or name not in TEST_DIRS)
            ]
            for name in sorted(filenames):
                candidate = Path(dirpath) / name
                if candidate.suffix.lower() in CODE:
                    yield candidate


def _focus_findings(path, lines, text):
    if path.suffix.lower() not in CODE:
        return []
    has_replacement = FOCUS_REPLACEMENT.search(text) is not None
    severity = "important" if has_replacement else "blocking"
    suffix = "" if has_replacement else " and this file has no focus style"
    found = []
    for number, line in _code_lines(lines):
        if FOCUS_REMOVED.search(line):
            found.append(Finding(
                "A11Y-FOCUS-REMOVED", severity, _display(path), number, _snippet(line),
                f"focus outline removed{suffix} (WCAG 2.4.7)",
            ))
    return found


def _hex_findings(path, lines):
    if path.suffix.lower() not in CODE or TOKEN_FILE.search(path.name):
        return []
    hits = []
    for number, line in _code_lines(lines):
        if "--" in line:  # custom property definitions and var() fallbacks
            continue
        hits.extend((number, line) for _ in HEX.finditer(line))
    if len(hits) < 8:
        return []
    number, line = hits[0]
    return [Finding(
        "COLOR-RAW-HEX", "polish", _display(path), number, _snippet(line),
        f"{len(hits)} raw hex colors outside token definitions; move them into the token file",
    )]


def scan_text(path, text):
    ext = path.suffix.lower()
    lines = text.splitlines()
    found = []
    for rule in RULES:
        if ext not in rule.extensions:
            continue
        for number, line in _code_lines(lines):
            if rule.below is not None:
                hit = any(float(match.group(1)) < rule.below for match in rule.pattern.finditer(line))
            else:
                hit = rule.pattern.search(line) is not None
            if hit:
                found.append(Finding(rule.id, rule.severity, _display(path), number, _snippet(line), rule.message))
    found.extend(_focus_findings(path, lines, text))
    found.extend(_hex_findings(path, lines))
    return found


def _reduced_motion_findings(texts):
    if any(REDUCED_MOTION.search(text) for text in texts.values()):
        return []
    for path in sorted(texts):
        if path.suffix.lower() not in CODE:
            continue
        for number, line in _code_lines(texts[path].splitlines()):
            if MOTION_USE.search(line):
                return [Finding(
                    "A11Y-REDUCED-MOTION", "important", _display(path), number, _snippet(line),
                    "motion is used, but no scanned file honours prefers-reduced-motion (WCAG 2.3.3)",
                )]
    return []


def scan(paths, include_tests=False):
    texts = {}
    findings = []
    for path in iter_files(paths, include_tests):
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        texts[path] = text
        findings.extend(scan_text(path, text))
    findings.extend(_reduced_motion_findings(texts))
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.file, f.line))
    return findings, len(texts)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scan UI source for generic-default tells and craft defects.")
    parser.add_argument("paths", nargs="+", help="files or directories to scan")
    parser.add_argument("--json", action="store_true", help="print findings as JSON")
    parser.add_argument("--include-tests", action="store_true", help="also scan test and fixture directories")
    parser.add_argument("--limit", type=int, default=200, help="maximum findings to print in text mode")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    findings, scanned = scan(args.paths, include_tests=args.include_tests)
    blocking = sum(f.severity == "blocking" for f in findings)

    if args.json:
        print(json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=2))
    else:
        for finding in findings[: args.limit]:
            print(f"{finding.severity:<9} {finding.rule:<24} {finding.file}:{finding.line}  {finding.snippet}")
            print(f"{'':<9} {'':<24} {finding.message}")
        if len(findings) > args.limit:
            print(f"... {len(findings) - args.limit} more; use --json or a higher --limit")
        counts = {level: sum(f.severity == level for f in findings) for level in SEVERITY_ORDER}
        print(
            f"scanned {scanned} file{'s' if scanned != 1 else ''}: "
            f"{counts['blocking']} blocking, {counts['important']} important, "
            f"{counts['review']} review, {counts['polish']} polish"
        )
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
