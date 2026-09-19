/* ==========================================================================
   plans.js
   Pure domain data — Starlink Zambia data plans.
   Source: reference Page 2 (Plans).
   No DOM access, no side effects.
   ========================================================================== */

(function (global) {
  "use strict";

  /** @type {ReadonlyArray<Readonly<Plan>>} */
  var PLANS = Object.freeze([
    Object.freeze({
      code: "basic",
      name: "Basic Plan",
      quotaLabel: "50GB",
      description: "Up to 12 devices. Perfect for small households.",
      priceZmw: 15.0,
      billingPeriod: "month"
    }),
    Object.freeze({
      code: "standard",
      name: "Standard Plan",
      quotaLabel: "100GB",
      description: "Up to 25 devices. High-speed, low-latency internet.",
      priceZmw: 25.0,
      billingPeriod: "month"
    }),
    Object.freeze({
      code: "premium",
      name: "Premium Plan",
      quotaLabel: "250GB",
      description: "Up to 50 devices. Best for high-demand users.",
      priceZmw: 45.0,
      billingPeriod: "month"
    }),
    Object.freeze({
      code: "unlimited",
      name: "Unlimited Plan",
      quotaLabel: "Truly Unlimited",
      description:
        "Unlimited devices. Maximum performance for power users.",
      priceZmw: 95.0,
      billingPeriod: "month"
    })
  ]);

  /**
   * Look up a plan by its code.
   * @param {string} code
   * @returns {Plan | undefined}
   */
  function findPlanByCode(code) {
    for (var i = 0; i < PLANS.length; i += 1) {
      if (PLANS[i].code === code) {
        return PLANS[i];
      }
    }
    return undefined;
  }

  /**
   * Format a plan's price as it appears in the UI: "ZMW 45.00".
   * @param {Plan} plan
   * @returns {string}
   */
  function formatPlanPrice(plan) {
    return "ZMW " + plan.priceZmw.toFixed(2);
  }

  global.Plans = Object.freeze({
    all: PLANS,
    findByCode: findPlanByCode,
    formatPrice: formatPlanPrice
  });
})(window);
