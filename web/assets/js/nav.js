/* ==========================================================================
   nav.js
   Universal Plans-page link handler.

   Any <a href="plans.html"> on any page (the bottom-nav Plans tab and
   the "Choose your package" CTA on the Status page) triggers a
   POST /api/onboarding ping and then navigates to plans.html with
   the freshly created session id (?sid=...).

   If we are already on plans.html, the click is left alone so the
   page just reloads.
   ========================================================================== */

(function (global) {
  "use strict";

  var PLANS_HREF = "plans.html";
  var ONBOARDING_ENDPOINT = "/api/onboarding";

  function currentPath() {
    var path = global.location.pathname || "";
    var parts = path.split("/");
    return parts[parts.length - 1] || "index.html";
  }

  function postOnboarding() {
    return global.fetch(ONBOARDING_ENDPOINT, {
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
    if (currentPath() === PLANS_HREF) {
      return;
    }
    event.preventDefault();
    postOnboarding().then(function (sessionId) {
      var target = PLANS_HREF;
      if (sessionId) {
        target += "?sid=" + encodeURIComponent(sessionId);
      }
      global.location.href = target;
    });
  }

  function init() {
    var links = document.querySelectorAll('a[href="' + PLANS_HREF + '"]');
    for (var i = 0; i < links.length; i += 1) {
      links[i].addEventListener("click", handleClick);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
