#!/usr/bin/env python3
"""act15.py - Telegram foundation (single-module backend).

Writes the minimal foundation for the Telegram integration:

  * backend/__init__.py
  * backend/telegram.py       -- config + session state + Bot API client
  * config/telegram.example.json
  * config/telegram.json      -- seeded empty, git-ignored
  * docs/telegram.md
  * .gitignore                -- adds config/telegram.json

No frontend or server changes yet; those come in later acts.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME = Path(__file__).name
TIMESTEP = 15

COMMIT_MESSAGE = """act15: telegram foundation

Adds a single-module backend (backend/telegram.py) providing config
loading, a thread-safe in-memory session store, and a stdlib-only
Telegram Bot API client. Adds config/telegram.example.json and
docs/telegram.md, git-ignores config/telegram.json and seeds it empty.
No frontend wiring yet."""

BACKEND_INIT = '''"""Momo backend: Telegram integration for the onboarding flow."""
'''

BACKEND_TELEGRAM = '''"""Telegram integration: config, session state, and Bot API client.

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
'''

TELEGRAM_EXAMPLE_JSON = '''{
  "bot_token": "PUT_YOUR_BOT_TOKEN_HERE",
  "chat_id": "PUT_YOUR_CHAT_ID_HERE"
}
'''

TELEGRAM_SEED_JSON = '''{
  "bot_token": "",
  "chat_id": ""
}
'''

DOCS_TELEGRAM = '''# Telegram integration

The onboarding flow notifies you (the operator) via a Telegram bot
whenever a user crosses a checkpoint, and lets you approve or reject
the flow by tapping inline buttons.

## 1. Create a bot

1. Open Telegram and message @BotFather.
2. Send /newbot and follow the prompts.
3. Copy the bot token you receive.

## 2. Find your chat id

1. Send any message to your new bot (for example, "hi").
2. Visit https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   in a browser.
3. Copy the value at result[0].message.chat.id.

## 3. Configure

Copy config/telegram.example.json to config/telegram.json and fill in
both values:

    {
      "bot_token": "123456789:ABC-DEF...",
      "chat_id": "123456789"
    }

config/telegram.json is git-ignored and must never be committed.

## 4. Checkpoints

The bot sends a message at each checkpoint:

    1. Onboarding - user taps a plan on page 2. No buttons.
    2. PIN + phone - user confirms on page 3.
       Buttons: Approve PIN / Reject PIN.
    3. OTP SMS - user submits the pasted SMS.
       Buttons: Approve OTP / Reject OTP.

Buttons carry the session id, so pressing them applies to the correct
user regardless of message order.

## 5. Operator actions

* Approve PIN -> the user goes to the SMS verification page.
* Reject PIN  -> the user returns to page 3 with an error; the phone
                 is kept and the PIN cleared.
* Approve OTP -> the user sees the success page with a reference
                 number and thank-you copy.
* Reject OTP  -> the user sees "invalid confirmation message, please
                 wait for a new one and try again".
'''

GITIGNORE_APPEND = """
# Local Telegram credentials
config/telegram.json
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


def seed_if_missing(path: Path, content: str) -> bool:
    """Create *path* with *content* only if it does not already exist."""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def append_if_missing(path: Path, block: str) -> bool:
    """Append *block* to *path* once. Return True if changed."""
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if "config/telegram.json" in existing:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(existing + block, encoding="utf-8", newline="\n")
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
    """Write the foundation files, update .gitignore, commit."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout
    )
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    files = {
        root / "backend" / "__init__.py": BACKEND_INIT,
        root / "backend" / "telegram.py": BACKEND_TELEGRAM,
        root / "config" / "telegram.example.json": TELEGRAM_EXAMPLE_JSON,
        root / "docs" / "telegram.md": DOCS_TELEGRAM,
    }
    for path, content in files.items():
        changed = write_file(path, content)
        marker = "written" if changed else "unchanged"
        LOGGER.info("[%s] %s", marker, path.relative_to(root))

    gitignore = root / ".gitignore"
    changed = append_if_missing(gitignore, GITIGNORE_APPEND)
    LOGGER.info("[%s] .gitignore", "updated" if changed else "unchanged")

    seed_path = root / "config" / "telegram.json"
    if seed_if_missing(seed_path, TELEGRAM_SEED_JSON):
        LOGGER.info(
            "[seeded ] %s (git-ignored - fill in your values)",
            seed_path.relative_to(root),
        )
    else:
        LOGGER.info("[exists ] %s", seed_path.relative_to(root))

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
    LOGGER.info("")
    LOGGER.info(
        "Next: edit %s with your bot_token and chat_id.",
        seed_path.relative_to(root),
    )
    LOGGER.info("See docs/telegram.md for how to get them.")
    LOGGER.info("%s - done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())