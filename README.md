# Momo

Mobile-first web experience for the Starlink Zambia data reseller
flow: choose a plan, pay via MTN MoMo, verify by SMS.

## Quick start

Open the preview to see all four screens side by side:

    start preview.html           # Windows
    open preview.html            # macOS
    xdg-open preview.html        # Linux

Or open any screen directly:

    web/index.html               Status dashboard
    web/plans.html               Plan catalogue
    web/checkout.html?plan=premium
    web/sms.html?plan=premium&phone=079764645

No build step. No bundler. No runtime dependencies.

## Pages

    1.  /status      Status dashboard          web/index.html
    2.  /plans       Plan catalogue            web/plans.html
    3.  /checkout    MTN MoMo gateway          web/checkout.html
    4.  /sms         Full SMS verification     web/sms.html

Between pages 2 and 3, tapping a plan card shows a ~5 s MoMo
redirect loader before navigating.

## Layout

    preview.html       Four-screen viewer for Chrome
    web/               Static site
      index.html       Status dashboard
      plans.html       Plan catalogue
      checkout.html    MoMo gateway
      sms.html         SMS verification
      assets/
        css/           tokens, base, components
        js/
          data/        plans.js, copy.js
          pages/       one module per page
    tests/             Test suite (added in a later act)
    docs/              Architecture notes
    config/            Project-wide configuration
    scripts/           Developer tooling

## How changes are made

The site is built up across numbered timestep scripts
(``act1.py``, ``act2.py``, ...). Each script does one incremental
change and commits itself with a descriptive message, so
``git reflog -a`` is a replayable log of how the project was built.
