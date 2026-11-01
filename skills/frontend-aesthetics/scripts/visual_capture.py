"""Capture UI screenshots with a Chromium-family browser, headless.

Usage:
  python visual_capture.py URL --out DIR [--width 1440] [--height 900]
                               [--theme dark] [--scale 1] [--name default]
  python visual_capture.py URL --out DIR --matrix [--allow-private]

Prints one JSON object with the captures, console lines and the browser path.
Exit status 2 when no browser is available, 3 when the URL is rejected.

Design notes (learned from a real capture run):
- Wait for a readiness signal, never a fixed sleep. A 4s virtual-time budget
  captured a blank frame of a real app; 8s captured the same view correctly.
- Never resolve the browser by bare name. On Windows the executable search
  order favours the current directory and the application folder, which turns
  a capture into arbitrary code execution. Only absolute paths under Program
  Files or /usr/bin are accepted; a miss disables the feature.
- The URL is untrusted input to argv. Validate the scheme and refuse a leading
  "-" so it cannot be parsed as a browser switch, and require an explicit flag
  before navigating to a private (non-loopback) address.
- Read-only: writes PNGs only into --out.
"""

import argparse
import ipaddress
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

sys.dont_write_bytecode = True
import image_diff  # noqa: E402  (sibling module; no third-party dependencies)

WINDOWS_CANDIDATES = (
    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
    r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
    r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
)
POSIX_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/microsoft-edge",
)
MIN_READY_TEXT = 200
MAX_WAIT_SECONDS = 20
# Two consecutive identical frames are considered settled; this many rounds max.
STABLE_ATTEMPTS = 4
# A rendered page has many anti-aliased shades; a bare shell has very few.
MIN_RENDERED_COLORS = 400


class UrlRejected(ValueError):
    pass


def find_browser():
    """Return an absolute path to a Chromium-family browser, or None."""
    if os.name == "nt":
        for path in WINDOWS_CANDIDATES:
            expanded = os.path.expandvars(path)
            if Path(expanded).is_file():
                return str(Path(expanded).resolve())
        return None
    for path in POSIX_CANDIDATES:
        if Path(path).is_file():
            return path
    for name in ("google-chrome", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found and Path(found).is_absolute():
            return found
    return None


def _addresses(host):
    try:
        return {ipaddress.ip_address(host)}
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as exc:
        raise UrlRejected(f"cannot resolve host {host!r}: {exc}") from exc
    return {ipaddress.ip_address(info[4][0]) for info in infos}


def validate_url(url, allow_private=False):
    """Reject non-http(s) schemes, option-like strings and private targets."""
    if url.startswith("-"):
        raise UrlRejected("URL must not start with '-' (it would be parsed as a browser switch)")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UrlRejected(f"only http and https are allowed, got {parsed.scheme or 'no scheme'!r}")
    host = parsed.hostname
    if not host:
        raise UrlRejected("URL has no host")
    for address in _addresses(host):
        if address.is_loopback:
            continue  # the tool's purpose: a local preview server
        if address.is_private or address.is_link_local or address.is_reserved or address.is_multicast:
            if not allow_private:
                raise UrlRejected(
                    f"{host} resolves to the non-public address {address}; "
                    "pass --allow-private to capture it"
                )
    return url


def _base_command(browser, profile_dir, width, height, scale):
    return [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-proxy-server",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        f"--user-data-dir={profile_dir}",
        f"--window-size={width},{height}",
        f"--force-device-scale-factor={scale}",
    ]


def _run(command):
    return subprocess.run(  # noqa: S603 - fixed absolute browser path, list form, no shell
        command,
        shell=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )


def _dom_and_console(browser, profile_dir, url, budget_ms):
    command = _base_command(browser, profile_dir, 1280, 800, 1) + [
        "--enable-logging=stderr",
        "--v=0",
        "--dump-dom",
        f"--virtual-time-budget={budget_ms}",
        url,
    ]
    result = _run(command)
    console = []
    for line in result.stderr.splitlines():
        if "CONSOLE" in line:
            message = line.split("CONSOLE", 1)[-1].lstrip(":)d ")
            console.append(message.strip())
    errors = [line for line in console if "error" in line.lower() or "uncaught" in line.lower()]
    return result.stdout, console, errors


def wait_for_render(browser, profile_dir, url, budget_ms):
    """Grow the virtual-time budget until the DOM has real content."""
    budget = budget_ms
    while True:
        dom, console, errors = _dom_and_console(browser, profile_dir, url, budget)
        if len(" ".join(dom.split())) >= MIN_READY_TEXT or budget >= MAX_WAIT_SECONDS * 1000:
            return dom, errors, budget
        budget = min(budget * 2, MAX_WAIT_SECONDS * 1000)


def _shoot(browser, profile, url, width, height, scale, budget, target):
    command = _base_command(browser, profile, width, height, scale) + [
        f"--virtual-time-budget={budget}",
        f"--screenshot={target}",
        url,
    ]
    _run(command)
    return Path(target).exists()


def capture(browser, url, out_dir, name, width, height, scale, theme, budget_ms):
    """Capture one view, retrying until two consecutive frames agree.

    A single shot is not trustworthy: on a real app a slower first paint
    produced a half-rendered shell at one window size while the same page was
    complete at another. Two identical frames mean the view has settled.
    """
    profile = Path(tempfile.mkdtemp(prefix="fa-profile-"))
    target = Path(out_dir) / f"{name}-{width}x{height}-{theme}@{scale:g}.png"
    first = target.with_suffix(".a.png")
    second = target.with_suffix(".b.png")
    target.parent.mkdir(parents=True, exist_ok=True)
    settled = False
    budget = budget_ms
    attempts = 0
    try:
        dom, errors, budget = wait_for_render(browser, profile, url, budget)
        while attempts < STABLE_ATTEMPTS:
            attempts += 1
            if not (_shoot(browser, profile, url, width, height, scale, budget, first)
                    and _shoot(browser, profile, url, width, height, scale, budget, second)):
                budget = min(int(budget * 1.5), MAX_WAIT_SECONDS * 1000)
                continue
            comparison = image_diff.diff(first, second)
            if comparison.get("comparable") and comparison["identical"]:
                settled = True
                break
            budget = min(int(budget * 1.5), MAX_WAIT_SECONDS * 1000)

        source = second if second.exists() else first
        if source.exists():
            source.replace(target)
        if target.exists():
            summary = image_diff.stats(target)
            blank = summary["distinct_colors_sampled"] < MIN_RENDERED_COLORS
        else:
            summary, blank = {"distinct_colors_sampled": 0}, True
        return {
            "file": str(target),
            "bytes": target.stat().st_size if target.exists() else 0,
            "dom_chars": len(" ".join(dom.split())),
            "distinct_colors": summary["distinct_colors_sampled"],
            "settled": settled,
            "attempts": attempts,
            "virtual_time_budget_ms": budget,
            "console_errors": errors,
            "blank": blank,
        }
    finally:
        for leftover in (first, second):
            leftover.unlink(missing_ok=True)
        shutil.rmtree(profile, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Headless UI screenshots for design review.")
    parser.add_argument("url")
    parser.add_argument("--out", required=True)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--scale", type=float, default=1)
    parser.add_argument("--theme", default="light", help="recorded in the filename only")
    parser.add_argument("--name", default="view")
    parser.add_argument("--budget", type=int, default=4000, help="initial virtual time in ms")
    parser.add_argument("--matrix", action="store_true", help="capture the standard set of sizes")
    parser.add_argument("--allow-private", action="store_true",
                        help="allow non-public, non-loopback addresses")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        url = validate_url(args.url, allow_private=args.allow_private)
    except UrlRejected as exc:
        print(json.dumps({"ok": False, "reason": f"URL rejected: {exc}"}, ensure_ascii=False))
        return 3

    browser = find_browser()
    if not browser:
        print(json.dumps({
            "ok": False,
            "reason": "no Chromium-family browser found at an absolute path; visual capture disabled",
        }, ensure_ascii=False))
        return 2

    if args.matrix:
        plan = [
            ("wide", 1440, 900, 1),
            ("wide-scaled", 1440, 900, 1.5),
            ("narrow", 1100, 720, 1),
            ("phone", 390, 844, 1),
        ]
    else:
        plan = [(args.name, args.width, args.height, args.scale)]

    results = [
        capture(browser, url, args.out, name, width, height, scale, args.theme, args.budget)
        for name, width, height, scale in plan
    ]
    print(json.dumps({
        "ok": True,
        "browser": browser,
        "captures": results,
        "blank_frames": any(item["blank"] for item in results),
        "console_errors": any(item["console_errors"] for item in results),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
