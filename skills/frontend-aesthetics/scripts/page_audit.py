"""Audit rendered text contrast on a live page over CDP.

Usage:
  python page_audit.py URL [--json] [--allow-private] [--limit N]

One persistent headless browser (sibling cdp.py; the launch sequence is shared
with visual_capture.py) navigates the URL, then a single Runtime.evaluate
walks every element that directly contains non-whitespace text and reports,
per the uncertainty taxonomy in notes/roadmap-0.1.3-2.0.md (修订 2):

- resolved        an ancestor background-color with alpha > 0 was found;
                  translucent layers are composited over the canvas first,
                  then Python computes the WCAG ratio (pass/FAIL verdict)
- assumed-canvas  nothing opaque up to the root; measured against the canvas
                  color implied by prefers-color-scheme — the assumption is
                  stated in the report header and counted in the summary
- uncertain:*     a gradient/image behind the text, opacity/blend/filter in
                  the ancestor chain, a fixed/sticky overlay covering the
                  text, or a color wcag.parse_color rejects — listed with
                  their evidence and NEVER verdicted; the visual capture loop
                  is the only way to settle these
- skipped         invisible text (display:none, visibility hidden, zero-size
                  rect, font-size 0) — counted, not listed

Every text pair lands in exactly one bucket. Uncertain findings describe what
was seen; they never masquerade as pass/fail. page_audit supplements, never
replaces, the capture loop.

Exit status: 0 no measurable failures, 1 at least one FAIL, 2 no browser or
browser/CDP failure ({"verified": false, "reason": ...} — the tool claims
nothing about the page), 3 URL rejected (visual_capture.validate_url).

Read-only: prints a report and writes nothing. stdlib only; CDP on loopback.
"""

import argparse
import json
import shutil
import sys

sys.dont_write_bytecode = True
import cdp  # noqa: E402  (sibling module; no third-party dependencies)
import visual_capture  # noqa: E402  (validate_url / find_browser / launch)
import wcag  # noqa: E402

MAX_ROWS = 400
MAX_COVERS = 20
SNIPPET_CHARS = 60
LOAD_TIMEOUT = 10.0
LARGE_SIZE = 24.0
LARGE_BOLD_SIZE = 18.66
BOLD_WEIGHT = 700

CANVAS_ASSUMPTION = (
    "text with no opaque ancestor background was measured against the "
    "{scheme} canvas color {canvas} (prefers-color-scheme: {scheme})"
)

# One evaluate per page. Walks body-scoped elements that directly contain
# non-whitespace text; classification happens in the browser because that is
# where the ancestor chains live; Python only does color math and verdicts.
# __MAX_ROWS__ is replaced by Python (str.replace, not str.format: the JS is
# full of braces). Rects are viewport coordinates at evaluation time, the same
# space the fixed/sticky cover rects use.
COLLECTOR_JS = r"""(function () {
  var MAX_ROWS = __MAX_ROWS__;
  var SNIPPET = 60;
  var result;
  try {
    result = collect();
  } catch (err) {
    result = { error: String((err && err.message) || err) };
  }
  return JSON.stringify(result);

  function collect() {
    var dark = false;
    try { dark = window.matchMedia("(prefers-color-scheme: dark)").matches; } catch (e) {}
    var canvas = dark ? "#000000" : "#ffffff";

    var scope = document.body || document.documentElement;
    var universe = [scope];
    var descendants = scope.getElementsByTagName("*");
    for (var di = 0; di < descendants.length; di++) universe.push(descendants[di]);

    // Overlays that can sit on top of text regardless of scroll (v1 heuristic).
    var covers = [];
    for (var ui = 0; ui < universe.length && covers.length < 20; ui++) {
      var ucs = styleOf(universe[ui]);
      if (ucs.position === "fixed" || ucs.position === "sticky") {
        var ucr = universe[ui].getBoundingClientRect();
        if (ucr.width > 0 && ucr.height > 0) {
          covers.push({ el: universe[ui], x: ucr.left, y: ucr.top,
                        w: ucr.width, h: ucr.height });
        }
      }
    }

    var rows = [], skipped = 0, capped = false;
    for (var ri = 0; ri < universe.length; ri++) {
      var el = universe[ri];
      var text = "";
      for (var node = el.firstChild; node; node = node.nextSibling) {
        if (node.nodeType === 3) text += node.nodeValue;
      }
      text = text.replace(/\s+/g, " ").trim();
      if (!text) continue;                 // no direct text: not a text pair
      if (rows.length >= MAX_ROWS) { capped = true; break; }

      var cs = styleOf(el);
      var rect = el.getBoundingClientRect();
      if (cs.display === "none" || cs.visibility === "hidden" || cs.visibility === "collapse"
          || rect.width <= 0 || rect.height <= 0 || parseFloat(cs.fontSize) === 0) {
        skipped += 1;                      // invisible: counted, not listed
        continue;
      }

      // Ancestor chain, innermost first, always to the root: every element in
      // it is an ancestor of the text, so each can affect how it is painted.
      var chain = [];
      for (var walker = el; walker && walker.nodeType === 1; walker = walker.parentElement) {
        chain.push(walker);
      }

      // First background with alpha > 0. An unparsed color format (oklch etc.)
      // counts as opaque; the raw string goes to Python, which parses it.
      var bgIndex = -1;
      for (var bi = 0; bi < chain.length; bi++) {
        var c = channelsOf(styleOf(chain[bi]).backgroundColor);
        if ((c ? c.a : 1) > 0) { bgIndex = bi; break; }
      }

      // A gradient/image is only visible over the resolved color while it sits
      // at or in front of it; behind an opaque background it cannot matter.
      var method = null, evidence = null;
      var gradientLimit = bgIndex < 0 ? chain.length : bgIndex + 1;
      for (var gi = 0; gi < gradientLimit; gi++) {
        var image = styleOf(chain[gi]).backgroundImage;
        if (image && image !== "none") {
          method = "uncertain:gradient-or-image";
          evidence = image;
          break;
        }
      }

      // Opacity < 1 composites the whole subtree; blend/filter change what is
      // really painted anywhere in the chain — full-chain scan on purpose.
      if (!method) {
        for (var fi = 0; fi < chain.length; fi++) {
          var fs = styleOf(chain[fi]);
          var why = null;
          if (parseFloat(fs.opacity) < 1) why = "opacity=" + fs.opacity;
          else if (fs.mixBlendMode && fs.mixBlendMode !== "normal") why = "mix-blend-mode=" + fs.mixBlendMode;
          else if (fs.filter && fs.filter !== "none") why = "filter=" + fs.filter;
          if (why) {
            method = "uncertain:blend-or-filter";
            evidence = tagOf(chain[fi]) + " " + why;
            break;
          }
        }
      }

      if (!method) {
        for (var ci = 0; ci < covers.length; ci++) {
          var cover = covers[ci];
          if (cover.el.contains(el)) continue;  // own container is not a cover
          if (rect.left < cover.x + cover.w && rect.right > cover.x
              && rect.top < cover.y + cover.h && rect.bottom > cover.y) {
            method = "uncertain:occluded";
            evidence = tagOf(cover.el);
            break;
          }
        }
      }

      var bg = null;
      if (!method) {
        if (bgIndex < 0) {
          method = "assumed-canvas";
          bg = canvas;
        } else {
          method = "resolved";
          var raw = styleOf(chain[bgIndex]).backgroundColor;
          var top = channelsOf(raw);
          if (!top || top.a >= 1) {
            bg = raw;                     // opaque, or an exotic format for Python
          } else {
            // Semi-transparent first, then compute: composite the translucent
            // layers over what is behind them, canvas last.
            var acc = channelsOf(canvas);
            for (var li = chain.length - 1; li >= bgIndex; li--) {
              var layer = channelsOf(styleOf(chain[li]).backgroundColor);
              if (layer && layer.a > 0) acc = over(layer, acc);
            }
            bg = rgbString(acc);
          }
        }
      }

      var fg = cs.color;
      var fgC = channelsOf(fg);
      if (fgC && fgC.a < 1) {
        var bgC = channelsOf(bg);
        if (bgC) fg = rgbString(over(fgC, bgC));  // translucent text: composite first
      }

      rows.push({
        method: method,
        fg: fg,
        bg: bg,
        font_size: parseFloat(cs.fontSize),
        font_weight: parseFloat(cs.fontWeight) || 0,
        rect: { x: Math.round(rect.left * 10) / 10, y: Math.round(rect.top * 10) / 10,
                width: Math.round(rect.width * 10) / 10,
                height: Math.round(rect.height * 10) / 10 },
        text: text.slice(0, SNIPPET),
        tag: tagOf(el),
        evidence: evidence
      });
    }

    return {
      color_scheme: dark ? "dark" : "light",
      canvas: canvas,
      rows: rows,
      skipped: skipped,
      capped: capped,
      limit: MAX_ROWS
    };
  }

  function styleOf(el) {
    return getComputedStyle(el);
  }

  function channelsOf(value) {
    // rgb()/rgba() (comma or space syntax) and #hex, so the canvas constant
    // composes; anything else returns null and the raw string travels on.
    var m = /^#([0-9a-f]{6})$/i.exec(value);
    if (m) {
      var h = m[1];
      return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16),
               b: parseInt(h.slice(4, 6), 16), a: 1 };
    }
    m = /^rgba?\(([^)]*)\)$/i.exec(value);
    if (m) {
      var parts = m[1].split(/[,\s\/]+/).filter(function (p) { return p.length > 0; });
      if (parts.length < 3) return null;
      var nums = [];
      for (var i = 0; i < 3; i++) {
        var v = parseFloat(parts[i]);
        if (isNaN(v)) return null;
        nums.push(v);
      }
      var a = 1;
      if (parts.length > 3) {
        a = parseFloat(parts[3]);
        if (isNaN(a)) a = 1;
      }
      return { r: nums[0], g: nums[1], b: nums[2], a: a };
    }
    return null;
  }

  function over(top, bottom) {
    // top painted over an opaque bottom (canvas-resolved chains only).
    return {
      r: top.r * top.a + bottom.r * (1 - top.a),
      g: top.g * top.a + bottom.g * (1 - top.a),
      b: top.b * top.a + bottom.b * (1 - top.a),
      a: 1
    };
  }

  function rgbString(c) {
    return "rgb(" + Math.round(c.r) + ", " + Math.round(c.g) + ", " + Math.round(c.b) + ")";
  }

  function tagOf(el) {
    var cls = typeof el.className === "string" ? el.className.trim().split(/\s+/)[0] : "";
    return cls ? el.tagName.toLowerCase() + "." + cls : el.tagName.toLowerCase();
  }
})()"""


# --- pure logic (no browser; the collector payload is plain dicts) ----------


def threshold_for(row):
    """AA large text (3.0) at >= 24px or >= 18.66px bold; else 4.5."""
    size = float(row.get("font_size") or 0)
    weight = float(row.get("font_weight") or 0)
    if size >= LARGE_SIZE or (size >= LARGE_BOLD_SIZE and weight >= BOLD_WEIGHT):
        return wcag.AA_LARGE_OR_UI
    return wcag.AA_TEXT


def verdict(row):
    """Verdict dict for one measurable row; None for uncertain methods.

    Raises ValueError (from wcag.parse_color / contrast_ratio) when a color
    cannot be parsed; classify_rows turns that into "uncertain:unparseable".
    """
    if str(row.get("method", "")).startswith("uncertain:"):
        return None
    ratio = wcag.contrast_ratio(row["fg"], row["bg"])
    threshold = threshold_for(row)
    return {
        "ratio": round(ratio, 2),
        "threshold": threshold,
        "verdict": "pass" if ratio >= threshold else "FAIL",
    }


def classify_rows(rows, skipped_count=0):
    """Split collector rows into (verdicts, uncertain, skipped_count).

    "resolved" and "assumed-canvas" rows get verdicts; anything starting
    "uncertain:" is listed verbatim and never verdicted; unparseable colors
    become "uncertain:unparseable" instead of crashing; rows marked "skipped"
    (and the browser-side skipped count) only raise the count.
    """
    verdicts, uncertain = [], []
    for row in rows:
        method = str(row.get("method", ""))
        if method == "skipped":
            skipped_count += 1
            continue
        if method in ("resolved", "assumed-canvas"):
            try:
                result = verdict(row)
            except (ValueError, KeyError) as exc:  # unknown color or missing field
                bad = dict(row, method="uncertain:unparseable", evidence=str(exc))
                uncertain.append(bad)
                continue
            verdicts.append(dict(row, **result))
        else:
            uncertain.append(row)
    return verdicts, uncertain, skipped_count


def build_report(url, payload):
    """Full report dict from one collector payload (real or synthetic)."""
    verdicts, uncertain, skipped = classify_rows(
        payload.get("rows", []), payload.get("skipped", 0))
    fails = [row for row in verdicts if row["verdict"] == "FAIL"]
    passes = [row for row in verdicts if row["verdict"] != "FAIL"]
    scheme = payload.get("color_scheme", "light")
    canvas = payload.get("canvas", "#ffffff")
    summary = {
        "checked": len(verdicts) + len(uncertain),
        "pass": len(passes),
        "fail": len(fails),
        "uncertain": len(uncertain),
        "skipped": skipped,
        "assumed_canvas": sum(1 for row in verdicts if row["method"] == "assumed-canvas"),
        "capped": bool(payload.get("capped")),
    }
    if summary["capped"]:
        summary["limit"] = payload.get("limit", MAX_ROWS)
    return {
        "url": url,
        "verified": True,
        "color_scheme": scheme,
        "canvas_assumption": CANVAS_ASSUMPTION.format(scheme=scheme, canvas=canvas),
        # FAIL pairs first, then passes, then the uncertain list.
        "results": fails + passes + uncertain,
        "summary": summary,
    }


def render_text(report):
    """Human report: FAIL pairs, then the uncertain list, then the summary."""
    lines = [
        f"Page contrast audit: {report['url']}",
        f"Canvas assumption: {report['canvas_assumption']}",
    ]
    for row in report["results"]:
        if row.get("verdict") == "FAIL":
            rect = row["rect"]
            lines.append(
                f"FAIL {row['fg']} on {row['bg']} {row['ratio']:.2f}:1 "
                f"(needs {row['threshold']:.2f} for {row['font_size']:g}px"
                f"/{row['font_weight']:g}) \"{row['text']}\" {row['tag']} "
                f"rect ({rect['x']:g}, {rect['y']:g}) {rect['width']:g}x{rect['height']:g}"
            )
    for row in report["results"]:
        method = str(row.get("method", ""))
        if method.startswith("uncertain:"):
            line = f"UNCERTAIN {method} \"{row['text']}\" {row['tag']}"
            if row.get("evidence"):
                line += f" [{row['evidence']}]"
            lines.append(line)
    summary = report["summary"]
    tail = (f"checked {summary['checked']} text pairs: {summary['pass']} pass, "
            f"{summary['fail']} fail, {summary['uncertain']} uncertain, "
            f"{summary['skipped']} skipped ({summary['assumed_canvas']} assumed canvas)")
    if summary.get("capped"):
        tail += f" [capped at {summary.get('limit', MAX_ROWS)} entries]"
    lines.append(tail)
    return "\n".join(lines)


# --- browser path (raises on any failure; main() reports "claims nothing") --


def _evaluate_collector(session, session_id, limit):
    """Run the collector once the page has settled (load + fonts.ready)."""
    expression = (
        "(async () => {"
        "try { if (document.fonts && document.fonts.ready) await document.fonts.ready; }"
        " catch (e) {}"
        "return " + COLLECTOR_JS.replace("__MAX_ROWS__", str(max(1, limit))) + ";"
        "})()"
    )
    result = session.send(
        "Runtime.evaluate",
        {"expression": expression, "returnByValue": True, "awaitPromise": True},
        session=session_id,
    )
    value = result["result"].get("value")
    if not isinstance(value, str):
        raise cdp.BrowserError("collector returned no data (evaluation blocked?)")
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise cdp.BrowserError("collector returned unexpected data")
    if payload.get("error"):
        raise cdp.BrowserError(f"collector failed on the page: {payload['error']}")
    return payload


def audit_url(url, limit=MAX_ROWS):
    """Launch one browser, navigate, collect rows; return the payload.

    Raises on any failure (no browser, CDP trouble, collector error) so main()
    can print {"verified": false} and claim nothing about the page.
    """
    browser = visual_capture.find_browser()
    if not browser:
        raise cdp.BrowserError(
            "no Chromium-family browser found at an absolute path; page audit disabled")
    process = profile = connection = session = target_id = None
    try:
        process, profile, ws_url = visual_capture._start_cdp_browser(browser)  # noqa: SLF001 - documented sibling reuse
        connection = cdp.Connection(ws_url)
        session = cdp.Session(connection)
        target_id = session.send("Target.createTarget", {"url": "about:blank"})["targetId"]
        session_id = session.send(
            "Target.attachToTarget", {"targetId": target_id, "flatten": True}
        )["sessionId"]
        for domain in ("Page", "Runtime"):
            session.send(domain + ".enable", session=session_id)
        session.send("Page.navigate", {"url": url}, session=session_id)
        if cdp.wait_for_event(
            session, "Page.loadEventFired", LOAD_TIMEOUT,
            match=lambda message: message.get("sessionId") == session_id,
        ) is None:
            raise cdp.BrowserError(f"page did not fire load within {LOAD_TIMEOUT:g}s")
        return _evaluate_collector(session, session_id, limit)
    finally:
        if session is not None and target_id is not None:
            try:
                session.send("Target.closeTarget", {"targetId": target_id}, timeout=3)
            except Exception:
                pass
        if session is not None:
            try:
                session.send("Browser.close", timeout=3)
            except Exception:
                pass
        if connection is not None:
            connection.close()
        if process is not None:
            process.terminate()
        if profile is not None:
            shutil.rmtree(profile, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rendered-page WCAG contrast audit over CDP.")
    parser.add_argument("url")
    parser.add_argument("--json", action="store_true", help="print the JSON report instead of text")
    parser.add_argument("--allow-private", action="store_true",
                        help="allow non-public, non-loopback addresses")
    parser.add_argument("--limit", type=int, default=MAX_ROWS,
                        help=f"max text rows to collect (default {MAX_ROWS})")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        url = visual_capture.validate_url(args.url, allow_private=args.allow_private)
    except visual_capture.UrlRejected as exc:
        print(json.dumps({"verified": False, "reason": f"URL rejected: {exc}"}, ensure_ascii=False))
        return 3

    try:
        payload = audit_url(url, limit=args.limit)
    except Exception as exc:  # noqa: BLE001 - the documented "claims nothing" contract
        print(json.dumps({
            "verified": False,
            "reason": f"no audit performed: {type(exc).__name__}: {exc}",
        }, ensure_ascii=False))
        return 2

    report = build_report(url, payload)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    return 1 if report["summary"]["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
