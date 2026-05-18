# Architecture

This document describes the technical design of the Instagram Unfollowers Tracker.

---

## High-Level Overview

```
┌──────────────────────────────────────────────────────────────┐
│  Docker Container                                            │
│                                                              │
│  ┌────────────────┐         ┌─────────────────────────┐      │
│  │  React (Vite)  │ ─AJAX─► │  FastAPI (uvicorn)      │      │
│  │  static files  │         │  ├── REST API (/api/v1) │      │
│  │  served by     │         │  ├── APScheduler        │      │
│  │  FastAPI       │         │  └── Playwright client  │      │
│  └────────────────┘         └─────────┬───────────────┘      │
│                                       │                      │
│                              ┌────────▼──────────┐           │
│                              │  SQLite DB        │           │
│                              │  (/app/data/)     │           │
│                              └───────────────────┘           │
│                                       │                      │
│                              ┌────────▼──────────┐           │
│                              │  Playwright       │           │
│                              │  (Chromium)       │           │
│                              │  for IG login     │           │
│                              └───────────────────┘           │
└──────────────────────────────────────────────────────────────┘
              │                                  │
              ▼                                  ▼
   ┌──────────────────┐                ┌─────────────────────┐
   │  Home Assistant  │ ◄── webhook ── │  Instagram GraphQL  │
   │   (your LAN)     │                │  (after auth)       │
   └──────────────────┘                └─────────────────────┘
```

---

## Tech Stack

### Backend
- **FastAPI 0.115+** — Async REST API framework
- **SQLAlchemy 2.0** — ORM (async mode)
- **SQLite** — Single-file database, perfect for self-hosted
- **APScheduler 3.x** — Job scheduling with SQLAlchemy persistence
- **Playwright** — Chromium automation for Instagram login (handles 2FA, challenges)
- **httpx** — Async HTTP client for GraphQL API calls + Home Assistant webhooks
- **Pydantic v2** — Request/response validation
- **cryptography** — Fernet encryption for stored Instagram sessions
- **python-jose** — JWT for dashboard sessions (if we add auth later)

### Frontend
- **React 18** — UI framework
- **TypeScript 5** — Type safety
- **Vite 5** — Build tool & dev server
- **Tailwind CSS 3** — Utility-first styling
- **shadcn/ui** — Accessible component primitives (Radix UI under the hood)
- **TanStack Query (React Query) 5** — Server state management
- **React Router 6** — Routing
- **Axios** — HTTP client
- **date-fns** — Date utilities

### Container
- **Multi-stage Dockerfile**: Stage 1 builds the frontend, Stage 2 builds the Python backend with the static frontend bundled in.
- **Base image**: `mcr.microsoft.com/playwright/python:v1.49.0-jammy` (Playwright pre-installed with Chromium)
- **Single exposed port**: Configurable via `APP_PORT` env var (default 8000)
- **Volume**: `/app/data` for SQLite DB and Playwright user data dir

---

## Instagram Authentication Strategy

This is the trickiest piece. Instagram's login has multiple flows: password, 2FA via SMS/app, suspicious-login challenges, "is this you?" prompts, etc.

### Approach: Playwright with persistent context

1. **Initial Setup**: User clicks "Add Account" → backend launches a Chromium instance via Playwright in **headed mode** inside the container.
2. **Browser Access**: A **noVNC** sidecar (built into the same container) exposes the browser visually via the web dashboard. User logs into Instagram exactly as they would in a normal browser — handling 2FA, challenges, etc.
3. **Session Capture**: Once login succeeds (detected by URL change to `/`), Playwright saves the storage state (cookies + localStorage) to an encrypted file under `/app/data/sessions/{account_id}.json`.
4. **Subsequent Scans**: For automated scans, Playwright launches in **headless mode** with the saved storage state. It opens `instagram.com`, extracts the `ds_user_id` / `sessionid` / `csrftoken` cookies, and uses `httpx` to call Instagram's GraphQL API directly (same endpoint as the original tool).
5. **Session Refresh**: If a request returns 401/403, the scheduler pauses scans for that account and marks it as "needs re-login" in the dashboard.

### Why this approach?
- **Matches the user's "log in like normal" requirement** — Instagram sees a real browser with a real human typing the password and entering 2FA codes.
- **Robust against challenges** — Instagram's "suspicious login" prompts work because the browser is real.
- **Efficient for ongoing scans** — Once logged in, we use lightweight GraphQL calls instead of full browser navigation.
- **Sessions persist** — Instagram sessions typically last weeks/months as long as you don't trigger re-auth.

### Alternative considered: `instagrapi`
Pure-Python Instagram Private API client. Rejected because:
- Uses the mobile API (different headers, more likely to flag as bot)
- Doesn't handle Instagram's web-based challenge flows as naturally
- The original repo's GraphQL approach is proven to work reliably

---

## Database Schema

SQLite database at `/app/data/tracker.db`. Schema managed by Alembic migrations.

### `accounts`
Tracked Instagram accounts.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `instagram_user_id` | TEXT UNIQUE | The numeric IG user ID (`ds_user_id`) |
| `username` | TEXT | `@handle` |
| `display_name` | TEXT | Full name as shown on IG |
| `profile_pic_url` | TEXT | |
| `session_path` | TEXT | Path to encrypted Playwright storage state |
| `session_status` | TEXT | `active` / `needs_relogin` / `expired` |
| `created_at` | DATETIME | |
| `last_scan_at` | DATETIME | |

### `snapshots`
Each scan produces a snapshot of the full followers + following lists.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `account_id` | INTEGER FK | → `accounts.id` |
| `taken_at` | DATETIME | |
| `followers_count` | INTEGER | |
| `following_count` | INTEGER | |
| `status` | TEXT | `running` / `completed` / `failed` |
| `error_message` | TEXT NULL | |

### `snapshot_users`
The actual user list inside each snapshot. Composite for both followers and following.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `snapshot_id` | INTEGER FK | → `snapshots.id` |
| `instagram_user_id` | TEXT | |
| `username` | TEXT | |
| `full_name` | TEXT | |
| `profile_pic_url` | TEXT | |
| `is_verified` | BOOLEAN | |
| `is_private` | BOOLEAN | |
| `relationship` | TEXT | `follower` / `following` / `mutual` |

Indexed on `(snapshot_id, instagram_user_id)` for fast diffing.

### `unfollowers`
Permanent log of detected unfollowers across all time.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `account_id` | INTEGER FK | |
| `instagram_user_id` | TEXT | |
| `username` | TEXT | Last known username |
| `full_name` | TEXT | |
| `profile_pic_url` | TEXT | |
| `detected_at` | DATETIME | When we noticed they unfollowed |
| `first_seen_at` | DATETIME | First snapshot where they appeared as follower |
| `notified` | BOOLEAN | Whether HA webhook was fired for this entry |

### `whitelist`
Accounts the user has marked as "OK to not follow back".

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `account_id` | INTEGER FK | |
| `instagram_user_id` | TEXT | |
| `username` | TEXT | |
| `added_at` | DATETIME | |
| `note` | TEXT NULL | Optional user note ("celebrity", "brand", etc.) |

### `schedules`
Scheduling config per account.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `account_id` | INTEGER FK | |
| `mode` | TEXT | `daily_at` / `interval_hours` / `manual_only` |
| `daily_time` | TEXT NULL | `HH:MM` if mode=`daily_at` |
| `interval_hours` | INTEGER NULL | If mode=`interval_hours` |
| `enabled` | BOOLEAN | |
| `next_run_at` | DATETIME NULL | Computed |

### `app_settings`
Singleton table for global config not in env vars.

| Column | Type | Notes |
|---|---|---|
| `key` | TEXT PK | |
| `value` | TEXT | |

---

## Scanning & Diff Logic

When a scan runs (manual or scheduled):

1. **Lock account** — set `accounts.session_status` to `scanning` so concurrent scans can't collide.
2. **Open Playwright** with stored session.
3. **Verify session** by visiting `instagram.com/accounts/edit`. If redirected to `/accounts/login`, mark `needs_relogin` and abort.
4. **Fetch followers** via GraphQL pagination (same query hash as original tool).
5. **Fetch following** via GraphQL pagination.
6. **Persist snapshot** — write `snapshots` row + bulk-insert `snapshot_users`.
7. **Diff against previous snapshot**:
   - `new_unfollowers = previous.followers - current.followers`
   - Insert each into `unfollowers` table (skip if already there from previous detection).
8. **Fire webhook** if `new_unfollowers` is non-empty AND `notified=false`. On success, set `notified=true`.
9. **Cleanup** — keep last N snapshots (configurable, default 30), prune older `snapshot_users` rows.

### Diff edge cases
- **Username changed** — Match by `instagram_user_id`, not `username`.
- **Account deleted** — Treat as unfollow (they're not in followers list anymore).
- **Account went private** — Still in followers list, no change.
- **You unfollowed them** — Doesn't appear in `unfollowers` (they're not in your `following` list either).

---

## Scheduling

Powered by APScheduler with SQLAlchemy job store, so jobs persist across container restarts.

**Three scheduling modes per account**:
1. **Daily at time** — e.g., "9:00 AM in `Europe/London`"
2. **Interval hours** — e.g., "every 6 hours"
3. **Manual only** — no automation

A background task reconciles `schedules` rows with APScheduler on startup and whenever a schedule is updated via the API.

**Manual trigger** is always available regardless of schedule — POST to `/api/v1/accounts/{id}/scan` enqueues an immediate one-off job.

---

## Home Assistant Webhook

Fires after a scan detects new unfollowers.

**URL**: `{HA_WEBHOOK_URL}/api/webhook/{HA_WEBHOOK_ID}`
**Method**: POST
**Content-Type**: `application/json`
**Body**:
```json
{
  "account": "your_handle",
  "unfollowers": ["user1", "user2"],
  "count": 2,
  "detected_at": "2026-05-18T14:30:00Z"
}
```

- Retries up to 3 times with exponential backoff if HA is unreachable.
- After 3 failures, marks the `unfollowers` rows as `notified=false` and logs a warning. Dashboard shows a banner if HA is unreachable.
- A "Test Webhook" button in Settings fires a dummy payload so the user can verify HA is wired up correctly.

---

## Frontend Architecture

```
src/
├── main.tsx                    # Entry — React root, providers
├── App.tsx                     # Router + layout shell
├── pages/
│   ├── Dashboard.tsx           # Overview across all accounts
│   ├── AccountDetail.tsx       # Per-account view (followers, unfollowers, whitelist)
│   ├── AddAccount.tsx          # Login flow with noVNC iframe
│   ├── Settings.tsx            # Global settings + webhook test
│   └── UnfollowerHistory.tsx   # Permanent unfollower log
├── components/
│   ├── ui/                     # shadcn primitives: Button, Card, Dialog, etc.
│   ├── layout/                 # Header, Sidebar, AppShell
│   ├── accounts/               # AccountCard, AccountSwitcher
│   ├── followers/              # FollowerList, FollowerCard, FilterBar
│   ├── login/                  # NoVNCFrame, LoginStatus
│   └── settings/               # ScheduleEditor, WebhookSettings
├── hooks/
│   ├── useAccounts.ts          # React Query hook for /api/v1/accounts
│   ├── useScan.ts              # Mutation hook for triggering scans
│   └── useWebSocket.ts         # Live scan progress via WS
├── services/
│   └── api.ts                  # Axios client + endpoint functions
├── contexts/
│   └── AccountContext.tsx      # Currently selected account
└── types/
    └── api.ts                  # Generated from OpenAPI schema (optional)
```

### Key UX flows

**Adding an account**:
1. Click "Add Account" → backend spawns Playwright + noVNC session, returns session ID.
2. Frontend embeds noVNC iframe pointing at the session.
3. User logs into Instagram in the iframe (handles 2FA naturally).
4. Backend detects successful login via URL polling, stores session, returns account info.
5. Frontend closes iframe and refreshes account list.

**Viewing non-followers**:
1. Account detail page shows list of "people you follow who don't follow you back".
2. Toggle "Hide whitelisted" filter.
3. Each row has a star button to toggle whitelist status.
4. Each row links to the IG profile in a new tab.

**Editing schedule**:
1. Schedule editor on account detail page.
2. Radio: Daily at time / Every X hours / Manual only.
3. Saving updates `schedules` row + APScheduler job.

---

## Security Considerations

- **Sessions encrypted at rest** with Fernet using `SECRET_KEY` env var.
- **No dashboard auth by default** — assumes the dashboard is only accessible on your trusted LAN. Future enhancement: add HTTP Basic auth via env var.
- **No external services** — all data stays on your server. Only outbound calls are to Instagram (auth required) and your Home Assistant.
- **CORS** locked to same-origin in production.
- **Rate limiting on Instagram calls** — uses same timing constants as the original tool (configurable per-account in settings).

---

## Deployment

### Single container (default)
- `docker compose up -d`
- Frontend served as static files by FastAPI
- noVNC accessible at `/novnc/*` via reverse proxy inside the container

### Resource requirements
- **RAM**: ~500 MB (mostly Chromium when scanning)
- **CPU**: Negligible when idle, spikes briefly during scans
- **Disk**: ~1 GB for the image + ~10 MB for a year of snapshot data

---

## Future Enhancements

See [ROADMAP.md](ROADMAP.md) for the phased plan.

Quick list:
- Notification channels beyond HA (Telegram, Discord, ntfy.sh)
- Track *new followers* in addition to unfollowers
- "Ghost follower" detection (accounts that never interact)
- Bulk unfollow feature (port from original tool)
- Statistics & charts (follower growth over time)
- Mobile-responsive PWA install
