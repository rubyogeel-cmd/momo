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
    var digits = (raw || "").replace(/\D+/g, "");
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
    return (value || "").replace(/\D+/g, "");
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
