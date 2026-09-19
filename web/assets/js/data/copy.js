/* ==========================================================================
   copy.js
   Shared copy strings used across pages 1–4 of the reference design.
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

    paymentLoader: Object.freeze({
      title: "Processing Payment...",
      body: "Verifying your payment with MTN MoMo",
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
        "DO NOT edit the SMS — only copy and paste the entire message below",
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
