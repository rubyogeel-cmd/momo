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
