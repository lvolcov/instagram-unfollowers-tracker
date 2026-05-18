# Roadmap

Implementation is broken into **phases** so the project can ship something useful early and grow from there.

---

## Phase 0 — Project scaffolding ✅
*Where we are now.*

- Project structure created
- Architecture, API, and roadmap documented
- Docker config in place
- Backend and frontend skeletons ready
- README polished for GitHub publication

---

## Phase 1 — MVP: Single account, manual scans

**Goal**: Get the end-to-end loop working with one Instagram account. No scheduling, no webhook — just prove the auth + scan + diff + display pipeline works.

- [ ] `accounts` + `snapshots` + `snapshot_users` + `unfollowers` tables with Alembic migrations
- [ ] Playwright integration + session storage (encrypted)
- [ ] noVNC sidecar for browser-based login
- [ ] Login flow API endpoints (`/auth/login/start`, `/auth/login/status`)
- [ ] Instagram GraphQL client (followers + following pagination)
- [ ] Scan service (fetch + persist + diff)
- [ ] React: AddAccount page with noVNC iframe
- [ ] React: AccountDetail page showing followers + non-followers
- [ ] React: Manual "Scan now" button + live progress (WebSocket or polling)

**Done when**: I can log into my Instagram, click "Scan", and see my non-followers list in the dashboard.

---

## Phase 2 — Unfollower detection + Home Assistant webhook

**Goal**: Add the core "unfollower" detection and HA notification.

- [ ] `unfollowers` table populated by diff logic
- [ ] HA webhook service with retry + backoff
- [ ] Webhook fires on new unfollowers after a scan
- [ ] React: Unfollower history page
- [ ] Settings: webhook URL + ID configuration
- [ ] Settings: "Test webhook" button

**Done when**: I unfollow myself from another account, run a scan, and get a phone notification via HA.

---

## Phase 3 — Whitelist + filtering

**Goal**: Stop celebrities from cluttering my list.

- [ ] `whitelist` table
- [ ] CRUD endpoints
- [ ] React: Star button on each non-follower row
- [ ] React: "Hide whitelisted" filter toggle
- [ ] Import/export whitelist as JSON (compatible with original tool)

**Done when**: I can hide whitelisted accounts and only see the people I actually want to track.

---

## Phase 4 — Scheduling

**Goal**: Set it and forget it.

- [ ] `schedules` table
- [ ] APScheduler integration with SQLAlchemy job store
- [ ] CRUD endpoints for schedule
- [ ] React: Schedule editor UI (radio modes: daily / interval / manual)
- [ ] Scheduler reconciliation on startup

**Done when**: I configure "daily at 9 AM" and it runs without me touching anything.

---

## Phase 5 — Multi-account

**Goal**: Add my partner's account.

- [ ] Account switcher in header
- [ ] All views scoped to selected account
- [ ] Dashboard overview shows per-account stats
- [ ] Per-account schedule (each account can have its own schedule)
- [ ] Webhook payload already includes `account` field — verify HA automation handles multiple accounts cleanly
- [ ] Concurrent scan support (or queue if same machine resource-limited)

**Done when**: Both my and my partner's accounts are tracked independently with separate schedules and separate HA notifications.

---

## Phase 6 — Polish & GitHub release

**Goal**: Ship to GitHub for others to use.

- [ ] LICENSE file (MIT)
- [ ] CONTRIBUTING.md
- [ ] GitHub Actions workflow:
  - Lint (ruff, eslint)
  - Test (pytest, vitest)
  - Build Docker image
  - Publish to ghcr.io on tag
- [ ] Screenshots / demo GIF in README
- [ ] Example `configuration.yaml` snippet for HA in docs
- [ ] Tagged v0.1.0 release

---

## Future / Wishlist (post-1.0)

Nice-to-have features not blocking initial release:

### Notifications
- Telegram bot integration
- Discord webhook
- ntfy.sh / Gotify
- Generic webhook (configurable JSON template)

### Analytics
- Follower count over time chart
- Net follower change per week/month
- "Most active" unfollow days
- Heatmap of when unfollows happen

### Smart features
- **Ghost follower detection** — followers who never like/comment (would need Instagram permissions we may not have)
- **Mutual scan** — show who you and friend X both follow
- **New follower notifications** (not just unfollows)
- **Username change tracking** — keep a history of handle changes for tracked users

### Quality of life
- Mobile-responsive PWA install
- Dark/light mode toggle (default dark)
- Database backup/export
- Database import from original tool's JSON exports
- Per-account API rate limit overrides
- Email reports (weekly digest)

### Operational
- HTTP Basic auth on dashboard (optional, env var driven)
- Prometheus metrics endpoint
- Structured JSON logging
- Sentry integration (opt-in)

---

## Out of scope (not planned)

- **Bulk unfollow feature** — Original tool already does this in-browser; adding it server-side significantly increases ban risk. Use the original tool for actual unfollowing.
- **Public deployment** — This is designed for self-hosted home use. Hosting it publicly is asking for Instagram bans.
- **Mobile app** — The PWA-installable web dashboard is sufficient.
