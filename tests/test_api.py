"""API-level tests using FastAPI's TestClient against SQLite + fake Redis."""


def _create(client):
    resp = client.post("/api/users")
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_user_returns_id_code_and_egg(client):
    data = _create(client)
    assert data["user_id"]
    assert data["recovery_code"]
    assert data["pet"]["species"] == "egg"
    assert data["pet"]["egg_phase"] == "idle"


def test_recovery_codes_are_unique(client):
    a = _create(client)
    b = _create(client)
    assert a["recovery_code"] != b["recovery_code"]
    assert a["user_id"] != b["user_id"]


def test_get_user_roundtrip(client):
    created = _create(client)
    uid = created["user_id"]
    resp = client.get(f"/api/users/{uid}")
    assert resp.status_code == 200
    assert resp.json()["recovery_code"] == created["recovery_code"]


def test_get_unknown_user_404(client):
    assert client.get("/api/users/does-not-exist").status_code == 404


def test_recover_by_code(client):
    created = _create(client)
    resp = client.post(
        "/api/users/recover", json={"recovery_code": created["recovery_code"]}
    )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == created["user_id"]


def test_recover_bad_code_404(client):
    assert (
        client.post("/api/users/recover", json={"recovery_code": "NOPE-NOPE-9999"}).status_code
        == 404
    )


def test_get_pet_polling(client):
    uid = _create(client)["user_id"]
    resp = client.get(f"/api/pets/{uid}")
    assert resp.status_code == 200
    pet = resp.json()["pet"]
    assert pet["species"] == "egg"
    assert "needs_attention" in pet


def test_hatch_before_ready_stays_egg(client):
    uid = _create(client)["user_id"]
    pet = client.post(f"/api/pets/{uid}/hatch").json()["pet"]
    # Freshly created egg is < 60s old, so it should not hatch yet.
    assert pet["species"] == "egg"


def test_action_on_egg_is_rejected_gracefully(client):
    uid = _create(client)["user_id"]
    # Feeding an egg is a no-op (still an egg), not an error.
    pet = client.post(f"/api/pets/{uid}/action", json={"action": "feed_meal"}).json()["pet"]
    assert pet["species"] == "egg"


def test_unknown_action_400(client):
    uid = _create(client)["user_id"]
    resp = client.post(f"/api/pets/{uid}/action", json={"action": "teleport"})
    assert resp.status_code == 400


def test_set_name(client):
    uid = _create(client)["user_id"]
    pet = client.post(f"/api/pets/{uid}/name", json={"name": "Pixel"}).json()["pet"]
    assert pet["name"] == "Pixel"


def test_reset_lays_fresh_egg(client):
    uid = _create(client)["user_id"]
    client.post(f"/api/pets/{uid}/name", json={"name": "Pixel"})
    pet = client.post(f"/api/pets/{uid}/reset").json()["pet"]
    assert pet["species"] == "egg"
    assert pet["name"] == ""


def test_action_unknown_user_404(client):
    resp = client.post("/api/pets/ghost/action", json={"action": "play"})
    assert resp.status_code == 404
