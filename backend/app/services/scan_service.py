"""Scan orchestration: fetch followers/following, diff, persist, notify."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select

from backend.app.core.database import AsyncSessionLocal
from backend.app.instagram.client import IGUser, InstagramClient, SessionExpiredError
from backend.app.instagram.session_store import cookies_from_storage, load_session
from backend.app.models.account import Account
from backend.app.models.snapshot import Snapshot, SnapshotUser
from backend.app.models.unfollower import Unfollower
from backend.app.models.whitelist import WhitelistEntry
from backend.app.schemas.scan import ScanJob, ScanProgress, ScanResult
from backend.app.services.webhook_service import webhook_service

logger = structlog.get_logger(__name__)


class ScanService:
    def __init__(self) -> None:
        self._jobs: dict[str, ScanJob] = {}

    async def enqueue(self, account_id: int) -> ScanJob:
        job = ScanJob(job_id=uuid.uuid4().hex, account_id=account_id, status="queued")
        self._jobs[job.job_id] = job
        asyncio.create_task(self._run(account_id, job))
        return job

    def get_job(self, job_id: str) -> ScanJob | None:
        return self._jobs.get(job_id)

    # ------------------------------------------------------------------

    async def _run(self, account_id: int, job: ScanJob) -> None:
        log = logger.bind(account_id=account_id, job_id=job.job_id)
        job.status = "running"
        snapshot_id: int | None = None

        try:
            # Load account
            async with AsyncSessionLocal() as db:
                account = await db.get(Account, account_id)
                if not account:
                    raise ValueError(f"Account {account_id} not found")
                session_path = account.session_path
                username = account.username

            if not session_path:
                raise ValueError("No saved session — please re-login")

            storage = load_session(session_path)
            cookies = cookies_from_storage(storage)
            if not cookies.get("sessionid"):
                raise ValueError("Session cookies are missing sessionid — please re-login")

            client = InstagramClient(cookies=cookies)
            log.info("scan.started", username=username)

            # Create snapshot row
            async with AsyncSessionLocal() as db:
                snapshot = Snapshot(account_id=account_id, status="running")
                db.add(snapshot)
                await db.flush()
                snapshot_id = snapshot.id
                await db.commit()

            # ---- fetch followers ----
            log.info("scan.fetching_followers")
            job.progress = ScanProgress(phase="followers", current=0, total=0)
            followers: list[IGUser] = []
            async for user in client.iter_followers():
                followers.append(user)
                job.progress = ScanProgress(phase="followers", current=len(followers), total=0)
            log.info("scan.followers_done", count=len(followers))

            # ---- fetch following ----
            log.info("scan.fetching_following")
            job.progress = ScanProgress(phase="following", current=0, total=0)
            following: list[IGUser] = []
            async for user in client.iter_following():
                following.append(user)
                job.progress = ScanProgress(phase="following", current=len(following), total=0)
            log.info("scan.following_done", count=len(following))

            # ---- persist snapshot users ----
            follower_ids = {u.id for u in followers}
            following_ids = {u.id for u in following}

            rows: list[SnapshotUser] = []
            for u in followers:
                rel = "mutual" if u.id in following_ids else "follower"
                rows.append(SnapshotUser(
                    snapshot_id=snapshot_id,
                    instagram_user_id=u.id,
                    username=u.username,
                    full_name=u.full_name or None,
                    profile_pic_url=u.profile_pic_url or None,
                    is_verified=u.is_verified,
                    is_private=u.is_private,
                    relationship=rel,
                ))
            for u in following:
                if u.id not in follower_ids:
                    rows.append(SnapshotUser(
                        snapshot_id=snapshot_id,
                        instagram_user_id=u.id,
                        username=u.username,
                        full_name=u.full_name or None,
                        profile_pic_url=u.profile_pic_url or None,
                        is_verified=u.is_verified,
                        is_private=u.is_private,
                        relationship="following",
                    ))

            async with AsyncSessionLocal() as db:
                db.add_all(rows)
                snap = await db.get(Snapshot, snapshot_id)
                snap.followers_count = len(followers)
                snap.following_count = len(following)
                snap.status = "completed"
                acc = await db.get(Account, account_id)
                acc.last_scan_at = datetime.now(timezone.utc)
                await db.commit()

            log.info("scan.snapshot_saved", snapshot_id=snapshot_id, rows=len(rows))

            # ---- diff unfollowers ----
            job.progress = ScanProgress(phase="diff", current=0, total=0)
            new_unfollowers = await self._diff_unfollowers(
                account_id, snapshot_id, follower_ids, log
            )
            log.info("scan.diff_done", new_unfollowers=len(new_unfollowers))

            # ---- notify ----
            if new_unfollowers:
                job.progress = ScanProgress(phase="notify", current=0, total=len(new_unfollowers))
                try:
                    await webhook_service.send(
                        account=username,
                        unfollowers=[u.username for u in new_unfollowers],
                    )
                    log.info("scan.webhook_sent", count=len(new_unfollowers))
                except Exception as exc:
                    log.warning("scan.webhook_failed", error=str(exc))

            job.status = "completed"
            job.progress = None
            job.result = ScanResult(snapshot_id=snapshot_id, new_unfollowers=len(new_unfollowers))
            log.info("scan.completed", new_unfollowers=len(new_unfollowers))

        except SessionExpiredError as exc:
            job.status = "failed"
            job.error = str(exc)
            log.warning("scan.session_expired", error=str(exc))
            async with AsyncSessionLocal() as db:
                acc = await db.get(Account, account_id)
                if acc:
                    acc.session_status = "needs_relogin"
                    await db.commit()
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

    async def _diff_unfollowers(
        self,
        account_id: int,
        current_snapshot_id: int,
        current_follower_ids: set[str],
        log,
    ) -> list[Unfollower]:
        async with AsyncSessionLocal() as db:
            # Find most recent completed snapshot before this one
            prev_result = await db.execute(
                select(Snapshot)
                .where(
                    Snapshot.account_id == account_id,
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

            # Previous followers
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

            # Check which are already recorded
            existing_result = await db.execute(
                select(Unfollower.instagram_user_id).where(
                    Unfollower.account_id == account_id,
                    Unfollower.instagram_user_id.in_(unfollower_ids),
                )
            )
            already_recorded = {r for r in existing_result.scalars()}
            new_ids = unfollower_ids - already_recorded

            records: list[Unfollower] = []
            for uid in new_ids:
                prev = prev_followers[uid]
                records.append(Unfollower(
                    account_id=account_id,
                    instagram_user_id=uid,
                    username=prev.username,
                    full_name=prev.full_name,
                    profile_pic_url=prev.profile_pic_url,
                ))

            if records:
                db.add_all(records)
                await db.commit()
                for r in records:
                    await db.refresh(r)

            log.info("scan.unfollowers_recorded", count=len(records))
            return records


scan_service = ScanService()
