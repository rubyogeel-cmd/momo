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
