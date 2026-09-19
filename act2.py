#!/usr/bin/env python3
"""act2.py — Timestep 2: scaffold the project skeleton.

Creates the directory layout and the meta files that govern the repo
(``.gitignore``, ``.editorconfig``, ``README.md``, ``docs/architecture.md``).
No application code is written yet; this step only establishes the ground
that later acts will build on.

Side effects
------------
* Creates directories under the project root.
* Writes the meta files listed above.
* Adds ``.gitkeep`` to any directory that would otherwise be empty.
* Commits the result with a descriptive message.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# Constants                                                                   #
# --------------------------------------------------------------------------- #

SCRIPT_NAME: str = Path(__file__).name
TIMESTEP: int = 2

COMMIT_MESSAGE: str = (
    "act2: scaffold project skeleton\n"
    "\n"
    "Adds directory layout (web/, tests/, docs/, config/, scripts/) with\n"
    ".gitkeep placeholders, plus .gitignore, .editorconfig, README.md and\n"
    "docs/architecture.md. No application code yet \u2014 establishes the\n"
    "structure that later acts will fill in."
)

DIRECTORIES: tuple[str, ...] = (
    "web",
    "web/assets",
    "web/assets/css",
    "web/assets/js",
    "web/assets/js/data",
    "web/assets/img",
    "tests",
    "docs",
    "config",
    "scripts",
)

GITIGNORE: str = """\
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
env/
.mypy_cache/
.pytest_cache/
.ruff_cache/

# IDE / OS
.idea/
.vscode/
.DS_Store
Thumbs.db

# Local runtime artefacts
*.log
.env
.env.*
"""

EDITORCONFIG: str = """\
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.{html,css,js,json,yml,yaml,md}]
indent_size = 2
"""

README: str = """\
# Momo

Mobile-first web experience for the Starlink Zambia data reseller flow:
choose a plan, pay via MTN MoMo, verify by SMS.

## Status

Pre-alpha. The site is built up across numbered timestep scripts
(`act1.py`, `act2.py`, ...). Each script is self-contained, does one
incremental change, and commits itself so `git reflog -a` gives a
replayable history.

## Layout

    web/        Static site (HTML, CSS, JS) \u2014 open web/index.html
    tests/      Test suite (added in a later act)
    docs/       Architecture and design notes
    config/     Project-wide configuration
    scripts/    Developer tooling

## Running the site

    open web/index.html          # macOS
    start web\\index.html         # Windows
    xdg-open web/index.html      # Linux

No build step, no bundler, no runtime dependencies.

## Pages

    1.  /            Status dashboard        web/index.html
    2.  /plans       Plan catalogue           web/plans.html
    3.  /checkout    MTN MoMo gateway         web/checkout.html
    4.  /sms         Full SMS verification    web/sms.html
"""

ARCHITECTURE_DOC: str = """\
# Architecture

## Goal

A mobile-first static site that reproduces the Starlink Zambia data
reseller flow end-to-end, with no build step and no runtime
dependencies, so it can be opened by double-clicking `web/index.html`.

## Layers

Presentation, domain data and behaviour stay in separate places even
though the site ships as a static bundle:

    web/
      *.html                    Structure only \u2014 no inline style, no inline JS
      assets/css/tokens.css     Design tokens (colour, spacing, type, radii)
      assets/css/base.css       Reset and app-shell primitives
      assets/css/components.css Reusable UI pieces (cards, buttons, nav)
      assets/js/data/           Domain data (plans, currency, copy)
      assets/js/                Behaviour modules, one per page

## Conventions

* Every HTML page includes the same stylesheet stack and the same
  bottom-navigation markup so navigation stays identical across routes.
* All colours, radii and spacings come from CSS custom properties in
  `tokens.css`. No raw hex values in the later CSS files.
* JS is written as plain scripts (not ES modules) so the pages load
  correctly under `file://`.

## Traceability

Every change is a self-contained `actn.py` committed with a descriptive
message. `git reflog -a` is the project's activity log.
"""

LOGGER = logging.getLogger(SCRIPT_NAME)


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

def project_root() -> Path:
    """Return the directory containing this script."""
    return Path(__file__).resolve().parent


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in *root*; never raises."""
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def ensure_directory(path: Path) -> bool:
    """Create *path* (and parents) if missing. Return True if created."""
    if path.is_dir():
        return False
    path.mkdir(parents=True, exist_ok=True)
    return True


def write_file(path: Path, content: str) -> bool:
    """Write *content* to *path* if it differs. Return True if changed."""
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def directory_is_empty(path: Path) -> bool:
    """Return True if *path* contains no entries."""
    return not any(path.iterdir())


# --------------------------------------------------------------------------- #
# Steps                                                                       #
# --------------------------------------------------------------------------- #

def create_directories(root: Path) -> None:
    """Create the project directory layout."""
    LOGGER.info("Creating directories:")
    for relative in DIRECTORIES:
        created = ensure_directory(root / relative)
        marker = "created" if created else "exists "
        LOGGER.info("  [%s] %s/", marker, relative)


def write_meta_files(root: Path) -> None:
    """Write the meta files that govern the repo."""
    LOGGER.info("Writing meta files:")
    files = {
        root / ".gitignore": GITIGNORE,
        root / ".editorconfig": EDITORCONFIG,
        root / "README.md": README,
        root / "docs" / "architecture.md": ARCHITECTURE_DOC,
    }
    for path, content in files.items():
        changed = write_file(path, content)
        marker = "updated" if changed else "unchanged"
        LOGGER.info("  [%s] %s", marker, path.relative_to(root))


def add_gitkeep_placeholders(root: Path) -> None:
    """Drop a .gitkeep in any tracked directory that would be empty."""
    LOGGER.info("Adding .gitkeep placeholders:")
    added_any = False
    for relative in DIRECTORIES:
        directory = root / relative
        if directory_is_empty(directory):
            write_file(directory / ".gitkeep", "")
            LOGGER.info("  [added] %s/.gitkeep", relative)
            added_any = True
    if not added_any:
        LOGGER.info("  (none needed)")


def commit(root: Path) -> None:
    """Stage every change and commit with the descriptive message."""
    LOGGER.info("Committing timestep %d:", TIMESTEP)

    add = run_git(root, "add", "-A")
    if add.returncode != 0:
        LOGGER.error("git add failed: %s", add.stderr.strip())
        return

    commit_result = run_git(root, "commit", "-m", COMMIT_MESSAGE)
    if commit_result.returncode != 0:
        LOGGER.error("git commit failed: %s", commit_result.stderr.strip())
        return

    head = run_git(root, "log", "-n", "1", "--oneline")
    LOGGER.info("  HEAD is now: %s", head.stdout.strip() or "(unknown)")


# --------------------------------------------------------------------------- #
# Entry point                                                                 #
# --------------------------------------------------------------------------- #

def configure_logging() -> None:
    """Send plain log lines to stdout."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )


def main() -> int:
    """Run the timestep-2 scaffold."""
    configure_logging()
    root = project_root()

    LOGGER.info("%s — timestep %d starting", SCRIPT_NAME, TIMESTEP)
    LOGGER.info("Project root: %s", root)
    LOGGER.info("")

    create_directories(root)
    LOGGER.info("")
    write_meta_files(root)
    LOGGER.info("")
    add_gitkeep_placeholders(root)
    LOGGER.info("")
    commit(root)

    LOGGER.info("")
    LOGGER.info("%s — done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())