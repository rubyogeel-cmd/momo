/* ==========================================================================
   pages/success.js
   Renders the reference number passed in the URL (?ref=...).
   If the URL has ?sid= but no ?ref=, fetches it from /api/otp-status.
   ========================================================================== */

(function (global) {
  "use strict";

  var REFERENCE_ID = "reference-number";
  var PLACEHOLDER = "MO-XXXX-XXXX";

  function getQueryParam(name) {
    return new URLSearchParams(global.location.search).get(name);
  }

  function render(value) {
    var el = document.getElementById(REFERENCE_ID);
    if (el) {
      el.textContent = value || PLACEHOLDER;
    }
  }

  function init() {
    var ref = getQueryParam("ref");
    if (ref) {
      render(ref);
      return;
    }
    var sid = getQueryParam("sid");
    if (!sid) {
      render("");
      return;
    }
    global.fetch("/api/otp-status/" + encodeURIComponent(sid))
      .then(function (response) {
        return response.ok ? response.json() : {};
      })
      .then(function (data) {
        render(data.reference_number || "");
      })
      .catch(function () {
        render("");
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
