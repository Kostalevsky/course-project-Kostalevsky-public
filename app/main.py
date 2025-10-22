import os
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError

from .errors import not_found_error, problem, validation_error
from .middleware import rate_limit_middleware
from .schemas import CardCreate, CardOut, DeckCreate, DeckOut, ReviewIn
from .security import secure_save, validate_file_upload

app = FastAPI(title="SecDev Course App", version="0.1.0")

# Отключаем rate limiting для тестов

if not os.getenv("DISABLE_RATE_LIMITING"):
    app.middleware("http")(rate_limit_middleware)

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


def validate_uuid(value: str, field_name: str = "id") -> bool:
    """Проверяет, является ли строка валидным UUID."""
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler для ошибок валидации FastAPI/Pydantic в формате RFC 7807."""
    errors = exc.errors()

    # Формируем понятное описание ошибки
    if errors:
        first_error = errors[0]
        field_path = " -> ".join(str(loc) for loc in first_error["loc"])
        detail = f"Validation error in {field_path}: {first_error['msg']}"
    else:
        detail = "Validation error"

    return problem(
        status=422,
        title="Validation Error",
        detail=detail,
        type_uri="https://api.example.com/problems/validation-error",
        instance=str(request.url.path),
        extras={"errors": errors},
    )


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return problem(
        status=exc.status,
        title="API Error",
        detail=exc.message,
        type_uri="https://api.example.com/problems/api-error",
        instance=str(request.url.path),
        extras={"code": exc.code},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "HTTP error occurred"
    return problem(
        status=exc.status_code,
        title="HTTP Error",
        detail=detail,
        type_uri="https://api.example.com/problems/http-error",
        instance=str(request.url.path),
    )


@app.get("/health")
def health():
    return {"status": "ok"}


_DB = {"items": []}


@app.post("/items")
def create_item(name: str):
    if not name or len(name) > 100:
        raise ApiError(code="validation_error", message="name must be 1..100 chars", status=422)
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
    if not validate_uuid(deck_id):
        return validation_error(
            detail="Invalid deck ID format",
            field="deck_id",
            instance=f"/decks/{deck_id}",
        )

    deck = get_deck(deck_id)
    if not deck:
        return not_found_error("deck", deck_id, f"/decks/{deck_id}")
    return deck


@app.post(
    "/decks/{deck_id}/cards",
    response_model=CardOut,
    status_code=status.HTTP_201_CREATED,
)
def create_card_endpoint(deck_id: str, payload: CardCreate):
    if not validate_uuid(deck_id):
        return validation_error(
            detail="Invalid deck ID format",
            field="deck_id",
            instance=f"/decks/{deck_id}/cards",
        )

    card = create_card(deck_id, payload.front, payload.back, payload.hint)
    if not card:
        return not_found_error("deck", deck_id, f"/decks/{deck_id}/cards")
    return card


@app.get("/decks/{deck_id}/cards/random", response_model=CardOut)
def get_random_card_endpoint(deck_id: str):
    if not validate_uuid(deck_id):
        return validation_error(
            detail="Invalid deck ID format",
            field="deck_id",
            instance=f"/decks/{deck_id}/cards/random",
        )

    card = random_card(deck_id)
    if not card:
        return problem(
            status=404,
            title="Resource Not Found",
            detail="no cards in deck",
            type_uri="https://api.learning-flashcards.com/problems/not-found",
            instance=f"/decks/{deck_id}/cards/random",
        )
    return card


@app.post("/reviews", response_model=CardOut)
def post_review(payload: ReviewIn):
    if not validate_uuid(payload.card_id):
        return validation_error(
            detail="Invalid card ID format", field="card_id", instance="/reviews"
        )

    card = review(payload.card_id, payload.grade)
    if not card:
        return not_found_error("card", payload.card_id, "/reviews")
    return card


@app.post("/decks/{deck_id}/cards/{card_id}/image")
def upload_card_image(deck_id: str, card_id: str, file: UploadFile = File(...)):
    if not validate_uuid(deck_id):
        return validation_error(
            detail="Invalid deck ID format",
            field="deck_id",
            instance=f"/decks/{deck_id}/cards/{card_id}/image",
        )

    if not validate_uuid(card_id):
        return validation_error(
            detail="Invalid card ID format",
            field="card_id",
            instance=f"/decks/{deck_id}/cards/{card_id}/image",
        )

    if deck_id not in _DECKS:
        return not_found_error("deck", deck_id, f"/decks/{deck_id}/cards/{card_id}/image")

    if card_id not in _CARDS or _CARDS[card_id]["deck_id"] != deck_id:
        return not_found_error("card", card_id, f"/decks/{deck_id}/cards/{card_id}/image")

    try:
        data = file.file.read()
    except Exception as e:
        return problem(
            status=400,
            title="File Read Error",
            detail=f"Failed to read uploaded file: {str(e)}",
            type_uri="https://api.learning-flashcards.com/problems/file-read-error",
            instance=f"/decks/{deck_id}/cards/{card_id}/image",
        )

    is_valid, error_msg = validate_file_upload(data, file.filename or "")
    if not is_valid:
        return validation_error(
            detail=error_msg,
            field="file",
            instance=f"/decks/{deck_id}/cards/{card_id}/image",
        )

    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    success, result = secure_save(upload_dir, file.filename or "", data)
    if not success:
        return problem(
            status=400,
            title="File Save Error",
            detail=f"Failed to save file: {result}",
            type_uri="https://api.learning-flashcards.com/problems/file-save-error",
            instance=f"/decks/{deck_id}/cards/{card_id}/image",
        )

    _CARDS[card_id]["image_path"] = result

    return {
        "message": "Image uploaded successfully",
        "image_path": result,
        "card_id": card_id,
    }
