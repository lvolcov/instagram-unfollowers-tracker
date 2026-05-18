"""Integration tests for the /api/v1/accounts/{id}/whitelist endpoints."""
import time
import pytest

pytestmark = pytest.mark.integration

FAKE_ACCOUNT_ID = 99999
# Unique prefix per test run so re-runs don't collide on the UNIQUE constraint
_RUN_ID = str(int(time.time()))


def test_list_whitelist_for_nonexistent_account(client):
    r = client.get(f"/api/v1/accounts/{FAKE_ACCOUNT_ID}/whitelist")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_add_to_whitelist_for_nonexistent_account(client):
    """Adding to a non-existent account should succeed or return a known error, never 500."""
    r = client.post(
        f"/api/v1/accounts/{FAKE_ACCOUNT_ID}/whitelist",
        json={"instagram_user_id": f"uid_{_RUN_ID}", "username": "test_celeb", "note": "test"},
    )
    assert r.status_code in (200, 201, 404, 409, 422)


def test_duplicate_whitelist_entry_returns_409(client):
    uid = f"dup_{_RUN_ID}"
    r1 = client.post(
        f"/api/v1/accounts/{FAKE_ACCOUNT_ID}/whitelist",
        json={"instagram_user_id": uid, "username": "dup_user"},
    )
    if r1.status_code not in (200, 201):
        pytest.skip("Could not create first entry")

    r2 = client.post(
        f"/api/v1/accounts/{FAKE_ACCOUNT_ID}/whitelist",
        json={"instagram_user_id": uid, "username": "dup_user"},
    )
    assert r2.status_code == 409

    # cleanup
    entry_id = r1.json()["id"]
    client.delete(f"/api/v1/accounts/{FAKE_ACCOUNT_ID}/whitelist/{entry_id}")


def test_delete_nonexistent_whitelist_entry(client):
    r = client.delete(f"/api/v1/accounts/{FAKE_ACCOUNT_ID}/whitelist/99999")
    assert r.status_code == 404


def test_whitelist_full_crud_cycle(client):
    """Add an entry then delete it — verifying full round-trip."""
    uid = f"cycle_{_RUN_ID}"
    create_r = client.post(
        f"/api/v1/accounts/{FAKE_ACCOUNT_ID}/whitelist",
        json={"instagram_user_id": uid, "username": "roundtrip_user"},
    )
    if create_r.status_code not in (200, 201):
        pytest.skip("Could not create whitelist entry")

    entry = create_r.json()
    entry_id = entry["id"]

    list_r = client.get(f"/api/v1/accounts/{FAKE_ACCOUNT_ID}/whitelist")
    ids = [e["id"] for e in list_r.json()]
    assert entry_id in ids

    del_r = client.delete(f"/api/v1/accounts/{FAKE_ACCOUNT_ID}/whitelist/{entry_id}")
    assert del_r.status_code == 200
    assert del_r.json()["deleted"] is True
