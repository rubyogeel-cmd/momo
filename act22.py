#!/usr/bin/env python3
"""act22.py - Bind to LAN so the phone can reach the server.

Three changes to backend/server.py:
  1. Add a get_lan_ip() helper.
  2. Change the default host from 127.0.0.1 to 0.0.0.0 so the server
     accepts connections from other devices on the same Wi-Fi.
  3. Print the LAN URL at startup so it is obvious what to type on
     the phone.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME = Path(__file__).name
TIMESTEP = 22

COMMIT_MESSAGE = """act22: bind to LAN for phone testing

Adds a get_lan_ip() helper and changes the default host to 0.0.0.0 so
the local server is reachable from a phone on the same Wi-Fi. Prints
the LAN URL at startup."""

OLD_SERVE = '''\
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

NEW_SERVE = '''\
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
'''

LOGGER = logging.getLogger(SCRIPT_NAME)


def project_root() -> Path:
    """Return the directory containing this script."""
    return Path(__file__).resolve().parent


def read_text(path: Path) -> str:
    """Return UTF-8 text, or '' if the file does not exist."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 with LF endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: Path, old: str, new: str) -> str:
    """Replace *old* with *new* once. Return a short status."""
    text = read_text(path)
    if not text:
        return "missing-file"
    if old not in text:
        if new in text:
            return "already"
        return "no-match"
    write_text(path, text.replace(old, new, 1))
    return "replaced"


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
    """Apply the server patch and commit."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout
    )
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    server_py = root / "backend" / "server.py"
    LOGGER.info("[%s] %s (LAN bind)",
                replace_once(server_py, OLD_SERVE, NEW_SERVE),
                server_py.relative_to(root))

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
    LOGGER.info("Restart the server (Ctrl+C then 'py run_server.py').")
    LOGGER.info("Watch the startup log for the LAN URL to type on the phone.")
    LOGGER.info("%s - done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())