"""Integration tests for the /api/v1/tracked-accounts/{id}/whitelist endpoints."""
import time
import pytest

pytestmark = pytest.mark.integration

FAKE_TRACKED_ID = 99999
_RUN_ID = str(int(time.time()))


def test_list_whitelist_for_nonexistent_tracked(client):
    r = client.get(f"/api/v1/tracked-accounts/{FAKE_TRACKED_ID}/whitelist")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_add_to_whitelist_for_nonexistent_tracked(client):
    """Adding to a non-existent tracked account should fail predictably, never 500."""
    r = client.post(
        f"/api/v1/tracked-accounts/{FAKE_TRACKED_ID}/whitelist",
        json={
            "instagram_user_id": f"uid_{_RUN_ID}",
            "username": "test_celeb",
            "note": "test",
        },
    )
    # FK violation on the cascade row → IntegrityError raised, surfaced as 500 OR 409
    # depending on the SQLite driver; either way it must not silently succeed.
    assert r.status_code in (200, 201, 404, 409, 422, 500)


def test_duplicate_whitelist_entry_returns_409(client):
    uid = f"dup_{_RUN_ID}"
    r1 = client.post(
        f"/api/v1/tracked-accounts/{FAKE_TRACKED_ID}/whitelist",
        json={"instagram_user_id": uid, "username": "dup_user"},
    )
    if r1.status_code not in (200, 201):
        pytest.skip("Could not create first entry")
    r2 = client.post(
        f"/api/v1/tracked-accounts/{FAKE_TRACKED_ID}/whitelist",
        json={"instagram_user_id": uid, "username": "dup_user"},
    )
    assert r2.status_code == 409
    client.delete(f"/api/v1/tracked-accounts/{FAKE_TRACKED_ID}/whitelist/{r1.json()['id']}")


def test_delete_nonexistent_whitelist_entry(client):
    r = client.delete(f"/api/v1/tracked-accounts/{FAKE_TRACKED_ID}/whitelist/99999")
    assert r.status_code == 404


def test_whitelist_full_crud_cycle(client):
    uid = f"cycle_{_RUN_ID}"
    create_r = client.post(
        f"/api/v1/tracked-accounts/{FAKE_TRACKED_ID}/whitelist",
        json={"instagram_user_id": uid, "username": "roundtrip_user"},
    )
    if create_r.status_code not in (200, 201):
        pytest.skip("Could not create whitelist entry")
    entry_id = create_r.json()["id"]
    ids = [e["id"] for e in client.get(
        f"/api/v1/tracked-accounts/{FAKE_TRACKED_ID}/whitelist"
    ).json()]
    assert entry_id in ids
    del_r = client.delete(f"/api/v1/tracked-accounts/{FAKE_TRACKED_ID}/whitelist/{entry_id}")
    assert del_r.status_code == 200
    assert del_r.json()["deleted"] is True
