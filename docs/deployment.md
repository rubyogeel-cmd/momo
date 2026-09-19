# Deploying to Render

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
