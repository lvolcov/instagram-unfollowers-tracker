"""Scan orchestration: open a real Chrome tab, fetch followers/following, diff, notify."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.instagram.browser_session import open_logged_in_page
from backend.app.instagram.client import (
    IGUser,
    NotFollowingError,
    SessionExpiredError,
)
from backend.app.models.login_account import LoginAccount
from backend.app.models.new_follower import NewFollower
from backend.app.models.snapshot import Snapshot, SnapshotUser
from backend.app.models.tracked_account import TrackedAccount
from backend.app.models.unfollower import Unfollower
from backend.app.schemas.scan import ScanJob, ScanProgress, ScanResult
from backend.app.services.webhook_service import webhook_service

logger = structlog.get_logger(__name__)


class ScanService:
    def __init__(self) -> None:
        self._jobs: dict[str, ScanJob] = {}
        self._scan_lock = asyncio.Lock()  # only one scan at a time (shared Xvfb display)

    async def enqueue(
        self, tracked_account_id: int, *, schedule_id: int | None = None
    ) -> ScanJob:
        job = ScanJob(
            job_id=uuid.uuid4().hex,
            tracked_account_id=tracked_account_id,
            status="queued",
        )
        self._jobs[job.job_id] = job
        asyncio.create_task(self._run(tracked_account_id, job, schedule_id))
        return job

    def get_job(self, job_id: str) -> ScanJob | None:
        return self._jobs.get(job_id)

    async def _run(
        self,
        tracked_account_id: int,
        job: ScanJob,
        schedule_id: int | None = None,
    ) -> None:
        log = logger.bind(
            tracked_account_id=tracked_account_id,
            job_id=job.job_id,
            schedule_id=schedule_id,
        )
        async with self._scan_lock:
            job.status = "running"
            snapshot_id: int | None = None

            try:
                async with AsyncSessionLocal() as db:
                    tracked = await db.get(TrackedAccount, tracked_account_id)
                    if not tracked:
                        raise ValueError(f"TrackedAccount {tracked_account_id} not found")
                    login = (await db.execute(select(LoginAccount))).scalar_one_or_none()
                    if not login:
                        raise ValueError("No LoginAccount configured — please log in first.")
                    target_uid = tracked.instagram_user_id
                    target_username = tracked.username
                    session_path = login.session_path

                async with AsyncSessionLocal() as db:
                    snapshot = Snapshot(
                        tracked_account_id=tracked_account_id, status="running"
                    )
                    db.add(snapshot)
                    await db.flush()
                    snapshot_id = snapshot.id
                    await db.commit()

                async with open_logged_in_page(session_path) as ig:
                    # Mandatory follow check — bail out cleanly if relationship is broken.
                    status = await ig.friendship_status(target_uid)
                    log.info(
                        "scan.friendship",
                        following=status.following,
                        followed_by=status.followed_by,
                        is_private=status.is_private,
                    )
                    if not status.following:
                        raise NotFollowingError(
                            f"Login account does not follow @{target_username}. "
                            "Follow them from the logged-in account, then retry."
                        )

                    async with AsyncSessionLocal() as db:
                        t = await db.get(TrackedAccount, tracked_account_id)
                        t.follows_us = status.followed_by
                        t.we_follow = status.following
                        t.is_private = status.is_private
                        await db.commit()

                    # Canonical counts via the public user-info endpoint
                    # (this one still returns JSON to page.evaluate fetches).
                    info = await ig.user_info(target_uid)
                    expected_followers = int(info.get("follower_count") or 0)
                    expected_following = int(info.get("following_count") or 0)
                    log.info(
                        "scan.canonical_counts",
                        followers=expected_followers,
                        following=expected_following,
                    )

                    def _progress(phase: str):
                        def _cb(current: int, total: int, attempt: int) -> None:
                            job.progress = ScanProgress(
                                phase=f"{phase} (attempt {attempt})",
                                current=current,
                                total=total,
                            )
                        return _cb

                    # Bookmarklet-style GraphQL fetch — the v1 REST endpoint
                    # returns the SPA HTML shell to spoofed fetches; the
                    # GraphQL endpoint still returns JSON.
                    log.info("scan.fetching_followers", target=target_username)
                    followers, followers_complete = await ig.collect_via_graphql(
                        target_user_id=target_uid,
                        kind="followers",
                        expected_count=expected_followers,
                        on_progress=_progress("followers"),
                    )

                    log.info(
                        "scan.fetching_following",
                        followers_seen=len(followers),
                        followers_complete=followers_complete,
                    )
                    following, following_complete = await ig.collect_via_graphql(
                        target_user_id=target_uid,
                        kind="following",
                        expected_count=expected_following,
                        on_progress=_progress("following"),
                    )
                    log.info(
                        "scan.fetched",
                        followers=len(followers),
                        following=len(following),
                        followers_complete=followers_complete,
                        following_complete=following_complete,
                    )

                follower_ids = {u.id for u in followers}
                following_ids = {u.id for u in following}

                rows: list[SnapshotUser] = []
                for u in followers:
                    rel = "mutual" if u.id in following_ids else "follower"
                    rows.append(
                        SnapshotUser(
                            snapshot_id=snapshot_id,
                            instagram_user_id=u.id,
                            username=u.username,
                            full_name=u.full_name or None,
                            profile_pic_url=u.profile_pic_url or None,
                            is_verified=u.is_verified,
                            is_private=u.is_private,
                            relationship=rel,
                        )
                    )
                for u in following:
                    if u.id not in follower_ids:
                        rows.append(
                            SnapshotUser(
                                snapshot_id=snapshot_id,
                                instagram_user_id=u.id,
                                username=u.username,
                                full_name=u.full_name or None,
                                profile_pic_url=u.profile_pic_url or None,
                                is_verified=u.is_verified,
                                is_private=u.is_private,
                                relationship="following",
                            )
                        )

                fully_captured = followers_complete and following_complete
                warning: str | None = None
                if not fully_captured:
                    warning = (
                        f"Captured {len(followers)}/{expected_followers} followers"
                        f" and {len(following)}/{expected_following} following"
                        " — Instagram's modal stopped serving more before the"
                        " canonical count was reached. Diff proceeded; expect a"
                        " few false-positive unfollowers."
                    )
                    log.warning("scan.partial", warning=warning)

                async with AsyncSessionLocal() as db:
                    db.add_all(rows)
                    snap = await db.get(Snapshot, snapshot_id)
                    snap.followers_count = len(followers)
                    snap.following_count = len(following)
                    # Always mark completed — we use whatever we captured.
                    snap.status = "completed"
                    if warning:
                        snap.error_message = warning
                    t = await db.get(TrackedAccount, tracked_account_id)
                    t.last_scan_at = datetime.now(timezone.utc)
                    await db.commit()

                log.info(
                    "scan.snapshot_saved",
                    snapshot_id=snapshot_id,
                    rows=len(rows),
                    fully_captured=fully_captured,
                )

                job.progress = ScanProgress(
                    phase="diff", current=0, total=len(followers)
                )
                new_unfollowers = await self._diff_unfollowers(
                    tracked_account_id, snapshot_id, follower_ids, log
                )
                new_followers = await self._diff_new_followers(
                    tracked_account_id, snapshot_id, follower_ids, log
                )

                if new_unfollowers:
                    job.progress = ScanProgress(
                        phase="notify", current=0, total=len(new_unfollowers)
                    )
                    # Per-schedule webhook URL override (if scan was triggered
                    # by a schedule and the schedule has its own webhook_url).
                    override_url: str | None = None
                    if schedule_id is not None:
                        from backend.app.models.schedule import Schedule
                        async with AsyncSessionLocal() as db:
                            sched = await db.get(Schedule, schedule_id)
                            if sched and sched.webhook_url:
                                override_url = sched.webhook_url
                    try:
                        await webhook_service.send_unfollowers(
                            account=target_username,
                            unfollowers=[u.username for u in new_unfollowers],
                            url=override_url,
                        )
                    except Exception as exc:
                        log.warning("scan.webhook_failed", error=str(exc))

                job.status = "completed"
                job.progress = None
                job.result = ScanResult(
                    snapshot_id=snapshot_id,
                    new_unfollowers=len(new_unfollowers),
                    new_followers=len(new_followers),
                    warning=warning,
                )
                log.info(
                    "scan.completed",
                    new_unfollowers=len(new_unfollowers),
                    warning=bool(warning),
                )

            except NotFollowingError as exc:
                job.status = "failed"
                job.error = str(exc)
                log.warning("scan.not_following", error=str(exc))
                if snapshot_id:
                    async with AsyncSessionLocal() as db:
                        snap = await db.get(Snapshot, snapshot_id)
                        if snap:
                            snap.status = "failed"
                            snap.error_message = str(exc)
                            await db.commit()
            except SessionExpiredError as exc:
                job.status = "failed"
                job.error = str(exc)
                log.warning("scan.session_expired", error=str(exc))
                async with AsyncSessionLocal() as db:
                    login = (await db.execute(select(LoginAccount))).scalar_one_or_none()
                    login_username = login.username if login else None
                    if login:
                        login.session_status = "needs_relogin"
                        await db.commit()
                # Fire health webhook so the user knows trabalho_otimizado
                # needs to log in again before the next scheduled scan can run.
                try:
                    await webhook_service.send_health(
                        event="session_expired",
                        login_account=login_username,
                        tracked_account_id=tracked_account_id,
                        message=str(exc),
                    )
                except Exception as e:
                    log.warning("scan.health_webhook_failed", error=str(e))
            except Exception as exc:
                job.status = "failed"
                job.error = str(exc)
                log.exception("scan.failed", error=str(exc))
                if snapshot_id:
                    async with AsyncSessionLocal() as db:
                        snap = await db.get(Snapshot, snapshot_id)
                        if snap:
                            snap.status = "failed"
                            snap.error_message = str(exc)
                            await db.commit()

        # ----- after lock released -----
        # Reflect outcome on the schedule row that triggered us.
        if schedule_id is not None:
            from backend.app.models.schedule import Schedule
            async with AsyncSessionLocal() as db:
                sched = await db.get(Schedule, schedule_id)
                if sched:
                    sched.last_run_status = job.status
                    await db.commit()

    async def _diff_unfollowers(
        self,
        tracked_account_id: int,
        current_snapshot_id: int,
        current_follower_ids: set[str],
        log,
    ) -> list[Unfollower]:
        # Only diff against a previous snapshot that was itself fully captured.
        # Diffing against an "incomplete" snapshot would surface phantom
        # unfollowers (people who simply weren't paginated last time).
        async with AsyncSessionLocal() as db:
            prev_result = await db.execute(
                select(Snapshot)
                .where(
                    Snapshot.tracked_account_id == tracked_account_id,
                    Snapshot.status == "completed",
                    Snapshot.id < current_snapshot_id,
                )
                .order_by(Snapshot.id.desc())
                .limit(1)
            )
            prev_snap = prev_result.scalar_one_or_none()
            if not prev_snap:
                log.info("scan.first_scan_no_diff")
                return []

            prev_followers_result = await db.execute(
                select(SnapshotUser).where(
                    SnapshotUser.snapshot_id == prev_snap.id,
                    SnapshotUser.relationship.in_(["follower", "mutual"]),
                )
            )
            prev_followers = {u.instagram_user_id: u for u in prev_followers_result.scalars()}

            unfollower_ids = set(prev_followers.keys()) - current_follower_ids
            if not unfollower_ids:
                return []

            existing_result = await db.execute(
                select(Unfollower.instagram_user_id).where(
                    Unfollower.tracked_account_id == tracked_account_id,
                    Unfollower.instagram_user_id.in_(unfollower_ids),
                )
            )
            already = {r for r in existing_result.scalars()}
            new_ids = unfollower_ids - already

            records: list[Unfollower] = []
            for uid in new_ids:
                prev = prev_followers[uid]
                records.append(
                    Unfollower(
                        tracked_account_id=tracked_account_id,
                        instagram_user_id=uid,
                        username=prev.username,
                        full_name=prev.full_name,
                        profile_pic_url=prev.profile_pic_url,
                    )
                )
            if records:
                db.add_all(records)
                await db.commit()
                for r in records:
                    await db.refresh(r)
            log.info("scan.unfollowers_recorded", count=len(records))
            return records

    async def _diff_new_followers(
        self,
        tracked_account_id: int,
        current_snapshot_id: int,
        current_follower_ids: set[str],
        log,
    ) -> list[NewFollower]:
        async with AsyncSessionLocal() as db:
            prev_result = await db.execute(
                select(Snapshot)
                .where(
                    Snapshot.tracked_account_id == tracked_account_id,
                    Snapshot.status == "completed",
                    Snapshot.id < current_snapshot_id,
                )
                .order_by(Snapshot.id.desc())
                .limit(1)
            )
            prev_snap = prev_result.scalar_one_or_none()
            if not prev_snap:
                log.info("scan.first_scan_no_new_followers_diff")
                return []

            prev_followers_result = await db.execute(
                select(SnapshotUser).where(
                    SnapshotUser.snapshot_id == prev_snap.id,
                    SnapshotUser.relationship.in_(["follower", "mutual"]),
                )
            )
            prev_follower_ids = {u.instagram_user_id for u in prev_followers_result.scalars()}

            # Users in current snapshot that were NOT in previous snapshot.
            new_ids = current_follower_ids - prev_follower_ids
            if not new_ids:
                return []

            # Skip IDs already recorded as new followers.
            existing_result = await db.execute(
                select(NewFollower.instagram_user_id).where(
                    NewFollower.tracked_account_id == tracked_account_id,
                    NewFollower.instagram_user_id.in_(new_ids),
                )
            )
            already = {r for r in existing_result.scalars()}
            new_ids -= already

            # Look up user data from current snapshot.
            current_result = await db.execute(
                select(SnapshotUser).where(
                    SnapshotUser.snapshot_id == current_snapshot_id,
                    SnapshotUser.instagram_user_id.in_(new_ids),
                )
            )
            current_users = {u.instagram_user_id: u for u in current_result.scalars()}

            records: list[NewFollower] = []
            for uid in new_ids:
                user = current_users.get(uid)
                if not user:
                    continue
                records.append(
                    NewFollower(
                        tracked_account_id=tracked_account_id,
                        instagram_user_id=uid,
                        username=user.username,
                        full_name=user.full_name,
                        profile_pic_url=user.profile_pic_url,
                    )
                )
            if records:
                db.add_all(records)
                await db.commit()
                for r in records:
                    await db.refresh(r)
            log.info("scan.new_followers_recorded", count=len(records))
            return records


scan_service = ScanService()
