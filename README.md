# Instagram Unfollowers Tracker

A self-hosted Docker container that tracks your Instagram followers, detects who unfollows you, and sends notifications to Home Assistant.

Built with **FastAPI** (Python) backend and **React + TypeScript** frontend. Designed for home server deployment via Docker Compose.

---

## Features

- **Single throwaway login, many tracked profiles** — Log in **once** with a secondary Instagram account; that session is then reused to scan any number of *tracked* profiles (your main, your partner's, etc.) **without ever logging them in**. Only the throwaway account is exposed to the tool, so if anything goes wrong only the throwaway is at risk.
- **In-browser fetches (no httpx)** — All Instagram API calls are made from inside the live Chromium tab via `page.evaluate()`, so the requests carry a real Chrome TLS/JA3 fingerprint, real `sec-ch-ua-*` hints, and the matching User-Agent. This avoids the "we detected unusual activity" flagging that hits server-side scrapers.
- **Follow-relationship check** — A tracked account can only be added (and scanned) if the logged-in account follows it. The scan refuses to run otherwise.
- **Retry-until-complete pagination** — Instagram's followers/following endpoint returns a re-ranked, partial list per call. Each scan fetches the canonical follower/following count up-front, then paginates repeatedly (up to 30 attempts, ~10–30 s cool-off between) unioning unique IDs until the count is reached or the list plateaus. Partial captures are still saved with a warning; the diff proceeds so you're never blocked on a "one user short" plateau.
- **Browser-based login** — Log into Instagram through the dashboard with full support for 2FA and security challenges
- **Historical snapshots** — Stores follower history in SQLite to detect changes over time
- **Unfollower detection** — Identifies who unfollowed and when, with a permanent log per tracked account
- **Whitelist system** — Mark accounts (celebrities, brands) as "OK to not follow back" and filter them out of your view
- **Manual + scheduled scans** — Trigger updates manually or on a schedule (daily at specific time, every X hours, or both)
- **Home Assistant integration** — Sends a webhook with new unfollowers' usernames so HA can push to your phone
- **Web dashboard** — Clean React interface accessible on your home network

---

## Quick Start

### Prerequisites

- Docker & Docker Compose installed
- A Home Assistant instance (optional, for notifications)

### Installation

1. Clone this repository to your server (e.g., `/opt/`):
   ```bash
   cd /opt && git clone https://github.com/lvolcov/instagram-unfollowers-tracker.git
   cd instagram-unfollowers-tracker
   ```

2. Copy the environment template and configure it:
   ```bash
   cp .env.example .env
   nano .env
   ```

3. Start the container:
   ```bash
   docker compose up -d
   ```

4. Open the dashboard at `http://YOUR_SERVER_IP:8000` (or whatever port you set)

5. Click **"Log in"** and authenticate with a **throwaway / secondary** Instagram account (do **not** use your main). Complete any 2FA. The session is encrypted and saved.

6. Click **"Add tracked account"** and enter the Instagram handle you want to track (e.g. your main). The tool verifies the throwaway is following that profile, then starts scanning. Add as many tracked accounts as you like — they never authenticate through the tool.

---

## Configuration

All configuration is done via the `.env` file:

| Variable | Default | Description |
|---|---|---|
| `APP_PORT` | `8000` | Port to expose the dashboard on |
| `HA_WEBHOOK_URL` | `http://homeassistant.local:8123` | Base URL of your Home Assistant instance |
| `HA_WEBHOOK_ID` | `instagram_unfollowers` | The webhook ID configured in Home Assistant |
| `SECRET_KEY` | (generate one) | Used to encrypt stored Instagram sessions at rest |
| `TIMEZONE` | `UTC` | Timezone for scheduled scans (e.g., `Europe/London`) |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

See `.env.example` for the full list.

---

## Home Assistant Integration

### 1. Create a webhook automation in Home Assistant

In `configuration.yaml` or via the UI, create an automation triggered by a webhook:

```yaml
automation:
  - alias: "Instagram Unfollowers Notification"
    trigger:
      - platform: webhook
        webhook_id: instagram_unfollowers
        allowed_methods:
          - POST
        local_only: true
    action:
      - service: notify.mobile_app_YOUR_PHONE
        data:
          title: "New Instagram Unfollowers ({{ trigger.json.account }})"
          message: "{{ trigger.json.unfollowers | join(', ') }}"
```

### 2. Webhook payload format

The container sends a POST to `{HA_WEBHOOK_URL}/api/webhook/{HA_WEBHOOK_ID}` with this body:

```json
{
  "account": "your_instagram_handle",
  "unfollowers": ["user1", "user2", "user3"],
  "count": 3,
  "detected_at": "2026-05-18T14:30:00Z"
}
```

Only fires when **new** unfollowers are detected.

---

## Adding to Your Existing Docker Compose

If you already have a `docker-compose.yml` on your server and want to merge this container in, add this service block:

```yaml
services:
  instagram-tracker:
    build: ./instagram-unfollowers-tracker
    container_name: instagram-tracker
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./instagram-unfollowers-tracker/data:/app/data
    env_file:
      - ./instagram-unfollowers-tracker/.env
```

Or pull the pre-built image (once published):

```yaml
services:
  instagram-tracker:
    image: ghcr.io/YOUR_USERNAME/instagram-unfollowers-tracker:latest
    container_name: instagram-tracker
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - instagram_tracker_data:/app/data
    env_file:
      - .env

volumes:
  instagram_tracker_data:
```

---

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full technical design.

**TL;DR**:
- **Backend**: FastAPI + SQLAlchemy + APScheduler + Playwright (login **and** every scan API call runs through a real Chromium tab on Xvfb).
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS
- **Database**: SQLite (file at `/app/data/tracker.db`) — one `LoginAccount` row, many `TrackedAccount` rows
- **Container**: Single Docker image, multi-stage build, exposes one port (noVNC streamed at `/novnc` for the login window)

---

## Project Structure

```
instagram-unfollowers-tracker/
├── README.md
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
├── docs/
│   ├── ARCHITECTURE.md      # Full technical design
│   ├── API.md               # API endpoint reference
│   └── ROADMAP.md           # Planned features
├── backend/
│   ├── requirements.txt
│   ├── main.py              # FastAPI entrypoint
│   └── app/
│       ├── api/v1/          # REST endpoints (accounts, followers, schedule, etc.)
│       ├── core/            # Config, database, security
│       ├── models/          # SQLAlchemy ORM models
│       ├── schemas/         # Pydantic request/response schemas
│       ├── services/        # Business logic (scanning, comparison, webhooks)
│       └── instagram/       # Instagram API client (Playwright + GraphQL)
└── frontend/
    ├── package.json
    ├── index.html
    ├── vite.config.ts
    └── src/
        ├── App.tsx
        ├── main.tsx
        ├── pages/           # Dashboard, AccountDetail, Settings, Login
        ├── components/      # UI primitives + feature components
        ├── hooks/           # Custom React hooks
        ├── services/        # API client
        ├── contexts/        # React contexts (auth, accounts)
        └── types/           # TypeScript types
```

---

## Development

### Run locally without Docker

**Backend**:
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload --port 8000
```

**Frontend**:
```bash
cd frontend
npm install
npm run dev
```

The frontend dev server proxies `/api` requests to the backend.

### Run inside Docker for development

```bash
docker compose -f docker-compose.dev.yml up --build
```

---

## Credit

Inspired by [InstagramUnfollowers](https://github.com/davidarroyo1234/InstagramUnfollowers) by David Arroyo — that browser-based tool was the proof-of-concept that showed Instagram's GraphQL approach works reliably. This project containerizes the same approach for self-hosted automation.

---

## Disclaimer

This tool is not affiliated with, authorized by, or endorsed by Instagram or Meta. Automating Instagram interactions may violate Instagram's Terms of Service. Use at your own risk — the maintainers accept no responsibility for account suspensions or bans.

The tool fetches data via Instagram's own REST endpoint (`/api/v1/friendships/`) executed from inside a real Chrome tab, with bookmarklet-style jitter, to minimise rate-limiting and detection. To further reduce risk, **only the throwaway account ever authenticates** — your main account is only ever *observed*, never logged in. No automation tool is 100% safe.

---

## License

MIT — see [LICENSE](LICENSE)
