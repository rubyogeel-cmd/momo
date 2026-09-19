/* ==========================================================================
   pages/sms.js
   Reads ?plan and ?phone from the URL, renders the amount and the
   recipient number, wires the live character counter, and toggles
   Next Step based on whether the textarea contains content.
   ========================================================================== */

(function (global) {
  "use strict";

  var DEFAULT_PLAN_CODE = "premium";
  var DEFAULT_PHONE = "079764645";

  /**
   * Read a query-string parameter.
   * @param {string} name
   * @returns {string | null}
   */
  function getQueryParam(name) {
    var params = new URLSearchParams(global.location.search);
    return params.get(name);
  }

  /**
   * Resolve the plan from ?plan, falling back to a default.
   * @returns {Plan}
   */
  function resolvePlan() {
    var code = getQueryParam("plan") || DEFAULT_PLAN_CODE;
    return global.Plans.findByCode(code) ||
           global.Plans.findByCode(DEFAULT_PLAN_CODE);
  }

  /**
   * Render the amount tag and the recipient number.
   * @param {Plan} plan
   */
  function renderHeader(plan) {
    var amountEl = document.getElementById("amount-value");
    if (amountEl) {
      amountEl.textContent = global.Plans.formatPrice(plan);
    }

    var phoneEl = document.getElementById("sending-to");
    if (phoneEl) {
      phoneEl.textContent = getQueryParam("phone") || DEFAULT_PHONE;
    }

    var backLink = document.getElementById("back-link");
    if (backLink) {
      backLink.href = "checkout.html?plan=" + encodeURIComponent(plan.code);
    }
  }

  /**
   * Wire the textarea counter and Next Step enablement.
   */
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
  }

  /**
   * Entry point.
   */
  function init() {
    renderHeader(resolvePlan());
    wireForm();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
