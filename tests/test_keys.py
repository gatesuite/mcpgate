async def test_create_key(client, admin_headers):
    resp = await client.post(
        "/api/v1/keys",
        json={"user_id": "user-1", "name": "My Key"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user-1"
    assert data["name"] == "My Key"
    assert data["key"].startswith("mcp_sk_")
    assert "key" in data  # plain-text key returned once
    assert "id" in data
    assert "prefix" in data
    assert "created_at" in data


async def test_create_key_no_auth(client):
    resp = await client.post("/api/v1/keys", json={"user_id": "user-1"})
    assert resp.status_code == 422  # missing required Authorization header


async def test_create_key_wrong_auth(client):
    resp = await client.post(
        "/api/v1/keys",
        json={"user_id": "user-1"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert resp.status_code == 403


async def test_create_key_with_scopes(client, admin_headers):
    resp = await client.post(
        "/api/v1/keys",
        json={"user_id": "user-2", "scopes": {"read": True, "write": False}},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["key"].startswith("mcp_sk_")


async def test_list_keys(client, admin_headers):
    # Create two keys for the same user
    for i in range(2):
        await client.post(
            "/api/v1/keys",
            json={"user_id": "user-list", "name": f"Key {i}"},
            headers=admin_headers,
        )

    resp = await client.get("/api/v1/keys/user-list", headers=admin_headers)
    assert resp.status_code == 200
    keys = resp.json()
    assert len(keys) == 2
    for key in keys:
        assert key["user_id"] == "user-list"
        assert "key" not in key  # secret must never be returned in list


async def test_list_keys_empty(client, admin_headers):
    resp = await client.get("/api/v1/keys/unknown-user", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_keys_no_auth(client):
    resp = await client.get("/api/v1/keys/user-1")
    assert resp.status_code == 422


async def test_revoke_key(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/keys",
        json={"user_id": "user-revoke"},
        headers=admin_headers,
    )
    key_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/keys/{key_id}", headers=admin_headers)
    assert resp.status_code == 204

    # Key should no longer appear in the list
    list_resp = await client.get("/api/v1/keys/user-revoke", headers=admin_headers)
    assert list_resp.json() == []


async def test_revoke_key_no_auth(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/keys",
        json={"user_id": "user-revoke-noauth"},
        headers=admin_headers,
    )
    key_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/keys/{key_id}")
    assert resp.status_code == 422
