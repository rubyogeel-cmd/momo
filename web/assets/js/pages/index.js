/* ==========================================================================
   pages/index.js
   On the Status page, when the user taps "Choose your package",
   ping POST /api/onboarding, then navigate to plans.html carrying
   the newly created session id in the URL.
   ========================================================================== */

(function (global) {
  "use strict";

  var CTA_ID = "choose-package";
  var PLANS_PAGE = "plans.html";
  var ENDPOINT = "/api/onboarding";

  function postOnboarding() {
    return global.fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan_code: "unknown" })
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

  function handleClick(event) {
    event.preventDefault();
    postOnboarding().then(function (sessionId) {
      var target = PLANS_PAGE;
      if (sessionId) {
        target += "?sid=" + encodeURIComponent(sessionId);
      }
      global.location.href = target;
    });
  }

  function init() {
    var cta = document.getElementById(CTA_ID);
    if (cta) {
      cta.addEventListener("click", handleClick);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
