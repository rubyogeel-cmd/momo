#!/usr/bin/env python3
"""act13.py - Timestep 13: swap logo asset to user-provided PNG.

References the user-provided ``web/assets/img/logo.png`` in place of
the generated ``starlink.svg`` across all four pages, adds it as the
favicon, and removes the now-unused SVG so we do not carry a dead
asset.

Side effects
------------
* Edits web/index.html, plans.html, checkout.html, sms.html in place
  (idempotent).
* Deletes web/assets/img/starlink.svg if present.
* Commits the result with a descriptive message.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME: str = Path(__file__).name
TIMESTEP: int = 13

COMMIT_MESSAGE: str = (
    "act13: use user-provided logo.png\n"
    "\n"
    "Swaps the generated starlink.svg for the user-provided\n"
    "web/assets/img/logo.png across all four pages, adds it as the\n"
    "favicon, and removes the now-unused SVG."
)

TARGET_PAGES: tuple[str, ...] = (
    "web/index.html",
    "web/plans.html",
    "web/checkout.html",
    "web/sms.html",
)

OLD_LOGO_SRC: str = 'src="assets/img/starlink.svg"'
NEW_LOGO_SRC: str = 'src="assets/img/logo.png"'

FAVICON_ANCHOR: str = '  <link rel="stylesheet" href="assets/css/tokens.css">'
FAVICON_LINE: str = (
    '  <link rel="icon" type="image/png" href="assets/img/logo.png">\n'
    '  <link rel="stylesheet" href="assets/css/tokens.css">'
)

LOGGER = logging.getLogger(SCRIPT_NAME)


def project_root() -> Path:
    """Return the directory containing this script."""
    return Path(__file__).resolve().parent


def read_text(path: Path) -> str:
    """Return the file's UTF-8 text, or '' if it does not exist."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    """Write *text* to *path* as UTF-8 with LF endings."""
    path.write_text(text, encoding="utf-8", newline="\n")


def swap_logo_src(path: Path) -> str:
    """Replace the SVG src with the PNG src. Return a short status."""
    text = read_text(path)
    if not text:
        return "missing-file"
    if NEW_LOGO_SRC in text:
        return "already"
    if OLD_LOGO_SRC not in text:
        return "no-match"
    write_text(path, text.replace(OLD_LOGO_SRC, NEW_LOGO_SRC))
    return "replaced"


def add_favicon(path: Path) -> str:
    """Insert the favicon <link> if not already present."""
    text = read_text(path)
    if not text:
        return "missing-file"
    if '<link rel="icon"' in text:
        return "already"
    if FAVICON_ANCHOR not in text:
        return "no-anchor"
    write_text(path, text.replace(FAVICON_ANCHOR, FAVICON_LINE, 1))
    return "added"


def delete_if_exists(path: Path) -> bool:
    """Delete *path* if it exists. Return True if deleted."""
    if path.exists():
        path.unlink()
        return True
    return False


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
    """Swap logo, add favicon, delete SVG, commit."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    logo_path = root / "web" / "assets" / "img" / "logo.png"
    if not logo_path.exists():
        LOGGER.error("Expected logo at %s but it is missing. Aborting.",
                     logo_path.relative_to(root))
        return 1
    LOGGER.info("[found] %s", logo_path.relative_to(root))

    for relative in TARGET_PAGES:
        page = root / relative
        LOGGER.info("[%s] %s (logo src)", swap_logo_src(page), relative)
        LOGGER.info("[%s] %s (favicon)", add_favicon(page), relative)

    svg_path = root / "web" / "assets" / "img" / "starlink.svg"
    if delete_if_exists(svg_path):
        LOGGER.info("[deleted] %s", svg_path.relative_to(root))
    else:
        LOGGER.info("[absent ] %s", svg_path.relative_to(root))

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