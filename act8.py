#!/usr/bin/env python3
"""act8.py - Timestep 8: Page 2 (Plans).

Writes ``web/plans.html`` (structure: gold hero card, section heading,
empty plan-list container, bottom nav) and
``web/assets/js/pages/plans.js`` (renders the four plan cards from
``window.Plans``).

Plan cards link to ``checkout.html?plan=<code>`` so the checkout page
can select the correct plan.

Side effects
------------
* Creates the two files above.
* Commits the result with a descriptive message.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME: str = Path(__file__).name
TIMESTEP: int = 8

COMMIT_MESSAGE: str = (
    "act8: add page 2 - plans catalogue\n"
    "\n"
    "Adds web/plans.html (gold hero, Select Your Plan heading, empty\n"
    "plan list, bottom nav) and web/assets/js/pages/plans.js which\n"
    "renders the four plan cards from window.Plans. Cards link to\n"
    "checkout.html?plan=<code>. ASCII-only commit message."
)

PLANS_HTML: str = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#000000">
  <title>Plans - Starlink Zambia</title>
  <link rel="stylesheet" href="assets/css/tokens.css">
  <link rel="stylesheet" href="assets/css/base.css">
  <link rel="stylesheet" href="assets/css/components.css">
</head>
<body>
  <div class="app-shell">

    <header class="app-top-bar">
      <svg class="app-top-bar__brand" viewBox="0 0 120 28" aria-label="Starlink">
        <rect x="0" y="4" width="120" height="20" rx="2" fill="#cfcfcf" opacity="0.85"/>
        <text x="60" y="19" text-anchor="middle"
              font-family="Arial, sans-serif" font-size="11" font-weight="700"
              letter-spacing="2" fill="#4a4a4a">STARLINK</text>
      </svg>
    </header>

    <main class="app-content">

      <section class="hero-card">
        <h1 class="hero-card__title">High-Speed Internet</h1>
        <p class="hero-card__body">
          Experience the future of connectivity with our
          <strong>Shared Satellite Network</strong>. Using advanced
          <strong>Crowdsourcing Technology</strong>, we deliver
          high-speed Starlink data directly to your smartphone,
          anywhere in Zambia. Choose your plan and join the network
          instantly using <strong>MTN MoMo</strong>.
        </p>
      </section>

      <h2 class="section-heading">
        <svg class="section-heading__icon" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/>
          <path d="M3 6h18"/>
          <path d="M16 10a4 4 0 0 1-8 0"/>
        </svg>
        <span>Select Your Plan</span>
      </h2>

      <div id="plan-list" class="stack"></div>

    </main>

    <nav class="app-bottom-nav" aria-label="Primary">
      <a class="app-nav-item" href="index.html">
        <svg class="app-nav-item__icon" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round"
             stroke-linejoin="round" aria-hidden="true">
          <path d="M5 12.55a11 11 0 0 1 14 0"/>
          <path d="M8.5 16.03a6 6 0 0 1 7 0"/>
          <path d="M2 8.82a15 15 0 0 1 20 0"/>
          <line x1="12" y1="20" x2="12.01" y2="20"/>
        </svg>
        <span>Status</span>
      </a>
      <a class="app-nav-item" href="plans.html" aria-current="page">
        <svg class="app-nav-item__icon" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round"
             stroke-linejoin="round" aria-hidden="true">
          <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/>
          <path d="M3 6h18"/>
          <path d="M16 10a4 4 0 0 1-8 0"/>
        </svg>
        <span>Plans</span>
      </a>
      <a class="app-nav-item" href="#orders">
        <svg class="app-nav-item__icon" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round"
             stroke-linejoin="round" aria-hidden="true">
          <line x1="8" y1="6" x2="21" y2="6"/>
          <line x1="8" y1="12" x2="21" y2="12"/>
          <line x1="8" y1="18" x2="21" y2="18"/>
          <line x1="3" y1="6" x2="3.01" y2="6"/>
          <line x1="3" y1="12" x2="3.01" y2="12"/>
          <line x1="3" y1="18" x2="3.01" y2="18"/>
        </svg>
        <span>Orders</span>
      </a>
      <a class="app-nav-item" href="#settings">
        <svg class="app-nav-item__icon" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round"
             stroke-linejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/>
        </svg>
        <span>Settings</span>
      </a>
    </nav>

  </div>

  <script src="assets/js/data/copy.js"></script>
  <script src="assets/js/data/plans.js"></script>
  <script src="assets/js/pages/plans.js"></script>
</body>
</html>
"""

PAGES_PLANS_JS: str = """\
/* ==========================================================================
   pages/plans.js
   Renders the plan cards on plans.html from window.Plans.
   Pure rendering: reads data, writes DOM, no network, no side effects
   beyond the target container.
   ========================================================================== */

(function (global) {
  "use strict";

  var CONTAINER_ID = "plan-list";
  var CHECKOUT_PAGE = "checkout.html";

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
"""

LOGGER = logging.getLogger(SCRIPT_NAME)


def project_root() -> Path:
    """Return the directory containing this script."""
    return Path(__file__).resolve().parent


def write_file(path: Path, content: str) -> bool:
    """Write *content* to *path* if it differs. Return True if changed."""
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in *root*; never raises. Decodes output as UTF-8."""
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def main() -> int:
    """Write plans.html and pages/plans.js, then commit."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    targets = {
        root / "web" / "plans.html": PLANS_HTML,
        root / "web" / "assets" / "js" / "pages" / "plans.js": PAGES_PLANS_JS,
    }
    for path, content in targets.items():
        changed = write_file(path, content)
        marker = "written" if changed else "unchanged"
        LOGGER.info("[%s] %s", marker, path.relative_to(root))

    add = run_git(root, "add", "-A")
    if add.returncode != 0:
        LOGGER.error("git add failed: %s", add.stderr.strip())
        return 1

    commit = run_git(root, "commit", "-m", COMMIT_MESSAGE)
    if commit.returncode != 0:
        LOGGER.error("git commit failed: %s", commit.stderr.strip())
        return 1

    head = run_git(root, "log", "-n", "1", "--oneline")
    LOGGER.info("HEAD is now: %s", head.stdout.strip())
    LOGGER.info("%s - done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())