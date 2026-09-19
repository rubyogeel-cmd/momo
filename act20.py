#!/usr/bin/env python3
"""act20.py - Single-phone preview + drop diagnostic button.

Two changes:
  1. preview.html is rewritten as a single-phone preview with a small
     tab bar (Status / Plans / Checkout / SMS). Default is Status.
     Only one iframe is loaded at any time.
  2. The "Run Diagnostic Test" outline button is removed from the
     Status page, since production will not offer it.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME = Path(__file__).name
TIMESTEP = 20

COMMIT_MESSAGE = """act20: single-phone preview, drop diagnostic button

Rewrites preview.html as a single-phone preview with a tab strip
(Status / Plans / Checkout / SMS) defaulting to Status, so only one
page loads at a time. Removes the Run Diagnostic Test button from
the Status page."""


PREVIEW_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Momo preview</title>
  <style>
    * { box-sizing: border-box; }
    html, body {
      margin: 0;
      height: 100%;
      background: #0b0f19;
      color: #e6e8ee;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                   Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    .layout {
      display: flex;
      flex-direction: column;
      height: 100vh;
    }
    header {
      padding: 12px 20px;
      border-bottom: 1px solid #1e2438;
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }
    header h1 {
      margin: 0;
      font-size: 14px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #8a91a4;
      font-weight: 600;
    }
    .tabs {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .tab {
      padding: 6px 14px;
      border-radius: 999px;
      border: 1px solid #1e2438;
      background: transparent;
      color: #cbd5e1;
      font: inherit;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }
    .tab:hover {
      border-color: #2f3a55;
    }
    .tab[aria-selected="true"] {
      background: #1e5af6;
      border-color: #1e5af6;
      color: #ffffff;
    }
    .stage {
      flex: 1 1 auto;
      display: flex;
      justify-content: center;
      align-items: stretch;
      padding: 16px;
      min-height: 0;
    }
    .phone {
      width: 100%;
      max-width: 420px;
      background: #000;
      border-radius: 24px;
      overflow: hidden;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
      display: flex;
    }
    .phone iframe {
      width: 100%;
      height: 100%;
      border: 0;
      background: #f5f5f7;
      display: block;
    }
  </style>
</head>
<body>
  <div class="layout">
    <header>
      <h1>Momo preview</h1>
      <nav class="tabs" role="tablist" aria-label="Preview pages">
        <button class="tab" role="tab" data-src="web/index.html"
                aria-selected="true">Status</button>
        <button class="tab" role="tab" data-src="web/plans.html"
                aria-selected="false">Plans</button>
        <button class="tab" role="tab"
                data-src="web/checkout.html?plan=premium"
                aria-selected="false">Checkout</button>
        <button class="tab" role="tab"
                data-src="web/sms.html?plan=premium&amp;phone=079764645"
                aria-selected="false">SMS</button>
      </nav>
    </header>
    <div class="stage">
      <div class="phone">
        <iframe id="frame" src="web/index.html" title="Momo preview"></iframe>
      </div>
    </div>
  </div>

  <script>
    (function () {
      var tabs = document.querySelectorAll(".tab");
      var frame = document.getElementById("frame");
      tabs.forEach(function (tab) {
        tab.addEventListener("click", function () {
          tabs.forEach(function (other) {
            other.setAttribute("aria-selected", "false");
          });
          tab.setAttribute("aria-selected", "true");
          frame.src = tab.dataset.src;
        });
      });
    })();
  </script>
</body>
</html>
"""


DIAGNOSTIC_BLOCK = """\
      <!-- Diagnostic -->
      <button type="button" class="btn btn--outline">
        <svg class="btn__icon" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M4 22h16"/>
          <path d="m10 2 6 12h-8l6 8" transform="translate(-2,0)"/>
        </svg>
        <span>Run Diagnostic Test</span>
      </button>

"""

LOGGER = logging.getLogger(SCRIPT_NAME)


def project_root() -> Path:
    """Return the directory containing this script."""
    return Path(__file__).resolve().parent


def read_text(path: Path) -> str:
    """Return UTF-8 text, or '' if the file does not exist."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 with LF endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def remove_block(path: Path, block: str) -> str:
    """Remove *block* from *path* once. Return a short status."""
    text = read_text(path)
    if not text:
        return "missing-file"
    if block not in text:
        return "already"
    write_text(path, text.replace(block, "", 1))
    return "removed"


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
    """Apply the two edits and commit."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout
    )
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    preview = root / "preview.html"
    write_text(preview, PREVIEW_HTML)
    LOGGER.info("[written] %s", preview.relative_to(root))

    index_html = root / "web" / "index.html"
    LOGGER.info("[%s] %s (diagnostic button)",
                remove_block(index_html, DIAGNOSTIC_BLOCK),
                index_html.relative_to(root))

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
    LOGGER.info("")
    LOGGER.info("Hard-refresh http://127.0.0.1:8000/preview.html")
    LOGGER.info("%s - done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())