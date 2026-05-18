"""Snapshot diff logic — detect new unfollowers between two snapshots."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserSummary:
    instagram_user_id: str
    username: str
    full_name: str | None
    profile_pic_url: str | None


def diff_unfollowers(
    previous_followers: list[UserSummary],
    current_followers: list[UserSummary],
) -> list[UserSummary]:
    """Return users present in `previous_followers` but not in `current_followers`.

    Match by `instagram_user_id` so username changes don't cause false positives.
    """
    current_ids = {u.instagram_user_id for u in current_followers}
    return [u for u in previous_followers if u.instagram_user_id not in current_ids]
