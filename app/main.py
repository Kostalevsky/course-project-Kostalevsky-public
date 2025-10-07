import uuid
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from .schemas import CardCreate, CardOut, DeckCreate, DeckOut, ReviewIn

app = FastAPI(title="SecDev Course App", version="0.1.0")

# Сделаем простое in-memory хранилище для колод и карточек
_DECKS: dict[str, dict] = {}
_CARDS: dict[str, dict] = {}


def _uid() -> str:
    return str(uuid.uuid4())


def list_decks():
    return [
        {
            "id": d["id"],
            "name": d["name"],
            "description": d.get("description"),
            "cards": sum(1 for c in _CARDS.values() if c["deck_id"] == d["id"]),
        }
        for d in _DECKS.values()
    ]


def create_deck(name: str, description: str | None):
    did = _uid()
    deck = {"id": did, "name": name, "description": description}
    _DECKS[did] = deck
    return {**deck, "cards": 0}


def get_deck(deck_id: str):
    d = _DECKS.get(deck_id)
    if not d:
        return None
    return {**d, "cards": sum(1 for c in _CARDS.values() if c["deck_id"] == deck_id)}


def create_card(deck_id: str, front: str, back: str, hint: str | None):
    if deck_id not in _DECKS:
        return None
    cid = _uid()
    card = {
        "id": cid,
        "deck_id": deck_id,
        "front": front,
        "back": back,
        "hint": hint,
        "due_at": datetime.now(UTC),
        "interval_days": 0,
        "ease": 2.5,
    }
    _CARDS[cid] = card
    return card


def random_card(deck_id: str):
    cards = [c for c in _CARDS.values() if c["deck_id"] == deck_id]
    if not cards:
        return None
    return cards[0]


def review(card_id: str, grade: str):
    c = _CARDS.get(card_id)
    if not c:
        return None
    if grade == "again":
        ease = max(1.3, c["ease"] - 0.2)
        interval = 1
    elif grade == "hard":
        ease = max(1.3, c["ease"] - 0.05)
        interval = max(1, int(max(1, c["interval_days"]) * 1.2))
    else:
        ease = min(3.0, c["ease"] + 0.05)
        interval = max(1, int(max(1, c["interval_days"]) * ease))
    c.update(
        {
            "ease": ease,
            "interval_days": interval,
            "due_at": datetime.now(UTC) + timedelta(days=interval),
        }
    )
    return c


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Normalize FastAPI HTTPException into our error envelope
    detail = exc.detail if isinstance(exc.detail, str) else "http_error"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": detail}},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


# Example minimal entity (for tests/demo)
_DB = {"items": []}


@app.post("/items")
def create_item(name: str):
    if not name or len(name) > 100:
        raise ApiError(
            code="validation_error", message="name must be 1..100 chars", status=422
        )
    item = {"id": len(_DB["items"]) + 1, "name": name}
    _DB["items"].append(item)
    return item


@app.get("/items/{item_id}")
def get_item(item_id: int):
    for it in _DB["items"]:
        if it["id"] == item_id:
            return it
    raise ApiError(code="not_found", message="item not found", status=404)


@app.get("/decks", response_model=list[DeckOut])
def get_decks():
    return list_decks()


@app.post("/decks", response_model=DeckOut, status_code=status.HTTP_201_CREATED)
def create_deck_endpoint(payload: DeckCreate):
    return create_deck(payload.name, payload.description)


@app.get("/decks/{deck_id}", response_model=DeckOut)
def get_deck_endpoint(deck_id: str):
    deck = get_deck(deck_id)
    if not deck:
        raise ApiError(code="not_found", message="deck not found", status=404)
    return deck


@app.post(
    "/decks/{deck_id}/cards",
    response_model=CardOut,
    status_code=status.HTTP_201_CREATED,
)
def create_card_endpoint(deck_id: str, payload: CardCreate):
    card = create_card(deck_id, payload.front, payload.back, payload.hint)
    if not card:
        raise ApiError(code="not_found", message="deck not found", status=404)
    return card


@app.get("/decks/{deck_id}/cards/random", response_model=CardOut)
def get_random_card_endpoint(deck_id: str):
    card = random_card(deck_id)
    if not card:
        raise ApiError(code="not_found", message="no cards in deck", status=404)
    return card


@app.post("/reviews", response_model=CardOut)
def post_review(payload: ReviewIn):
    card = review(payload.card_id, payload.grade)
    if not card:
        raise ApiError(code="not_found", message="card not found", status=404)
    return card
