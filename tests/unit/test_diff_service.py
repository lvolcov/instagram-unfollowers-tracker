"""Unit tests for the snapshot diff logic — no container required."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.app.services.diff_service import UserSummary, diff_unfollowers


def _user(uid: str, username: str = "") -> UserSummary:
    return UserSummary(
        instagram_user_id=uid,
        username=username or f"user_{uid}",
        full_name=None,
        profile_pic_url=None,
    )


def test_no_unfollowers_when_lists_identical():
    users = [_user("1"), _user("2"), _user("3")]
    assert diff_unfollowers(users, users) == []


def test_detects_single_unfollower():
    prev = [_user("1"), _user("2")]
    curr = [_user("1")]
    result = diff_unfollowers(prev, curr)
    assert len(result) == 1
    assert result[0].instagram_user_id == "2"


def test_detects_multiple_unfollowers():
    prev = [_user("1"), _user("2"), _user("3")]
    curr = [_user("1")]
    result = diff_unfollowers(prev, curr)
    assert {u.instagram_user_id for u in result} == {"2", "3"}


def test_new_follower_not_reported_as_unfollower():
    prev = [_user("1")]
    curr = [_user("1"), _user("2")]
    assert diff_unfollowers(prev, curr) == []


def test_empty_previous_means_no_unfollowers():
    curr = [_user("1"), _user("2")]
    assert diff_unfollowers([], curr) == []


def test_empty_current_means_all_unfollowed():
    prev = [_user("1"), _user("2"), _user("3")]
    result = diff_unfollowers(prev, [])
    assert len(result) == 3


def test_both_empty():
    assert diff_unfollowers([], []) == []


def test_matches_by_id_not_username():
    """Username change should NOT produce a false-positive unfollower."""
    prev = [UserSummary("42", "old_name", None, None)]
    curr = [UserSummary("42", "new_name", None, None)]
    assert diff_unfollowers(prev, curr) == []


def test_result_preserves_user_metadata():
    alice = UserSummary("99", "alice", "Alice Smith", "https://cdn.example.com/alice.jpg")
    result = diff_unfollowers([alice], [])
    assert result[0] == alice
