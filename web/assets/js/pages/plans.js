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
