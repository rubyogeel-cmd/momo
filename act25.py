#!/usr/bin/env python3
"""act25.py - Connect GitHub remote and push.

Assumes you have already created an empty repo on GitHub and obtained
a Personal Access Token. Configures git user.name/email if missing,
adds or updates the origin remote, renames master -> main if needed,
commits this script, and pushes to origin/main.

You WILL be prompted for GitHub credentials during the push:
  Username: your GitHub username
  Password: paste your Personal Access Token (ghp_...)
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME = Path(__file__).name
TIMESTEP = 25

# --------------------------------------------------------------------- #
# EDIT THESE TWO LINES BEFORE RUNNING
# --------------------------------------------------------------------- #

GITHUB_USERNAME = "rubyogeel-cmd"
REPO_NAME = "momo"

# --------------------------------------------------------------------- #

REMOTE_NAME = "origin"
TARGET_BRANCH = "main"

COMMIT_MESSAGE = """act25: connect github remote

Adds act25.py, which configures the origin remote and pushes to
GitHub. No application code changes."""

LOGGER = logging.getLogger(SCRIPT_NAME)


def project_root() -> Path:
    """Return the directory containing this script."""
    return Path(__file__).resolve().parent


def run_git(
    root: Path,
    *args: str,
    interactive: bool = False,
) -> subprocess.CompletedProcess[str] | int:
    """Run git in *root*.

    When interactive is True, stdin/stdout/stderr are inherited so
    git can prompt for credentials; returns the exit code.
    Otherwise, output is captured and a CompletedProcess is returned.
    """
    if interactive:
        return subprocess.call(["git", *args], cwd=root)
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def git_output(root: Path, *args: str) -> str:
    """Return trimmed stdout of a git command, or '' on failure."""
    result = run_git(root, *args)
    if isinstance(result, int):
        return ""
    return result.stdout.strip()


def ensure_identity(root: Path) -> bool:
    """Warn if git user.name or user.email is missing."""
    name = git_output(root, "config", "user.name")
    email = git_output(root, "config", "user.email")
    if name and email:
        LOGGER.info("git identity: %s <%s>", name, email)
        return True
    LOGGER.error("git user.name and/or user.email are not set.")
    LOGGER.error("Set them once (global) with:")
    LOGGER.error('    git config --global user.name "Your Name"')
    LOGGER.error('    git config --global user.email "you@example.com"')
    return False


def ensure_branch(root: Path) -> None:
    """Rename master -> main if necessary."""
    current = git_output(root, "rev-parse", "--abbrev-ref", "HEAD")
    LOGGER.info("current branch: %s", current or "(unknown)")
    if current == "master":
        LOGGER.info("renaming master -> %s", TARGET_BRANCH)
        rename = run_git(root, "branch", "-M", TARGET_BRANCH)
        if not isinstance(rename, int) and rename.returncode != 0:
            LOGGER.error("rename failed: %s", rename.stderr.strip())


def ensure_remote(root: Path, url: str) -> None:
    """Add or update the origin remote."""
    existing = git_output(root, "remote", "get-url", REMOTE_NAME)
    if not existing:
        LOGGER.info("adding remote %s -> %s", REMOTE_NAME, url)
        result = run_git(root, "remote", "add", REMOTE_NAME, url)
        if not isinstance(result, int) and result.returncode != 0:
            LOGGER.error("remote add failed: %s", result.stderr.strip())
        return
    if existing == url:
        LOGGER.info("remote %s already points at %s", REMOTE_NAME, url)
        return
    LOGGER.info("updating remote %s: %s -> %s", REMOTE_NAME, existing, url)
    result = run_git(root, "remote", "set-url", REMOTE_NAME, url)
    if not isinstance(result, int) and result.returncode != 0:
        LOGGER.error("remote set-url failed: %s", result.stderr.strip())


def commit_act(root: Path) -> None:
    """Stage and commit this script if there are changes."""
    add = run_git(root, "add", "-A")
    if isinstance(add, int):
        return

    # If nothing to commit, skip.
    status = git_output(root, "status", "--porcelain")
    if not status:
        LOGGER.info("nothing to commit")
        return

    commit = run_git(root, "commit", "-m", COMMIT_MESSAGE)
    if not isinstance(commit, int) and commit.returncode != 0:
        LOGGER.error("commit failed: %s", commit.stderr.strip())
        return
    LOGGER.info("committed: %s", git_output(root, "log", "-n", "1", "--oneline"))


def push(root: Path) -> int:
    """Push interactively so git can prompt for credentials."""
    LOGGER.info("")
    LOGGER.info("=" * 68)
    LOGGER.info("Pushing to GitHub. Git will prompt for credentials:")
    LOGGER.info("    Username: your GitHub username")
    LOGGER.info("    Password: paste your Personal Access Token (ghp_...)")
    LOGGER.info("The token will not echo as you type or paste it.")
    LOGGER.info("=" * 68)
    LOGGER.info("")
    return run_git(
        root,
        "push",
        "-u",
        REMOTE_NAME,
        TARGET_BRANCH,
        interactive=True,
    )


def main() -> int:
    """Configure remote, commit, push."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout
    )
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    if GITHUB_USERNAME == "REPLACE_WITH_YOUR_GITHUB_USERNAME":
        LOGGER.error("Edit GITHUB_USERNAME at the top of this script first.")
        return 1

    if not ensure_identity(root):
        return 1

    ensure_branch(root)

    url = f"https://github.com/{GITHUB_USERNAME}/{REPO_NAME}.git"
    ensure_remote(root, url)

    commit_act(root)

    rc = push(root)
    if rc != 0:
        LOGGER.error("")
        LOGGER.error("Push failed (exit %d).", rc)
        LOGGER.error("Common causes:")
        LOGGER.error("  * Wrong username or token")
        LOGGER.error("  * Token missing the 'repo' scope")
        LOGGER.error("  * Repository does not exist on GitHub yet")
        LOGGER.error("  * Repo was created with a README, so the histories")
        LOGGER.error("    diverge. Fix with:")
        LOGGER.error("      git pull --rebase origin main")
        LOGGER.error("      git push -u origin main")
        return 1

    LOGGER.info("")
    LOGGER.info("Pushed. Your repo is now at:")
    LOGGER.info("    https://github.com/%s/%s", GITHUB_USERNAME, REPO_NAME)
    LOGGER.info("%s - done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())