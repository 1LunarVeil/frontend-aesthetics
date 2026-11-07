"""Browser-free tests for page_audit.py.

The collector runs in a browser, so everything Python-side is pinned here with
synthetic rows shaped exactly like the collector emits (page_audit.row fields
are dicts; real-browser behaviour is a manual smoke, per the WS-A convention).
"""

import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "skills" / "frontend-aesthetics" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import page_audit  # noqa: E402


def run(main, argv):
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


def row(**overrides):
    """One collector row: near-black on white body text by default."""
    base = {
        "method": "resolved",
        "fg": "rgb(51, 51, 51)",
        "bg": "rgb(255, 255, 255)",
        "font_size": 16,
        "font_weight": 400,
        "rect": {"x": 8, "y": 8, "width": 200, "height": 24},
        "text": "sample text",
        "tag": "p",
        "evidence": None,
    }
    base.update(overrides)
    return base


def payload(rows, **overrides):
    base = {"color_scheme": "light", "canvas": "#ffffff",
            "rows": rows, "skipped": 0, "capped": False, "limit": 400}
    base.update(overrides)
    return base


class ThresholdTests(unittest.TestCase):
    def test_measurable_pass_gets_ratio_and_threshold(self):
        # rgb(118,118,118) on white is 4.54:1 — over the 4.5 floor.
        result = page_audit.verdict(row(fg="rgb(118, 118, 118)"))
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["threshold"], 4.5)
        self.assertAlmostEqual(result["ratio"], 4.54, places=2)

    def test_fail_at_4_5(self):
        # rgb(153,153,153) on white is 2.85:1.
        result = page_audit.verdict(row(fg="rgb(153, 153, 153)"))
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(result["threshold"], 4.5)
        self.assertAlmostEqual(result["ratio"], 2.85, places=2)

    def test_large_text_thresholds_at_boundaries(self):
        cases = [
            ({"font_size": 24, "font_weight": 400}, 3.0),   # >= 24px, any weight
            ({"font_size": 24, "font_weight": 700}, 3.0),
            ({"font_size": 23.9, "font_weight": 400}, 4.5),
            ({"font_size": 18.66, "font_weight": 700}, 3.0),  # bold large floor
            ({"font_size": 18.65, "font_weight": 700}, 4.5),
            ({"font_size": 18.66, "font_weight": 400}, 4.5),  # large size, not bold
            ({"font_size": 16, "font_weight": 900}, 4.5),
        ]
        for overrides, expected in cases:
            self.assertEqual(page_audit.threshold_for(row(**overrides)), expected, overrides)

    def test_large_text_3_to_1_verdict(self):
        # rgb(128,128,128) on white is 3.95:1: passes as 24px bold, fails as body text.
        large = page_audit.verdict(row(fg="rgb(128, 128, 128)",
                                       font_size=24, font_weight=700))
        self.assertEqual(large["verdict"], "pass")
        self.assertEqual(large["threshold"], 3.0)
        body = page_audit.verdict(row(fg="rgb(128, 128, 128)"))
        self.assertEqual(body["verdict"], "FAIL")
        self.assertEqual(body["threshold"], 4.5)


class ClassifyTests(unittest.TestCase):
    def test_assumed_canvas_labeled_verdicted_and_counted(self):
        rows = [
            row(method="assumed-canvas", bg="#ffffff"),
            row(method="assumed-canvas", bg="#ffffff", fg="rgb(153, 153, 153)"),
        ]
        verdicts, uncertain, skipped = page_audit.classify_rows(rows)
        self.assertEqual(skipped, 0)
        self.assertEqual(uncertain, [])
        self.assertEqual([v["method"] for v in verdicts], ["assumed-canvas"] * 2)
        self.assertEqual([v["verdict"] for v in verdicts], ["pass", "FAIL"])
        report = page_audit.build_report("http://x/", payload(rows))
        self.assertEqual(report["summary"]["assumed_canvas"], 2)

    def test_uncertain_methods_preserved_verbatim_never_verdicted(self):
        methods = [
            ("uncertain:gradient-or-image", "linear-gradient(90deg, rgb(11, 87, 208), rgb(168, 199, 250))"),
            ("uncertain:blend-or-filter", "div.fade opacity=0.5"),
            ("uncertain:occluded", "div.cookie-bar"),
            ("uncertain:some-future-method", "whatever"),
        ]
        rows = [row(method=method, evidence=evidence) for method, evidence in methods]
        verdicts, uncertain, skipped = page_audit.classify_rows(rows)
        self.assertEqual([verdicts, skipped], [[], 0])
        self.assertEqual([u["method"] for u in uncertain], [m for m, _ in methods])
        self.assertEqual([u["evidence"] for u in uncertain], [e for _, e in methods])
        for entry in uncertain:
            self.assertNotIn("verdict", entry)
            self.assertNotIn("ratio", entry)
            self.assertIsNone(page_audit.verdict(entry))

    def test_occluded_row_classified_with_cover_evidence(self):
        rows = [row(method="uncertain:occluded", evidence="header.site-nav")]
        verdicts, uncertain, _ = page_audit.classify_rows(rows)
        self.assertEqual(verdicts, [])
        self.assertEqual(uncertain[0]["method"], "uncertain:occluded")
        self.assertEqual(uncertain[0]["evidence"], "header.site-nav")

    def test_skipped_counted_not_listed(self):
        rows = [
            row(),
            row(method="skipped", text="hidden heading", tag="h1"),
        ]
        verdicts, uncertain, skipped = page_audit.classify_rows(rows, skipped_count=2)
        self.assertEqual(skipped, 3)
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(uncertain, [])
        report = page_audit.build_report("http://x/", payload(rows, skipped=2))
        self.assertEqual(report["summary"]["skipped"], 3)
        self.assertNotIn("skipped", [str(entry.get("method")) for entry in report["results"]])

    def test_unparseable_color_becomes_uncertain_not_a_crash(self):
        # wcag.parse_color has no hsl support; the row must degrade, not raise.
        rows = [row(fg="hsl(0, 50%, 50%)")]
        verdicts, uncertain, _ = page_audit.classify_rows(rows)
        self.assertEqual(verdicts, [])
        self.assertEqual(uncertain[0]["method"], "uncertain:unparseable")
        self.assertIn("hsl", uncertain[0]["evidence"])

    def test_summary_math(self):
        rows = [
            row(),                                   # pass
            row(text="b"),                           # pass
            row(text="c"),                           # pass
            row(fg="rgb(153, 153, 153)", text="d"),  # FAIL
            row(fg="rgb(153, 153, 153)", text="e"),  # FAIL
            row(method="uncertain:gradient-or-image", evidence="linear-gradient(1px)"),
            row(method="uncertain:occluded", evidence="div.nav"),
        ]
        report = page_audit.build_report("http://x/", payload(rows, skipped=1))
        summary = report["summary"]
        self.assertEqual(summary["checked"], 7)
        self.assertEqual(summary["pass"], 3)
        self.assertEqual(summary["fail"], 2)
        self.assertEqual(summary["uncertain"], 2)
        self.assertEqual(summary["skipped"], 1)
        self.assertEqual(summary["checked"], summary["pass"] + summary["fail"] + summary["uncertain"])
        self.assertEqual(summary["assumed_canvas"], 0)

    def test_exit_code_rule_is_fail_only(self):
        self.assertEqual(1 if page_audit.build_report(
            "http://x/", payload([row(fg="rgb(153, 153, 153)")]))["summary"]["fail"] else 0, 1)
        self.assertEqual(1 if page_audit.build_report(
            "http://x/", payload([row(method="uncertain:occluded", evidence="d")]))["summary"]["fail"] else 0, 0)


class ReportTests(unittest.TestCase):
    def test_header_carries_url_canvas_assumption_and_scheme(self):
        report = page_audit.build_report(
            "http://127.0.0.1:8125/", payload([row()], color_scheme="light", canvas="#ffffff"))
        self.assertEqual(report["url"], "http://127.0.0.1:8125/")
        self.assertTrue(report["verified"])
        self.assertEqual(report["color_scheme"], "light")
        self.assertIn("#ffffff", report["canvas_assumption"])
        self.assertIn("prefers-color-scheme: light", report["canvas_assumption"])

    def test_text_report_orders_fails_then_uncertain_then_summary(self):
        rows = [
            row(method="assumed-canvas", bg="#ffffff"),
            row(method="uncertain:gradient-or-image", evidence="linear-gradient(90deg, a, b)"),
            row(fg="rgb(153, 153, 153)", text="Failing pair."),
        ]
        text = page_audit.render_text(page_audit.build_report("http://x/", payload(rows)))
        lines = text.splitlines()
        self.assertIn("Page contrast audit: http://x/", lines[0])
        self.assertIn("Canvas assumption:", lines[1])
        fails = [i for i, line in enumerate(lines) if line.startswith("FAIL ")]
        uncertains = [i for i, line in enumerate(lines) if line.startswith("UNCERTAIN ")]
        summary = [i for i, line in enumerate(lines) if line.startswith("checked ")]
        self.assertEqual(len(fails), 1)
        self.assertEqual(len(uncertains), 1)
        self.assertLess(fails[0], uncertains[0])
        self.assertLess(uncertains[0], summary[0])
        self.assertIn('UNCERTAIN uncertain:gradient-or-image "sample text" p '
                      '[linear-gradient(90deg, a, b)]', lines[uncertains[0]])
        self.assertIn("checked 3 text pairs: 1 pass, 1 fail, 1 uncertain, "
                      "0 skipped (1 assumed canvas)", lines[summary[0]])

    def test_capped_note_in_text_and_summary(self):
        report = page_audit.build_report("http://x/", payload([row()], capped=True, limit=3))
        self.assertTrue(report["summary"]["capped"])
        self.assertEqual(report["summary"]["limit"], 3)
        self.assertIn("[capped at 3 entries]", page_audit.render_text(report))

    def test_json_report_shape(self):
        rows = [row(fg="rgb(153, 153, 153)"),
                row(method="uncertain:occluded", evidence="div.nav")]
        report = page_audit.build_report("http://x/", payload(rows, skipped=1))
        rendered = json.loads(json.dumps(report))
        self.assertEqual(set(rendered), {"url", "verified", "color_scheme",
                                         "canvas_assumption", "results", "summary"})
        self.assertTrue(rendered["verified"])
        self.assertEqual(len(rendered["results"]), 2)
        self.assertEqual(set(rendered["summary"]), {
            "checked", "pass", "fail", "uncertain", "skipped", "assumed_canvas", "capped"})


class CliTests(unittest.TestCase):
    URL = "http://127.0.0.1:1/"  # loopback: validate_url needs no network

    def test_rejected_url_exits_3_and_claims_nothing(self):
        code, out = run(page_audit.main, ["ftp://example.com/"])
        self.assertEqual(code, 3)
        body = json.loads(out)
        self.assertFalse(body["verified"])
        self.assertIn("URL rejected", body["reason"])

    def test_cdp_failure_exits_2_with_unverified_json(self):
        with mock.patch.object(page_audit, "audit_url",
                               side_effect=RuntimeError("browser exploded")):
            code, out = run(page_audit.main, [self.URL, "--json"])
        self.assertEqual(code, 2)
        body = json.loads(out)
        self.assertEqual(set(body), {"verified", "reason"})
        self.assertFalse(body["verified"])
        self.assertIn("browser exploded", body["reason"])

    def test_json_cli_shape_with_stubbed_audit(self):
        stub = payload(
            [row(), row(method="uncertain:occluded", evidence="div.nav")], skipped=1)
        with mock.patch.object(page_audit, "audit_url", return_value=stub):
            code, out = run(page_audit.main, [self.URL, "--json"])
        self.assertEqual(code, 0)
        body = json.loads(out)
        self.assertEqual(body["url"], self.URL)
        self.assertTrue(body["verified"])
        self.assertEqual(body["color_scheme"], "light")
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["summary"]["checked"], 2)
        self.assertEqual(body["summary"]["skipped"], 1)

    def test_text_cli_shape_and_exit_1_on_fail(self):
        stub = payload([row(fg="rgb(153, 153, 153)", text="Failing pair.")])
        with mock.patch.object(page_audit, "audit_url", return_value=stub):
            code, out = run(page_audit.main, [self.URL])
        self.assertEqual(code, 1)
        self.assertIn("FAIL rgb(153, 153, 153) on rgb(255, 255, 255) 2.85:1", out)
        self.assertIn("checked 1 text pairs: 0 pass, 1 fail, 0 uncertain, "
                      "0 skipped (0 assumed canvas)", out)


if __name__ == "__main__":
    unittest.main()
