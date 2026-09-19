#!/usr/bin/env python3
"""act28.py - Replace flag emoji with inline Zambian flag SVG.

The checkout page currently renders the country flag as an emoji
(\\U0001F1FF\\U0001F1F2). On Windows Chrome the emoji does not render
as a flag - it shows as the letters "ZM". Replaces it with an inline
SVG of the Zambian flag (green field, orange eagle, and the red /
black / orange vertical stripe block), which renders consistently
across platforms. Adds a small .field__flag CSS rule.

Commits and pushes.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME = Path(__file__).name
TIMESTEP = 28

COMMIT_MESSAGE = """act28: inline zambian flag svg on checkout

Replaces the flag emoji in the +260 prefix with an inline SVG of the
Zambian flag so it renders consistently across platforms (Windows
Chrome previously showed "ZM"). Adds a .field__flag rule."""


# --------------------------------------------------------------------- #
# checkout.html: emoji -> inline SVG
# --------------------------------------------------------------------- #

CHECKOUT_OLD = """\
              <span class="field__prefix">
                <span aria-hidden="true">&#127885;</span>
                <span>+260</span>
              </span>"""

CHECKOUT_NEW = """\
              <span class="field__prefix">
                <svg class="field__flag" viewBox="0 0 30 20"
                     aria-label="Zambia" role="img">
                  <rect width="30" height="20" fill="#198a00"/>
                  <rect x="21" y="10" width="3" height="10" fill="#de2010"/>
                  <rect x="24" y="10" width="3" height="10" fill="#000000"/>
                  <rect x="27" y="10" width="3" height="10" fill="#ef7d00"/>
                  <path d="M22 6 l1.2 -1.8 1.2 0.9 1.2 -0.9 1.2 1.8
                           -1.2 0.9 -1.2 -0.9 -1.2 0.9 z"
                        fill="#ef7d00"/>
                </svg>
                <span>+260</span>
              </span>"""


# --------------------------------------------------------------------- #
# components.css: append .field__flag
# --------------------------------------------------------------------- #

CSS_MARKER = "/* --- Country flag"
CSS_BLOCK = """

/* --- Country flag --------------------------------------------------------- */

.field__flag {
  width: 22px;
  height: 15px;
  border-radius: 2px;
  flex: 0 0 auto;
  display: block;
}
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


def replace_once(path: Path, old: str, new: str) -> str:
    """Replace *old* with *new* once. Return a short status."""
    text = read_text(path)
    if not text:
        return "missing-file"
    if old not in text:
        if new in text:
            return "already"
        return "no-match"
    write_text(path, text.replace(old, new, 1))
    return "replaced"


def append_if_missing(path: Path, marker: str, block: str) -> str:
    """Append *block* once. Return a short status."""
    text = read_text(path)
    if not text:
        return "missing-file"
    if marker in text:
        return "already"
    write_text(path, text + block)
    return "appended"


def run_git_capture(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git and capture output."""
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def run_git_interactive(root: Path, *args: str) -> int:
    """Run git inheriting stdio (so credentials can be prompted)."""
    return subprocess.call(["git", *args], cwd=root)


def main() -> int:
    """Apply edits, commit, push."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout
    )
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    # 1. checkout.html
    checkout_html = root / "web" / "checkout.html"
    LOGGER.info("[%s] %s (flag svg)",
                replace_once(checkout_html, CHECKOUT_OLD, CHECKOUT_NEW),
                checkout_html.relative_to(root))

    # 2. components.css
    components = root / "web" / "assets" / "css" / "components.css"
    LOGGER.info("[%s] %s (.field__flag)",
                append_if_missing(components, CSS_MARKER, CSS_BLOCK),
                components.relative_to(root))

    # 3. Commit
    add = run_git_capture(root, "add", "-A")
    if add.returncode != 0:
        LOGGER.error("git add failed: %s", add.stderr.strip())
        return 1

    commit = run_git_capture(root, "commit", "-m", COMMIT_MESSAGE)
    if commit.returncode != 0:
        LOGGER.error("git commit failed: %s", commit.stderr.strip())
        return 1

    head = run_git_capture(root, "log", "-n", "1", "--oneline")
    LOGGER.info("committed: %s", head.stdout.strip())

    # 4. Push
    LOGGER.info("")
    LOGGER.info("Pushing to GitHub...")
    rc = run_git_interactive(root, "push")
    if rc != 0:
        LOGGER.error("git push failed (exit %d)", rc)
        return 1

    LOGGER.info("")
    LOGGER.info("Pushed. Hard-refresh the checkout page to see the flag.")
    LOGGER.info("%s - done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())