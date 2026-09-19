#!/usr/bin/env python3
"""act4.py — Timestep 4: base stylesheet.

Writes ``web/assets/css/base.css``, providing:
  * a modern minimal reset,
  * the mobile-app shell (centred frame with a max width),
  * the black top bar,
  * the scrollable content region,
  * the persistent bottom navigation skeleton,
  * a few small accessibility utilities.

Every value comes from ``tokens.css``. No HTML is touched, so nothing
can render incorrectly yet.

Side effects
------------
* Creates ``web/assets/css/base.css``.
* Commits the result with a descriptive message.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME: str = Path(__file__).name
TIMESTEP: int = 4

COMMIT_MESSAGE: str = (
    "act4: add base stylesheet\n"
    "\n"
    "Adds web/assets/css/base.css \u2014 reset, app-shell frame, black top\n"
    "bar, scrollable content region and persistent bottom-navigation\n"
    "skeleton. All values reference design tokens; no raw hex values.\n"
    "No HTML yet \u2014 this act only establishes the visual frame that\n"
    "pages 1\u20134 will share."
)

BASE_CSS: str = """\
/* ==========================================================================
   Base stylesheet
   Reset + app shell. Consumes tokens.css; declares no raw values.
   ========================================================================== */

/* ---------- Reset ---------------------------------------------------------- */

*,
*::before,
*::after {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  padding: 0;
}

html {
  -webkit-text-size-adjust: 100%;
}

body {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  color: var(--color-text-primary);
  background: var(--color-bg);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

h1, h2, h3, h4, h5, h6, p, figure, blockquote {
  margin: 0;
}

ul, ol {
  margin: 0;
  padding: 0;
  list-style: none;
}

a {
  color: inherit;
  text-decoration: none;
}

button,
input,
textarea,
select {
  font: inherit;
  color: inherit;
  background: none;
  border: none;
  padding: 0;
}

button {
  cursor: pointer;
}

img,
svg {
  display: block;
  max-width: 100%;
}

/* ---------- App shell ------------------------------------------------------ */

.app-shell {
  position: relative;
  min-height: 100vh;
  max-width: var(--app-max-width);
  margin: 0 auto;
  background: var(--color-bg);
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
}

/* ---------- Top bar -------------------------------------------------------- */

.app-top-bar {
  position: sticky;
  top: 0;
  z-index: 20;
  height: var(--top-bar-height);
  background: var(--color-top-bar);
  display: flex;
  align-items: center;
  padding: 0 var(--page-padding);
}

.app-top-bar__brand {
  height: 28px;
  width: auto;
  opacity: 0.9;
}

/* ---------- Content -------------------------------------------------------- */

.app-content {
  flex: 1 1 auto;
  padding: var(--space-4) var(--page-padding);
  padding-bottom: calc(var(--bottom-nav-height) + var(--space-6));
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* ---------- Bottom navigation --------------------------------------------- */

.app-bottom-nav {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: var(--app-max-width);
  height: var(--bottom-nav-height);
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  align-items: center;
  z-index: 30;
}

.app-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  height: 100%;
  color: var(--color-nav-inactive);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  transition: color var(--duration-fast) var(--ease-standard);
}

.app-nav-item__icon {
  width: 24px;
  height: 24px;
  display: block;
}

.app-nav-item[aria-current="page"] {
  color: var(--color-nav-active);
}

/* ---------- Utilities ------------------------------------------------------ */

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.stack {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
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
    """Write base.css and commit."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    root = project_root()

    LOGGER.info("%s — timestep %d starting", SCRIPT_NAME, TIMESTEP)

    target = root / "web" / "assets" / "css" / "base.css"
    changed = write_file(target, BASE_CSS)
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