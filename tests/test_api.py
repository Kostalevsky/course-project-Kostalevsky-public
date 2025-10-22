# Больше не импортируем _CARDS, _DECKS
# from app.main import _CARDS, _DECKS, app

# Удалите эту фикстуру - она теперь в conftest.py
# @pytest.fixture(autouse=True)
# def reset_storage():
#     _DECKS.clear()
#     _CARDS.clear()
#     yield
#     _DECKS.clear()
#     _CARDS.clear()

# Удалите эту строку - client теперь фикстура из conftest.py
# client = TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_decks_flow_create_and_get(client):
    # изначально пусто
    r = client.get("/decks")
    assert r.status_code == 200
    assert r.json() == []

    # создаём колоду
    r = client.post("/decks", json={"name": "Spanish A1", "description": "Basics"})
    assert r.status_code == 201
    deck = r.json()
    assert deck["name"] == "Spanish A1"
    assert deck["cards"] == 0
    did = deck["id"]

    r = client.get(f"/decks/{did}")
    assert r.status_code == 200
    assert r.json()["cards"] == 0

    r = client.get("/decks/does-not-exist")
    assert r.status_code == 422  # Invalid UUID format
    body = r.json()
    assert body["status"] == 422
    assert "correlation_id" in body


def test_cards_and_random_and_review(client):
    deck = client.post("/decks", json={"name": "IT-terms", "description": None}).json()
    did = deck["id"]

    r = client.get(f"/decks/{did}/cards/random")
    assert r.status_code == 404
    body = r.json()
    assert body["status"] == 404
    assert "correlation_id" in body

    r = client.post(
        f"/decks/{did}/cards",
        json={"front": "hola", "back": "hello", "hint": None},
    )
    assert r.status_code == 201
    card = r.json()
    assert card["front"] == "hola"
    cid = card["id"]

    r = client.get(f"/decks/{did}/cards/random")
    assert r.status_code == 200
    rc = r.json()
    assert rc["id"] == cid

    before_due = rc["due_at"]
    r = client.post("/reviews", json={"card_id": cid, "grade": "good"})
    assert r.status_code == 200
    after = r.json()
    assert after["id"] == cid
    assert after["due_at"] != before_due
    assert after["interval_days"] >= 1
    assert 1.3 <= after["ease"] <= 3.0


def test_validation_errors(client):
    r = client.post("/decks", json={"name": "", "description": "x"})
    assert r.status_code == 422

    r = client.post(
        "/decks",
        json={"name": "ok", "description": None},
    )
    did = r.json()["id"]

    r = client.post(
        f"/decks/{did}/cards",
        json={"front": "x" * 201, "back": "ok", "hint": None},
    )
    assert r.status_code == 422


def test_review_unknown_card_gives_404_envelope(client):
    import uuid

    unknown = str(uuid.uuid4())  # Valid UUID v4 format
    r = client.post("/reviews", json={"card_id": unknown, "grade": "good"})
    assert r.status_code == 404
    body = r.json()
    assert body["status"] == 404
    assert "correlation_id" in body
