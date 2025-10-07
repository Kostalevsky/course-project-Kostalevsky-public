import pytest
from fastapi.testclient import TestClient

from app.main import _CARDS, _DECKS, app


@pytest.fixture(autouse=True)
def reset_storage():
    _DECKS.clear()
    _CARDS.clear()
    yield
    _DECKS.clear()
    _CARDS.clear()


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_decks_flow_create_and_get():
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
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "not_found"
    assert "deck not found" in body["error"]["message"]


def test_cards_and_random_and_review():
    deck = client.post("/decks", json={"name": "IT-terms", "description": None}).json()
    did = deck["id"]

    r = client.get(f"/decks/{did}/cards/random")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"

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


def test_validation_errors():
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


def test_review_unknown_card_gives_404_envelope():
    unknown = "00000000-0000-0000-0000-000000000000"
    r = client.post("/reviews", json={"card_id": unknown, "grade": "good"})
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "not_found"
    assert "card not found" in body["error"]["message"]
