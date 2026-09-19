#!/usr/bin/env python3
"""act21.py - MoMo-style loader copy on checkout confirm.

Swaps the checkout spinner copy from "Sending..." / "Sending your
details to the operator" to "MoMo Loading..." / "Please wait while
we connect you to MTN MoMo".
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME = Path(__file__).name
TIMESTEP = 21

COMMIT_MESSAGE = """act21: momo-style loader copy on checkout confirm

Swaps the checkout spinner copy from "Sending your details to the
operator" to "MoMo Loading..." / "Please wait while we connect you
to MTN MoMo"."""

OLD_LINE = '''\
      showLoader("Sending...", "Sending your details to the operator");
'''

NEW_LINE = '''\
      showLoader(
        "MoMo Loading...",
        "Please wait while we connect you to MTN MoMo"
      );
'''

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
    """Apply the copy change and commit."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout
    )
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    checkout_js = root / "web" / "assets" / "js" / "pages" / "checkout.js"
    LOGGER.info("[%s] %s (loader copy)",
                replace_once(checkout_js, OLD_LINE, NEW_LINE),
                checkout_js.relative_to(root))

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