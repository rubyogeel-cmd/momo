#!/usr/bin/env python3
"""act3.py — Timestep 3: design tokens.

Writes ``web/assets/css/tokens.css``, the single source of truth for
every colour, radius, spacing, type size and motion value used by the
rest of the site. Later CSS files must reference these custom
properties and never declare raw hex values of their own.

Side effects
------------
* Creates/overwrites ``web/assets/css/tokens.css``.
* Commits the result with a descriptive message.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME: str = Path(__file__).name
TIMESTEP: int = 3

COMMIT_MESSAGE: str = (
    "act3: add design tokens\n"
    "\n"
    "Adds web/assets/css/tokens.css \u2014 the project's single source of\n"
    "truth for colour, typography, spacing, radii, shadows and motion.\n"
    "Values are derived from the Starlink Zambia reference screenshots\n"
    "captured across pages 1\u20134."
)

TOKENS_CSS: str = """\
/* ==========================================================================
   Design tokens
   Single source of truth for every visual constant in the site.
   Later CSS files MUST reference these variables \u2014 no raw hex values.
   ========================================================================== */

:root {
  /* ---------- Brand ---------- */
  --color-brand-blue:        #1e5af6;
  --color-brand-blue-dark:   #1744c2;
  --color-brand-yellow:      #fdc500;
  --color-brand-yellow-soft: #ffd54f;
  --color-brand-yellow-deep: #e0a800;
  --color-brand-orange:      #fb8500;
  --color-brand-orange-dark: #d96f00;

  /* ---------- Surfaces ---------- */
  --color-bg:            #f5f5f7;
  --color-surface:       #ffffff;
  --color-surface-muted: #f2f4f7;
  --color-top-bar:       #000000;
  --color-scrim:         rgba(0, 0, 0, 0.45);

  /* ---------- Text ---------- */
  --color-text-primary:   #0b0f19;
  --color-text-secondary: #6b7280;
  --color-text-muted:     #9ca3af;
  --color-text-inverse:   #ffffff;

  /* ---------- Accents ---------- */
  --color-accent-blue:  #2563eb;
  --color-accent-green: #16a34a;
  --color-accent-red:   #dc2626;

  /* ---------- Warning callout ---------- */
  --color-warn-bg:     #fef3c7;
  --color-warn-border: #f59e0b;
  --color-warn-text:   #b45309;

  /* ---------- Pills / chips ---------- */
  --color-pill-bg:   #dbe6ff;
  --color-pill-text: #1e40af;

  /* ---------- Borders ---------- */
  --color-border:        #e5e7eb;
  --color-border-strong: #d1d5db;

  /* ---------- Progress ---------- */
  --color-progress-track: #e5e7eb;
  --color-progress-fill:  #2563eb;

  /* ---------- Bottom navigation ---------- */
  --color-nav-active:   var(--color-accent-blue);
  --color-nav-inactive: #6b7280;

  /* ---------- Radii ---------- */
  --radius-sm:   8px;
  --radius-md:   12px;
  --radius-lg:   16px;
  --radius-xl:   20px;
  --radius-pill: 999px;

  /* ---------- Spacing (4px scale) ---------- */
  --space-1:  4px;
  --space-2:  8px;
  --space-3:  12px;
  --space-4:  16px;
  --space-5:  20px;
  --space-6:  24px;
  --space-8:  32px;
  --space-10: 40px;

  /* ---------- Typography ---------- */
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               "Helvetica Neue", Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;

  --text-xs:     11px;
  --text-sm:     13px;
  --text-base:   15px;
  --text-md:     16px;
  --text-lg:     18px;
  --text-xl:     22px;
  --text-2xl:    28px;
  --text-metric: 32px;

  --weight-regular:  400;
  --weight-medium:   500;
  --weight-semibold: 600;
  --weight-bold:     700;

  --leading-tight:  1.15;
  --leading-snug:   1.3;
  --leading-normal: 1.5;

  --tracking-caps: 0.08em;

  /* ---------- Layout ---------- */
  --app-max-width:      480px;
  --top-bar-height:     56px;
  --bottom-nav-height:  64px;
  --page-padding:       var(--space-4);

  /* ---------- Shadows ---------- */
  --shadow-card: 0 1px 2px rgba(11, 15, 25, 0.04),
                 0 4px 12px rgba(11, 15, 25, 0.04);
  --shadow-button: 0 6px 16px rgba(30, 90, 246, 0.25);
  --shadow-modal: 0 20px 60px rgba(0, 0, 0, 0.25);

  /* ---------- Motion ---------- */
  --duration-fast:   120ms;
  --duration-base:   200ms;
  --duration-slow:   400ms;
  --duration-dwell:  5000ms;
  --ease-standard:   cubic-bezier(0.2, 0, 0, 1);
}
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
    """Run git in *root*; never raises."""
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )


def main() -> int:
    """Write tokens.css and commit."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    root = project_root()

    LOGGER.info("%s — timestep %d starting", SCRIPT_NAME, TIMESTEP)

    target = root / "web" / "assets" / "css" / "tokens.css"
    changed = write_file(target, TOKENS_CSS)
    LOGGER.info("[%s] %s", "written" if changed else "unchanged", target.relative_to(root))

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
    LOGGER.info("%s — done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())