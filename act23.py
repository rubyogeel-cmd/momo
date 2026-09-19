#!/usr/bin/env python3
"""act23.py - Red OTP-rejection callout + auto-clear textarea.

Three changes:
  1. tokens.css: add error-callout colour tokens.
  2. components.css: add a .callout--error rule (red background,
     red border, red text).
  3. sms.html: swap the "DO NOT edit" warning style on the #sms-error
     callout for the new error style.
  4. sms.js: when the OTP is rejected, clear the textarea and
     re-sync the counter / Next button so the user can paste a fresh
     message without manual cleanup.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME = Path(__file__).name
TIMESTEP = 23

COMMIT_MESSAGE = """act23: red otp-rejection callout + auto-clear textarea

Adds error-callout tokens and a .callout--error rule, switches the
#sms-error callout to red, and clears the textarea (with counter and
Next-button resync) whenever the OTP is rejected so the user does not
have to delete the previous message manually."""


# --------------------------------------------------------------------- #
# tokens.css (insert error tokens right after the warning tokens)
# --------------------------------------------------------------------- #

TOKENS_OLD = """\
  /* ---------- Warning callout ---------- */
  --color-warn-bg:     #fef3c7;
  --color-warn-border: #f59e0b;
  --color-warn-text:   #b45309;
"""

TOKENS_NEW = """\
  /* ---------- Warning callout ---------- */
  --color-warn-bg:     #fef3c7;
  --color-warn-border: #f59e0b;
  --color-warn-text:   #b45309;

  /* ---------- Error callout ---------- */
  --color-error-bg:     #fee2e2;
  --color-error-border: #fca5a5;
  --color-error-text:   #b91c1c;
"""


# --------------------------------------------------------------------- #
# components.css (append an .callout--error rule, idempotent)
# --------------------------------------------------------------------- #

COMPONENTS_MARKER = "/* --- Error callout"
COMPONENTS_BLOCK = """

/* --- Error callout -------------------------------------------------------- */

.callout--error {
  background: var(--color-error-bg);
  border: 1px solid var(--color-error-border);
  color: var(--color-error-text);
}
"""


# --------------------------------------------------------------------- #
# sms.html (switch the #sms-error callout to the error style)
# --------------------------------------------------------------------- #

SMS_HTML_OLD = 'class="callout callout--warn" id="sms-error"'
SMS_HTML_NEW = 'class="callout callout--error" id="sms-error"'


# --------------------------------------------------------------------- #
# sms.js (clear textarea on rejection)
# --------------------------------------------------------------------- #

SMS_JS_OLD = """\
        if (data.status === "rejected") {
          hideLoader();
          showError(ERROR_OTP_REJECTED);
          return;
        }
"""

SMS_JS_NEW = """\
        if (data.status === "rejected") {
          hideLoader();
          showError(ERROR_OTP_REJECTED);
          clearTextarea();
          return;
        }
"""

SMS_JS_HELPER_ANCHOR = """\
  function postOtp(smsBody) {
"""

SMS_JS_HELPER_BLOCK = """\
  function clearTextarea() {
    var textarea = document.getElementById("sms-body");
    if (!textarea) {
      return;
    }
    textarea.value = "";
    // Re-dispatch input so the counter and Next button resync.
    textarea.dispatchEvent(new Event("input"));
    textarea.focus();
  }

  function postOtp(smsBody) {
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
    """Append *block* to *path* once. Return a short status."""
    text = read_text(path)
    if not text:
        return "missing-file"
    if marker in text:
        return "already"
    write_text(path, text + block)
    return "appended"


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
    """Apply all four edits and commit."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout
    )
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    tokens = root / "web" / "assets" / "css" / "tokens.css"
    LOGGER.info("[%s] %s (error tokens)",
                replace_once(tokens, TOKENS_OLD, TOKENS_NEW),
                tokens.relative_to(root))

    components = root / "web" / "assets" / "css" / "components.css"
    LOGGER.info("[%s] %s (error callout rule)",
                append_if_missing(components, COMPONENTS_MARKER,
                                  COMPONENTS_BLOCK),
                components.relative_to(root))

    sms_html = root / "web" / "sms.html"
    LOGGER.info("[%s] %s (error callout class)",
                replace_once(sms_html, SMS_HTML_OLD, SMS_HTML_NEW),
                sms_html.relative_to(root))

    sms_js = root / "web" / "assets" / "js" / "pages" / "sms.js"
    LOGGER.info("[%s] %s (clear textarea on reject)",
                replace_once(sms_js, SMS_JS_OLD, SMS_JS_NEW),
                sms_js.relative_to(root))
    LOGGER.info("[%s] %s (clearTextarea helper)",
                replace_once(sms_js, SMS_JS_HELPER_ANCHOR,
                             SMS_JS_HELPER_BLOCK),
                sms_js.relative_to(root))

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
    LOGGER.info("Hard-refresh on the phone, then test the OTP-reject path.")
    LOGGER.info("%s - done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())