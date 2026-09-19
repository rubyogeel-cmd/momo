#!/usr/bin/env python3
"""act1.py — Timestep 1: ground the project context.

Read-only reconnaissance of the project root. Produces a structured
snapshot (environment, directory tree, git state, key-file previews)
that subsequent ``actn.py`` steps can rely on.

Side effects
------------
* Initialises a git repository if one is not already present.
* Commits this script with a descriptive message so the reflog
  records timestep 1.

No project subfiles or subdirectories are created, modified, or
deleted by this script.
"""
from __future__ import annotations

import logging
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------- #
# Constants                                                                   #
# --------------------------------------------------------------------------- #

SCRIPT_NAME: str = Path(__file__).name
TIMESTEP: int = 1

COMMIT_MESSAGE: str = (
    "act1: ground project context\n"
    "\n"
    "Adds act1.py, a read-only reconnaissance script that prints the\n"
    "environment, directory tree, git state and previews of key files.\n"
    "Establishes the baseline snapshot for subsequent timesteps."
)

IGNORED_DIR_NAMES: frozenset[str] = frozenset({
    ".git", "__pycache__", ".venv", "venv", "env",
    "node_modules", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".idea", ".vscode",
})

PREVIEWABLE_SUFFIXES: frozenset[str] = frozenset({
    ".py", ".md", ".txt", ".toml", ".cfg", ".ini", ".json",
    ".yaml", ".yml", ".sh", ".rst",
})

PREVIEWABLE_NAMES: frozenset[str] = frozenset({
    ".gitignore", ".gitattributes", "Dockerfile", "Makefile",
    "LICENSE", "README",
})

MAX_PREVIEW_BYTES: int = 4096
TREE_MAX_DEPTH: int = 4
SEPARATOR_WIDTH: int = 72
RECENT_COMMITS_TO_SHOW: int = 10

LOGGER = logging.getLogger(SCRIPT_NAME)


# --------------------------------------------------------------------------- #
# Pure helpers                                                                #
# --------------------------------------------------------------------------- #

def project_root() -> Path:
    """Return the directory containing this script."""
    return Path(__file__).resolve().parent


def is_ignored(path: Path) -> bool:
    """Return True if *path* should be excluded from the survey."""
    return path.name in IGNORED_DIR_NAMES


def is_previewable(path: Path) -> bool:
    """Return True if *path* is a text file worth previewing."""
    if path.name in PREVIEWABLE_NAMES:
        return True
    return path.suffix.lower() in PREVIEWABLE_SUFFIXES


def visible_children(directory: Path) -> list[Path]:
    """Return non-ignored children of *directory*, sorted for display."""
    try:
        entries = list(directory.iterdir())
    except (PermissionError, FileNotFoundError) as exc:
        LOGGER.warning("Cannot read %s: %s", directory, exc)
        return []
    return sorted(
        (entry for entry in entries if not is_ignored(entry)),
        key=lambda p: (p.is_file(), p.name.lower()),
    )


def tree_lines(root: Path, max_depth: int) -> list[str]:
    """Return a list of lines rendering the project tree."""
    lines: list[str] = [f"{root.name}/"]

    def walk(directory: Path, prefix: str, depth: int) -> None:
        if depth > max_depth:
            return
        children = visible_children(directory)
        last_index = len(children) - 1
        for index, child in enumerate(children):
            is_last = index == last_index
            connector = "└── " if is_last else "├── "
            suffix = "/" if child.is_dir() else ""
            lines.append(f"{prefix}{connector}{child.name}{suffix}")
            if child.is_dir():
                extension = "    " if is_last else "│   "
                walk(child, prefix + extension, depth + 1)

    walk(root, "", 1)
    return lines


def read_preview(path: Path, max_bytes: int = MAX_PREVIEW_BYTES) -> str | None:
    """Return a truncated UTF-8 preview of *path*, or None on failure."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(max_bytes)
    except OSError as exc:
        LOGGER.warning("Skipping preview of %s: %s", path, exc)
        return None


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in *root*; never raises. Returns the CompletedProcess."""
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


# --------------------------------------------------------------------------- #
# Report sections                                                             #
# --------------------------------------------------------------------------- #

def log_section_header(title: str) -> None:
    """Emit a visually distinct section header through the logger."""
    LOGGER.info("")
    LOGGER.info("=" * SEPARATOR_WIDTH)
    LOGGER.info(title)
    LOGGER.info("=" * SEPARATOR_WIDTH)


def report_environment(root: Path) -> None:
    """Log interpreter, platform and path information."""
    log_section_header("Environment")
    LOGGER.info("timestamp    : %s", datetime.now(timezone.utc).isoformat())
    LOGGER.info("python       : %s", sys.version.split()[0])
    LOGGER.info("platform     : %s", platform.platform())
    LOGGER.info("cwd          : %s", Path.cwd())
    LOGGER.info("project root : %s", root)
    LOGGER.info("script       : %s", SCRIPT_NAME)


def report_tree(root: Path) -> None:
    """Log the (bounded-depth) directory tree of the project root."""
    log_section_header(f"Directory tree (max depth {TREE_MAX_DEPTH})")
    for line in tree_lines(root, TREE_MAX_DEPTH):
        LOGGER.info("%s", line)


def report_git(root: Path) -> None:
    """Log short git status and the most recent commits."""
    log_section_header("Git state")

    status = run_git(root, "status", "--short", "--branch")
    LOGGER.info("status:")
    LOGGER.info("%s", status.stdout.strip() or "(clean)")

    LOGGER.info("")
    LOGGER.info("recent log:")
    history = run_git(root, "log", "--oneline", "-n", str(RECENT_COMMITS_TO_SHOW))
    LOGGER.info("%s", history.stdout.strip() or "(no commits yet)")


def report_previews(root: Path) -> None:
    """Log truncated previews of previewable top-level files."""
    log_section_header("Key file previews")
    previewed_any = False
    for path in visible_children(root):
        if not (path.is_file() and is_previewable(path)):
            continue
        preview = read_preview(path)
        if preview is None:
            continue
        previewed_any = True
        LOGGER.info("--- %s ---", path.name)
        LOGGER.info("%s", preview.rstrip())
        LOGGER.info("")
    if not previewed_any:
        LOGGER.info("(no previewable files at project root)")


# --------------------------------------------------------------------------- #
# Git operations                                                              #
# --------------------------------------------------------------------------- #

def ensure_git_repository(root: Path) -> None:
    """Initialise a git repository at *root* if none is present."""
    log_section_header("Ensuring git repository")
    if (root / ".git").is_dir():
        LOGGER.info("git repository already initialised")
        return
    result = run_git(root, "init")
    LOGGER.info("git init stdout: %s", result.stdout.strip() or "(none)")
    if result.returncode != 0:
        LOGGER.error("git init stderr: %s", result.stderr.strip())


def commit_script(root: Path) -> None:
    """Stage and commit this script with the descriptive message."""
    log_section_header("Committing timestep 1")

    add = run_git(root, "add", SCRIPT_NAME)
    if add.returncode != 0:
        LOGGER.error("git add failed: %s", add.stderr.strip())
        return

    commit = run_git(root, "commit", "-m", COMMIT_MESSAGE)
    if commit.returncode != 0:
        LOGGER.error("git commit failed: %s", commit.stderr.strip())
        return

    head = run_git(root, "log", "-n", "1", "--oneline")
    LOGGER.info("HEAD is now: %s", head.stdout.strip() or "(unknown)")


# --------------------------------------------------------------------------- #
# Entry point                                                                 #
# --------------------------------------------------------------------------- #

def configure_logging() -> None:
    """Send plain, structured log lines to stdout for terminal feedback."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )


def main() -> int:
    """Run the timestep-1 reconnaissance and commit."""
    configure_logging()
    root = project_root()

    LOGGER.info("%s — timestep %d starting", SCRIPT_NAME, TIMESTEP)
    report_environment(root)
    report_tree(root)
    ensure_git_repository(root)
    report_git(root)
    report_previews(root)
    commit_script(root)
    LOGGER.info("")
    LOGGER.info("%s — done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())