async def test_verify_valid_key(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/keys",
        json={"user_id": "user-verify", "scopes": {"read": True}},
        headers=admin_headers,
    )
    plain_key = create_resp.json()["key"]

    resp = await client.post("/api/v1/verify", json={"key": plain_key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["user_id"] == "user-verify"
    assert data["scopes"] == {"read": True}
    assert data.get("error") is None


async def test_verify_wrong_secret(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/keys",
        json={"user_id": "user-bad-secret"},
        headers=admin_headers,
    )
    plain_key = create_resp.json()["key"]
    # Corrupt the secret portion (everything after the last underscore)
    tampered = plain_key[:-4] + "XXXX"

    resp = await client.post("/api/v1/verify", json={"key": tampered})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert data.get("error") is not None


async def test_verify_malformed_key(client):
    resp = await client.post("/api/v1/verify", json={"key": "not-a-valid-key"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert "Invalid key format" in data["error"]


async def test_verify_wrong_prefix(client):
    resp = await client.post("/api/v1/verify", json={"key": "sk_live_abc123_xyz"})
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


async def test_verify_revoked_key(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/keys",
        json={"user_id": "user-revoked"},
        headers=admin_headers,
    )
    data = create_resp.json()
    plain_key = data["key"]
    key_id = data["id"]

    await client.delete(f"/api/v1/keys/{key_id}", headers=admin_headers)

    resp = await client.post("/api/v1/verify", json={"key": plain_key})
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


async def test_verify_expired_key(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/keys",
        json={"user_id": "user-expired", "expires_in_days": -1},
        headers=admin_headers,
    )
    plain_key = create_resp.json()["key"]

    resp = await client.post("/api/v1/verify", json={"key": plain_key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert data["error"] == "Key expired"


async def test_verify_updates_last_used(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/keys",
        json={"user_id": "user-last-used"},
        headers=admin_headers,
    )
    plain_key = create_resp.json()["key"]

    # last_used_at should be null before first verify
    list_resp = await client.get("/api/v1/keys/user-last-used", headers=admin_headers)
    assert list_resp.json()[0]["last_used_at"] is None

    await client.post("/api/v1/verify", json={"key": plain_key})

    list_resp = await client.get("/api/v1/keys/user-last-used", headers=admin_headers)
    assert list_resp.json()[0]["last_used_at"] is not None
