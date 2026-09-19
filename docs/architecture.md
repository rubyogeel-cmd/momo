# Architecture

## Goal

A mobile-first static site that reproduces the Starlink Zambia data
reseller flow end-to-end, with no build step and no runtime
dependencies, so it can be opened by double-clicking `web/index.html`.

## Layers

Presentation, domain data and behaviour stay in separate places even
though the site ships as a static bundle:

    web/
      *.html                    Structure only — no inline style, no inline JS
      assets/css/tokens.css     Design tokens (colour, spacing, type, radii)
      assets/css/base.css       Reset and app-shell primitives
      assets/css/components.css Reusable UI pieces (cards, buttons, nav)
      assets/js/data/           Domain data (plans, currency, copy)
      assets/js/                Behaviour modules, one per page

## Conventions

* Every HTML page includes the same stylesheet stack and the same
  bottom-navigation markup so navigation stays identical across routes.
* All colours, radii and spacings come from CSS custom properties in
  `tokens.css`. No raw hex values in the later CSS files.
* JS is written as plain scripts (not ES modules) so the pages load
  correctly under `file://`.

## Traceability

Every change is a self-contained `actn.py` committed with a descriptive
message. `git reflog -a` is the project's activity log.
