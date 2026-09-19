# Momo

Mobile-first web experience for the Starlink Zambia data reseller flow:
choose a plan, pay via MTN MoMo, verify by SMS.

## Status

Pre-alpha. The site is built up across numbered timestep scripts
(`act1.py`, `act2.py`, ...). Each script is self-contained, does one
incremental change, and commits itself so `git reflog -a` gives a
replayable history.

## Layout

    web/        Static site (HTML, CSS, JS) — open web/index.html
    tests/      Test suite (added in a later act)
    docs/       Architecture and design notes
    config/     Project-wide configuration
    scripts/    Developer tooling

## Running the site

    open web/index.html          # macOS
    start web\index.html         # Windows
    xdg-open web/index.html      # Linux

No build step, no bundler, no runtime dependencies.

## Pages

    1.  /            Status dashboard        web/index.html
    2.  /plans       Plan catalogue           web/plans.html
    3.  /checkout    MTN MoMo gateway         web/checkout.html
    4.  /sms         Full SMS verification    web/sms.html
