#!/usr/bin/env python3
"""act12.py - Timestep 12: Starlink-style logo.

Writes ``web/assets/img/starlink.svg`` - a minimal Starlink-style
mark (elongated chevron over a horizontal line, light-on-transparent)
- and replaces the inline placeholder SVG in all four HTML pages with
a single ``<img>`` reference. Removes four duplicated copies of the
markup in favour of one asset (DRY).

Side effects
------------
* Creates web/assets/img/starlink.svg.
* Edits web/index.html, plans.html, checkout.html, sms.html in place.
* Commits the result with a descriptive message.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME: str = Path(__file__).name
TIMESTEP: int = 12

COMMIT_MESSAGE: str = (
    "act12: replace inline logo with starlink-style svg asset\n"
    "\n"
    "Adds web/assets/img/starlink.svg (elongated chevron above a\n"
    "horizontal line, light on transparent) and swaps the placeholder\n"
    "inline SVG in all four pages for a single <img> reference.\n"
    "Removes four duplicated copies of the markup."
)

STARLINK_SVG: str = """\
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 140 32"
     role="img"
     aria-label="Starlink">
  <title>Starlink</title>
  <g fill="#e8e8e8">
    <!-- Elongated chevron above -->
    <path d="M14 17 L70 5 L126 17 L70 11 Z"/>
    <!-- Horizontal base line -->
    <rect x="6" y="23" width="128" height="2.2" rx="1.1"/>
  </g>
</svg>
"""

# The exact block we ship in act7/8/9/10 - matched literally for a
# safe, deterministic replacement.
OLD_BLOCK: str = """\
      <svg class="app-top-bar__brand" viewBox="0 0 120 28" aria-label="Starlink">
        <rect x="0" y="4" width="120" height="20" rx="2" fill="#cfcfcf" opacity="0.85"/>
        <text x="60" y="19" text-anchor="middle"
              font-family="Arial, sans-serif" font-size="11" font-weight="700"
              letter-spacing="2" fill="#4a4a4a">STARLINK</text>
      </svg>"""

NEW_BLOCK: str = (
    '      <img class="app-top-bar__brand" '
    'src="assets/img/starlink.svg" alt="Starlink">'
)

TARGET_PAGES: tuple[str, ...] = (
    "web/index.html",
    "web/plans.html",
    "web/checkout.html",
    "web/sms.html",
)

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


def replace_in_file(path: Path, old: str, new: str) -> str:
    """Replace *old* with *new* in *path*.

    Returns one of: ``replaced``, ``already``, ``missing-file``,
    ``no-match``.
    """
    if not path.exists():
        return "missing-file"
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return "already"
        return "no-match"
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    return "replaced"


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
    """Write the SVG and swap the inline placeholders, then commit."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    svg_path = root / "web" / "assets" / "img" / "starlink.svg"
    svg_changed = write_file(svg_path, STARLINK_SVG)
    LOGGER.info("[%s] %s",
                "written" if svg_changed else "unchanged",
                svg_path.relative_to(root))

    for relative in TARGET_PAGES:
        page = root / relative
        outcome = replace_in_file(page, OLD_BLOCK, NEW_BLOCK)
        LOGGER.info("[%s] %s", outcome, relative)

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