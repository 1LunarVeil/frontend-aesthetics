"""Tests for the frontend-aesthetics scripts.

Run from the plugin root: python -B -m unittest discover -s tests -v
(-B keeps __pycache__ out of the plugin tree.)
"""

import io
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "skills" / "frontend-aesthetics" / "scripts"
FIXTURES = TESTS / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import design_lookup  # noqa: E402
import slop_scan  # noqa: E402
import wcag  # noqa: E402


def run(main, argv):
    """Run a script's main() with stdout and stderr captured; return (exit code, stdout text)."""
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="utf-8", write_through=True)
    original_out, original_err = sys.stdout, sys.stderr
    sys.stdout = stream
    sys.stderr = io.StringIO()
    try:
        code = main(argv)
    except SystemExit as exc:
        code = exc.code
    finally:
        sys.stdout, sys.stderr = original_out, original_err
    stream.flush()
    return code, raw.getvalue().decode("utf-8")


class WcagTests(unittest.TestCase):
    def test_reference_values(self):
        self.assertAlmostEqual(wcag.contrast_ratio("#000000", "#ffffff"), 21.0, places=2)
        self.assertAlmostEqual(wcag.contrast_ratio("#767676", "#ffffff"), 4.54, places=2)
        self.assertAlmostEqual(wcag.contrast_ratio("#777777", "#ffffff"), 4.48, places=2)

    def test_oklch_agrees_with_srgb(self):
        self.assertAlmostEqual(wcag.contrast_ratio("oklch(0.628 0.2577 29.23)", "#ffffff"), 4.00, places=2)
        self.assertAlmostEqual(wcag.contrast_ratio("oklch(0.546 0.2153 262.9)", "#ffffff"), 5.17, places=2)

    def test_unknown_syntax_is_rejected(self):
        with self.assertRaises(ValueError):
            wcag.parse_color("tomato-ish")


class LookupTests(unittest.TestCase):
    def test_name_match_outranks_keyword_match(self):
        code, out = run(design_lookup.main, ["portfolio"])
        self.assertEqual(code, 0)
        self.assertIn("# Detail: Portfolio/Personal", out)

    def test_fintech_brief_resolves_to_its_own_row(self):
        _, out = run(design_lookup.main, ["fintech"])
        self.assertIn("# Detail: Fintech/Crypto", out)

    def test_palette_section_reports_contrast_results(self):
        _, out = run(design_lookup.main, ["saas dashboard"])
        self.assertIn("text pairs failing:", out)
        self.assertIn("text Foreground on Background:", out)

    def test_chinese_only_query_is_rejected(self):
        code, _ = run(design_lookup.main, ["作品集"])
        self.assertEqual(code, 2)

    def test_unmatched_query_returns_one_and_lists_types(self):
        code, out = run(design_lookup.main, ["zzqqxx"])
        self.assertEqual(code, 1)
        self.assertIn("Product types in the data", out)


class ScanTests(unittest.TestCase):
    def test_tells_fixture_triggers_expected_rules(self):
        findings, scanned = slop_scan.scan([str(FIXTURES / "tells" / "index.html")])
        rules = {finding.rule for finding in findings}
        expected = {
            "A11Y-ZOOM", "A11Y-IMG-ALT", "A11Y-FOCUS-REMOVED", "A11Y-TABINDEX",
            "A11Y-REDUCED-MOTION", "TYPE-TINY", "TYPE-DEFAULT-PRIMARY", "TYPE-CAPS",
            "MOTION-ALL", "MOTION-GENERIC-ENTRANCE", "COLOR-PURPLE-GRADIENT",
            "COLOR-PURE-BLACK", "COLOR-GREY-SHADOW", "COLOR-RAW-HEX", "COPY-LOREM",
            "COPY-GENERIC-ERROR", "COPY-SUBMIT", "COPY-ARROW-CTA", "COPY-MIDDOT-META",
        }
        self.assertEqual(expected - rules, set())
        self.assertEqual(scanned, 1)

    def test_clean_fixture_has_no_blocking_or_important_findings(self):
        findings, _ = slop_scan.scan([str(FIXTURES / "clean" / "app.css")])
        self.assertEqual([f for f in findings if f.severity in ("blocking", "important")], [])

    def test_comment_lines_are_not_scanned(self):
        text = '/* transition: all 0.3s; */\n// <img src="a.png">\n'
        self.assertEqual(slop_scan.scan_text(Path("x.html"), text), [])

    def test_layout_transition_is_review_level(self):
        findings = slop_scan.scan_text(Path("x.css"), ".drawer { transition: width 0.2s; }\n")
        self.assertEqual([(f.rule, f.severity) for f in findings], [("MOTION-LAYOUT", "review")])

    def test_exit_status_reflects_blocking_findings(self):
        code, _ = run(slop_scan.main, [str(FIXTURES / "tells" / "index.html")])
        self.assertEqual(code, 1)
        code, _ = run(slop_scan.main, [str(FIXTURES / "clean" / "app.css")])
        self.assertEqual(code, 0)

    def test_fixture_directories_are_skipped_when_scanning_a_folder(self):
        _, scanned = slop_scan.scan([str(TESTS)])
        self.assertEqual(scanned, 0)


if __name__ == "__main__":
    unittest.main()
