"""
API integration tests — covers the full HTTP request/response cycle.
All tests use an in-memory SQLite DB via the conftest fixtures.
"""


# --- Entries: auth guard ---

async def test_entries_requires_auth(client):
    resp = await client.get("/api/entries")
    assert resp.status_code == 401


async def test_add_entry_requires_auth(client):
    resp = await client.post("/api/entries", json={"item_name": "spinach"})
    assert resp.status_code == 401


# --- Entries: adding items ---

async def test_add_entry_success(client, user, auth_headers):
    resp = await client.post(
        "/api/entries", json={"item_name": "spinach"}, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["blocked"] is False
    assert data["entry"]["item_name"] == "spinach"
    assert data["entry"]["item_name_normalized"] == "spinach"
    assert isinstance(data["entry"]["id"], int)


async def test_add_entry_normalizes_name(client, user, auth_headers):
    resp = await client.post(
        "/api/entries", json={"item_name": "  Blueberries  "}, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["entry"]["item_name_normalized"] == "blueberry"


async def test_add_entry_rejects_empty_name(client, user, auth_headers):
    resp = await client.post(
        "/api/entries", json={"item_name": "   "}, headers=auth_headers
    )
    assert resp.status_code == 400


# --- Entries: duplicate handling ---

async def test_exact_duplicate_blocked(client, user, auth_headers):
    await client.post("/api/entries", json={"item_name": "garlic"}, headers=auth_headers)
    resp = await client.post(
        "/api/entries", json={"item_name": "garlic"}, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["blocked"] is True
    assert data["entry"] is None
    assert any("garlic" in w for w in data["warnings"])


async def test_near_duplicate_blocked_without_force(client, user, auth_headers):
    await client.post("/api/entries", json={"item_name": "turmeric"}, headers=auth_headers)
    resp = await client.post(
        "/api/entries", json={"item_name": "tumeric"}, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["blocked"] is True
    assert data["entry"] is None


async def test_near_duplicate_allowed_with_force(client, user, auth_headers):
    await client.post("/api/entries", json={"item_name": "turmeric"}, headers=auth_headers)
    resp = await client.post(
        "/api/entries?force=true", json={"item_name": "tumeric"}, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["blocked"] is False
    assert data["entry"] is not None


async def test_duplicate_check_from_another_user_is_independent(
    client, user, second_user, auth_headers, second_auth_headers
):
    # User 1 adds garlic; user 2 adding garlic should NOT be blocked.
    await client.post("/api/entries", json={"item_name": "garlic"}, headers=auth_headers)
    resp = await client.post(
        "/api/entries", json={"item_name": "garlic"}, headers=second_auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["blocked"] is False


# --- Entries: listing ---

async def test_list_entries_empty_initially(client, user, auth_headers):
    resp = await client.get("/api/entries", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_entries_returns_own_items(client, user, auth_headers):
    await client.post("/api/entries", json={"item_name": "spinach"}, headers=auth_headers)
    await client.post("/api/entries", json={"item_name": "garlic"}, headers=auth_headers)
    resp = await client.get("/api/entries", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    names = {i["item_name_normalized"] for i in items}
    assert names == {"spinach", "garlic"}


async def test_list_entries_does_not_include_other_users(
    client, user, second_user, auth_headers, second_auth_headers
):
    await client.post("/api/entries", json={"item_name": "kale"}, headers=second_auth_headers)
    resp = await client.get("/api/entries", headers=auth_headers)
    assert resp.json() == []


# --- Entries: delete ---

async def test_delete_own_entry(client, user, auth_headers):
    add_resp = await client.post(
        "/api/entries", json={"item_name": "spinach"}, headers=auth_headers
    )
    entry_id = add_resp.json()["entry"]["id"]

    del_resp = await client.delete(f"/api/entries/{entry_id}", headers=auth_headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["ok"] is True

    # Confirm it's gone
    list_resp = await client.get("/api/entries", headers=auth_headers)
    assert list_resp.json() == []


async def test_delete_other_users_entry_returns_404(
    client, user, second_user, auth_headers, second_auth_headers
):
    add_resp = await client.post(
        "/api/entries", json={"item_name": "spinach"}, headers=second_auth_headers
    )
    entry_id = add_resp.json()["entry"]["id"]

    del_resp = await client.delete(f"/api/entries/{entry_id}", headers=auth_headers)
    assert del_resp.status_code == 404


async def test_delete_nonexistent_entry_returns_404(client, user, auth_headers):
    resp = await client.delete("/api/entries/99999", headers=auth_headers)
    assert resp.status_code == 404


# --- Entries: check endpoint ---

async def test_check_entry_clean(client, user, auth_headers):
    resp = await client.get("/api/entries/check?item_name=spinach", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_duplicate"] is False
    assert data["is_near_duplicate"] is False


async def test_check_entry_exact_duplicate(client, user, auth_headers):
    await client.post("/api/entries", json={"item_name": "garlic"}, headers=auth_headers)
    resp = await client.get("/api/entries/check?item_name=garlic", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_duplicate"] is True
    assert data["is_near_duplicate"] is False


async def test_check_entry_near_duplicate(client, user, auth_headers):
    await client.post("/api/entries", json={"item_name": "turmeric"}, headers=auth_headers)
    resp = await client.get("/api/entries/check?item_name=tumeric", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_duplicate"] is False
    assert data["is_near_duplicate"] is True
    assert data["near_match"] == "turmeric"


async def test_check_entry_spelling_suggestion(client, user, auth_headers):
    resp = await client.get("/api/entries/check?item_name=tumeric", headers=auth_headers)
    assert resp.status_code == 200
    # "tumeric" is close enough to trigger spelling suggestion for "turmeric"
    data = resp.json()
    assert data["spelling_suggestion"] == "turmeric"


# --- Leaderboard ---

async def test_leaderboard_requires_auth(client):
    resp = await client.get("/api/leaderboard")
    assert resp.status_code == 401


async def test_leaderboard_shows_all_active_users(
    client, user, second_user, auth_headers
):
    resp = await client.get("/api/leaderboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "standings" in data
    assert "week" in data
    names = {s["name"] for s in data["standings"]}
    assert "TestUser" in names
    assert "OtherUser" in names


async def test_leaderboard_ranks_by_count(client, user, second_user, auth_headers):
    # TestUser adds 2 items, OtherUser adds 0
    await client.post("/api/entries", json={"item_name": "spinach"}, headers=auth_headers)
    await client.post("/api/entries", json={"item_name": "garlic"}, headers=auth_headers)

    resp = await client.get("/api/leaderboard", headers=auth_headers)
    standings = resp.json()["standings"]

    leader = standings[0]
    assert leader["name"] == "TestUser"
    assert leader["count"] == 2
    assert leader["rank"] == 1

    last = standings[-1]
    assert last["name"] == "OtherUser"
    assert last["count"] == 0
    assert last["rank"] == 2


# --- View another user's entries ---

async def test_view_other_user_entries(
    client, user, second_user, auth_headers, second_auth_headers
):
    await client.post(
        "/api/entries", json={"item_name": "kale"}, headers=second_auth_headers
    )
    resp = await client.get(
        f"/api/entries/user/{second_user.id}", headers=auth_headers
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["item_name_normalized"] == "kale"


# --- Admin: create user ---

async def test_admin_create_user(client):
    resp = await client.post(
        "/api/admin/users",
        json={"name": "NewPerson", "pin": "9999"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "NewPerson"
    assert data["is_active"] is True


async def test_admin_create_duplicate_user_fails(client, user):
    resp = await client.post(
        "/api/admin/users",
        json={"name": "TestUser", "pin": "9999"},
    )
    assert resp.status_code == 400


async def test_admin_list_users_requires_auth(client):
    resp = await client.get("/api/admin/users")
    assert resp.status_code == 401
