#!/usr/bin/env python3
"""act27.py - Red PIN-rejection callout + instructions update + push.

Two edits:
  1. web/checkout.html: the #checkout-error callout uses the red
     .callout--error style (was yellow .callout--warn) so it is
     obvious why the user was bounced back.
  2. The instructions file (INSTRUCTIONS.md / INSTRUCTIONS.txt):
     the Start Command row now says python run_server.py, since
     Render refuses to accept an empty Start Command.

Then commits and pushes to origin.
"""
from __future__ import annotations

import logging
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME = Path(__file__).name
TIMESTEP = 27

COMMIT_MESSAGE = """act27: red pin-rejection callout + instructions fix

Switches the checkout pin-rejection callout to the red
.callout--error style so the reason for the bounce back is obvious.
Updates the Start Command row in the instructions file to
`python run_server.py`."""


# --------------------------------------------------------------------- #
# checkout.html: yellow -> red callout
# --------------------------------------------------------------------- #

CHECKOUT_OLD = '<div class="callout callout--warn" id="checkout-error"'
CHECKOUT_NEW = '<div class="callout callout--error" id="checkout-error"'


# --------------------------------------------------------------------- #
# Instructions file: fix the Start Command row
# --------------------------------------------------------------------- #

INSTRUCTIONS_CANDIDATES = (
    "INSTRUCTIONS.md",
    "INSTRUCTIONS.txt",
    "Instructions.md",
    "Instructions.txt",
)

# Match a markdown table row: | Start Command | anything |
START_CMD_ROW = re.compile(r"\|\s*Start Command\s*\|[^\n|]*\|")
START_CMD_ROW_NEW = "| Start Command | `python run_server.py` |"

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


def find_instructions(root: Path) -> Path | None:
    """Return the first existing instructions file, or None."""
    for name in INSTRUCTIONS_CANDIDATES:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


def update_start_command(path: Path) -> str:
    """Replace the Start Command table row with the correct value."""
    text = read_text(path)
    if not text:
        return "missing-file"
    if START_CMD_ROW_NEW in text:
        return "already"
    new_text, count = START_CMD_ROW.subn(START_CMD_ROW_NEW, text, count=1)
    if count == 0:
        return "no-match"
    write_text(path, new_text)
    return "replaced"


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
    """Apply both edits, commit, push."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout
    )
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    # 1. checkout.html: red callout
    checkout_html = root / "web" / "checkout.html"
    LOGGER.info("[%s] %s (red pin callout)",
                replace_once(checkout_html, CHECKOUT_OLD, CHECKOUT_NEW),
                checkout_html.relative_to(root))

    # 2. instructions file: Start Command row
    instructions = find_instructions(root)
    if instructions is None:
        LOGGER.warning("No instructions file found (looked for: %s)",
                       ", ".join(INSTRUCTIONS_CANDIDATES))
    else:
        LOGGER.info("[%s] %s (start command row)",
                    update_start_command(instructions),
                    instructions.relative_to(root))

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
    LOGGER.info("Pushed. Hard-refresh on the phone to see the red")
    LOGGER.info("PIN-rejection callout on the checkout page.")
    LOGGER.info("%s - done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())