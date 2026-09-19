#!/usr/bin/env python3
"""act11.py - Timestep 11: preview, README, cross-links.

Writes ``preview.html`` at the project root: a single self-contained
page that embeds all four site screens side by side in phone-sized
iframes so the whole flow can be walked in Chrome.

Also refreshes ``README.md`` with the final page map and the exact
command to open the preview.

Side effects
------------
* Creates preview.html.
* Rewrites README.md.
* Commits the result with a descriptive message.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME: str = Path(__file__).name
TIMESTEP: int = 11

COMMIT_MESSAGE: str = (
    "act11: add preview and refresh readme\n"
    "\n"
    "Adds preview.html at the project root - a single page that embeds\n"
    "all four site screens (status, plans, momo gateway, sms\n"
    "verification) as side-by-side phone-sized iframes for Chrome\n"
    "review. Refreshes README.md with the final page map."
)

PREVIEW_HTML: str = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Momo preview - all four screens</title>
  <style>
    :root {
      --bg:      #10131a;
      --surface: #1a1e28;
      --border:  #2a2f3d;
      --text:    #e6e8ee;
      --muted:   #8a91a4;
      --accent:  #1e5af6;
    }
    * { box-sizing: border-box; }
    html, body {
      margin: 0;
      padding: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                   Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    header.top {
      padding: 20px 28px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: baseline;
      gap: 16px;
    }
    header.top h1 {
      margin: 0;
      font-size: 18px;
      letter-spacing: 0.02em;
    }
    header.top span.hint {
      color: var(--muted);
      font-size: 13px;
    }
    .frames {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 20px;
      padding: 24px 28px 40px;
      align-items: start;
    }
    @media (max-width: 1200px) {
      .frames { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 680px) {
      .frames { grid-template-columns: 1fr; }
    }
    .frame {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      min-width: 0;
    }
    .frame__head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
    }
    .frame__label {
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }
    .frame__title {
      font-size: 14px;
      font-weight: 600;
    }
    .frame__route {
      font-size: 12px;
      color: var(--muted);
      margin-top: 2px;
    }
    .frame__open {
      color: var(--accent);
      font-size: 12px;
      font-weight: 600;
      text-decoration: none;
      padding: 6px 10px;
      border: 1px solid var(--border);
      border-radius: 8px;
    }
    .frame__open:hover {
      background: rgba(30, 90, 246, 0.12);
    }
    .frame__viewport {
      position: relative;
      height: 720px;
      background: #000;
    }
    .frame__viewport iframe {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      border: 0;
    }
  </style>
</head>
<body>

  <header class="top">
    <h1>Momo preview</h1>
    <span class="hint">
      Four screens of the Starlink Zambia reseller flow.
      Interact directly inside each frame.
    </span>
  </header>

  <section class="frames">

    <article class="frame">
      <div class="frame__head">
        <div>
          <div class="frame__title">Status</div>
          <div class="frame__route">web/index.html</div>
        </div>
        <a class="frame__open" href="web/index.html" target="_blank" rel="noopener">
          Open
        </a>
      </div>
      <div class="frame__viewport">
        <iframe src="web/index.html" title="Status page" loading="lazy"></iframe>
      </div>
    </article>

    <article class="frame">
      <div class="frame__head">
        <div>
          <div class="frame__title">Plans</div>
          <div class="frame__route">web/plans.html</div>
        </div>
        <a class="frame__open" href="web/plans.html" target="_blank" rel="noopener">
          Open
        </a>
      </div>
      <div class="frame__viewport">
        <iframe src="web/plans.html" title="Plans page" loading="lazy"></iframe>
      </div>
    </article>

    <article class="frame">
      <div class="frame__head">
        <div>
          <div class="frame__title">MTN MoMo gateway</div>
          <div class="frame__route">web/checkout.html</div>
        </div>
        <a class="frame__open" href="web/checkout.html?plan=premium"
           target="_blank" rel="noopener">
          Open
        </a>
      </div>
      <div class="frame__viewport">
        <iframe src="web/checkout.html?plan=premium"
                title="MoMo gateway page" loading="lazy"></iframe>
      </div>
    </article>

    <article class="frame">
      <div class="frame__head">
        <div>
          <div class="frame__title">Full SMS verification</div>
          <div class="frame__route">web/sms.html</div>
        </div>
        <a class="frame__open"
           href="web/sms.html?plan=premium&phone=079764645"
           target="_blank" rel="noopener">
          Open
        </a>
      </div>
      <div class="frame__viewport">
        <iframe src="web/sms.html?plan=premium&phone=079764645"
                title="SMS verification page" loading="lazy"></iframe>
      </div>
    </article>

  </section>

</body>
</html>
"""

README: str = """\
# Momo

Mobile-first web experience for the Starlink Zambia data reseller
flow: choose a plan, pay via MTN MoMo, verify by SMS.

## Quick start

Open the preview to see all four screens side by side:

    start preview.html           # Windows
    open preview.html            # macOS
    xdg-open preview.html        # Linux

Or open any screen directly:

    web/index.html               Status dashboard
    web/plans.html               Plan catalogue
    web/checkout.html?plan=premium
    web/sms.html?plan=premium&phone=079764645

No build step. No bundler. No runtime dependencies.

## Pages

    1.  /status      Status dashboard          web/index.html
    2.  /plans       Plan catalogue            web/plans.html
    3.  /checkout    MTN MoMo gateway          web/checkout.html
    4.  /sms         Full SMS verification     web/sms.html

Between pages 2 and 3, tapping a plan card shows a ~5 s MoMo
redirect loader before navigating.

## Layout

    preview.html       Four-screen viewer for Chrome
    web/               Static site
      index.html       Status dashboard
      plans.html       Plan catalogue
      checkout.html    MoMo gateway
      sms.html         SMS verification
      assets/
        css/           tokens, base, components
        js/
          data/        plans.js, copy.js
          pages/       one module per page
    tests/             Test suite (added in a later act)
    docs/              Architecture notes
    config/            Project-wide configuration
    scripts/           Developer tooling

## How changes are made

The site is built up across numbered timestep scripts
(``act1.py``, ``act2.py``, ...). Each script does one incremental
change and commits itself with a descriptive message, so
``git reflog -a`` is a replayable log of how the project was built.
"""

LOGGER = logging.getLogger(SCRIPT_NAME)


def project_root() -> Path:
    """Return the directory containing this script."""
    return Path(__file__).resolve().parent


def write_file(path: Path, content: str) -> bool:
    """Write *content* to *path* if it differs. Return True if changed."""
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in *root*; never raises. Decodes output as UTF-8."""
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def main() -> int:
    """Write preview.html, refresh README, commit."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    targets = {
        root / "preview.html": PREVIEW_HTML,
        root / "README.md": README,
    }
    for path, content in targets.items():
        changed = write_file(path, content)
        marker = "written" if changed else "unchanged"
        LOGGER.info("[%s] %s", marker, path.relative_to(root))

    add = run_git(root, "add", "-A")
    if add.returncode != 0:
        LOGGER.error("git add failed: %s", add.stderr.strip())
        return 1

    commit = run_git(root, "commit", "-m", COMMIT_MESSAGE)
    if commit.returncode != 0:
        LOGGER.error("git commit failed: %s", commit.stderr.strip())
        return 1

    head = run_git(root, "log", "-n", "1", "--oneline")
    LOGGER.info("HEAD is now: %s", head.stdout.strip())
    LOGGER.info("%s - done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())