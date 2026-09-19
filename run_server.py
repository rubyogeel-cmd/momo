#!/usr/bin/env python3
"""Start the Momo local server.

Loads the Telegram config, starts the update polling thread, then
serves the static site and API on http://127.0.0.1:8000.

Open http://127.0.0.1:8000/preview.html to see all four screens.
Stop with Ctrl+C.
"""
from __future__ import annotations

import logging
import sys

from backend.server import _try_load_telegram, serve
from backend.polling import TelegramPoller


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )


def main() -> int:
    _configure_logging()
    logger = logging.getLogger("run_server")

    telegram, store = _try_load_telegram()
    poller: TelegramPoller | None = None

    if telegram is not None:
        poller = TelegramPoller(telegram, store)
        poller.start()
    else:
        logger.warning("Skipping Telegram poller (config missing)")

    try:
        serve()
    finally:
        if poller is not None:
            poller.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
