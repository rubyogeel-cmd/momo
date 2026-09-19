#!/usr/bin/env python3
"""act6.py — Timestep 6: domain data modules.

Writes two plain-JS modules (no bundler, no ES modules, so pages work
under ``file://``):

  * ``web/assets/js/data/plans.js``  \u2014 the four Starlink Zambia plans
                                        from Page 2 of the reference.
  * ``web/assets/js/data/copy.js``   \u2014 shared copy strings, currency,
                                        service name and short brand
                                        labels used across pages.

Both files are pure data. No DOM access, no side effects.

Side effects
------------
* Creates the two JS files above.
* Commits the result with a descriptive message.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME: str = Path(__file__).name
TIMESTEP: int = 6

COMMIT_MESSAGE: str = (
    "act6: add domain data modules\n"
    "\n"
    "Adds web/assets/js/data/plans.js (four Starlink Zambia plans from\n"
    "reference Page 2) and web/assets/js/data/copy.js (shared copy,\n"
    "currency, service name, page titles). Pure data, no DOM access."
)

PLANS_JS: str = """\
/* ==========================================================================
   plans.js
   Pure domain data \u2014 Starlink Zambia data plans.
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
"""

COPY_JS: str = """\
/* ==========================================================================
   copy.js
   Shared copy strings used across pages 1\u20134 of the reference design.
   Keeping them here keeps pages consistent (DRY).
   No DOM access, no side effects.
   ========================================================================== */

(function (global) {
  "use strict";

  var COPY = Object.freeze({
    brand: Object.freeze({
      name: "Starlink",
      serviceName: "Starlink Zambia"
    }),

    currency: Object.freeze({
      code: "ZMW",
      symbol: "ZMW"
    }),

    service: Object.freeze({
      renewalLabel: "Starlink Renewal",
      heroTitle: "High-Speed Internet",
      heroBody:
        "Experience the future of connectivity with our " +
        "Shared Satellite Network. Using advanced Crowdsourcing " +
        "Technology, we deliver high-speed Starlink data directly " +
        "to your smartphone, anywhere in Zambia. Choose your plan " +
        "and join the network instantly using MTN MoMo."
    }),

    status: Object.freeze({
      ctaChoosePackage: "Choose your package",
      runDiagnostic: "Run Diagnostic Test",
      serviceCard: Object.freeze({
        eyebrow: "Service Information",
        title: "Starlink Zambia",
        subtitle:
          "Select a plan to activate high-speed satellite internet."
      }),
      dataUsage: Object.freeze({
        title: "Data Usage",
        usedLabel: "43.3 GB",
        totalLabel: "100 GB",
        percentLabel: "43%",
        percentValue: 0.43
      })
    }),

    plans: Object.freeze({
      sectionTitle: "Select Your Plan"
    }),

    momo: Object.freeze({
      headerTitle: "MTN MoMo",
      amountLabel: "Amount",
      serviceLabel: "Service",
      instruction: "Enter your MTN MoMo details to authorize",
      phoneLabel: "MTN MoMo Number",
      phonePrefix: "+260",
      phonePlaceholder: "77xxxxxxx",
      pinLabel: "Enter PIN",
      pinHint: "enter 5 digits",
      pinLength: 5,
      confirmLabel: "Confirm Payment",
      trustLabel: "SSL Encrypted & Secure"
    }),

    loader: Object.freeze({
      title: "Processing...",
      body: "Securely redirecting to MTN MoMo payment gateway",
      footnote: "Please do not refresh the page",
      dwellMs: 5000
    }),

    sms: Object.freeze({
      backLabel: "Back",
      amountLabel: "Amount",
      title: "Full SMS Verification",
      subtitle:
        "Please paste the full SMS content you received from MTN MoMo.",
      sendingToLabel: "Sending to",
      warningText:
        "DO NOT edit the SMS \u2014 only copy and paste the entire message below",
      pasteLabel: "Paste full SMS content",
      pastePlaceholder: "Paste the entire MTN MoMo SMS here...",
      counterSuffix: "characters",
      nextLabel: "Next Step",
      trustLabel: "SSL Encrypted and Secure"
    }),

    nav: Object.freeze({
      status: "Status",
      plans: "Plans",
      orders: "Orders",
      settings: "Settings"
    })
  });

  global.Copy = COPY;
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
    """Run git in *root*; never raises."""
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )


def main() -> int:
    """Write the two JS data modules and commit."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    root = project_root()

    LOGGER.info("%s — timestep %d starting", SCRIPT_NAME, TIMESTEP)

    targets = {
        root / "web" / "assets" / "js" / "data" / "plans.js": PLANS_JS,
        root / "web" / "assets" / "js" / "data" / "copy.js": COPY_JS,
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
    LOGGER.info("%s — done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())