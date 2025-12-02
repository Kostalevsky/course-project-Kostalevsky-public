import logging
import os
import random
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from .config import install_secret_filter
from .database import get_db, init_db
from .errors import not_found_error, problem, validation_error
from .middleware import rate_limit_middleware
from .models import Card, Deck
from .schemas import CardCreate, CardOut, DeckCreate, DeckOut, ReviewIn
from .security import secure_save, validate_file_upload

app = FastAPI(title="SecDev Course App", version="0.1.0")

logger = logging.getLogger("app")
install_secret_filter(logger, "DATABASE_URL", "API_TOKEN", "DB_PASSWORD")


@app.on_event("startup")
def on_startup():
    # В тестах не создаём таблицы автоматически
    if not os.getenv("TESTING"):
        init_db()


if not os.getenv("DISABLE_RATE_LIMITING"):
    app.middleware("http")(rate_limit_middleware)


def list_decks(db: Session):
    decks = db.query(Deck).all()
    return [deck.to_dict() for deck in decks]


def create_deck(db: Session, name: str, description: str | None):
    deck = Deck(name=name, description=description)
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return deck.to_dict()


def get_deck(db: Session, deck_id: str):
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        return None
    return deck.to_dict()


def create_card(db: Session, deck_id: str, front: str, back: str, hint: str | None):
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        return None

    card = Card(
        deck_id=deck_id,
        front=front,
        back=back,
        hint=hint,
        due_at=datetime.now(UTC),
        interval_days=0,
        ease=2.5,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card.to_dict()


def random_card(db: Session, deck_id: str):
    cards = db.query(Card).filter(Card.deck_id == deck_id).all()
    if not cards:
        return None
    return random.choice(cards).to_dict()


def review(db: Session, card_id: str, grade: str):
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        return None

    if grade == "again":
        ease = max(1.3, card.ease - 0.2)
        interval = 1
    elif grade == "hard":
        ease = max(1.3, card.ease - 0.05)
        interval = max(1, int(max(1, card.interval_days) * 1.2))
    else:
        ease = min(3.0, card.ease + 0.05)
        interval = max(1, int(max(1, card.interval_days) * ease))

    card.ease = ease
    card.interval_days = interval
    card.due_at = datetime.now(UTC) + timedelta(days=interval)

    db.commit()
    db.refresh(card)
    return card.to_dict()


def validate_uuid(value: str, field_name: str = "id") -> bool:
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
    errors = exc.errors()

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


@app.get("/decks", response_model=list[DeckOut])
def get_decks(db: Session = Depends(get_db)):
    return list_decks(db)


@app.post("/decks", response_model=DeckOut, status_code=status.HTTP_201_CREATED)
def create_deck_endpoint(payload: DeckCreate, db: Session = Depends(get_db)):
    return create_deck(db, payload.name, payload.description)


@app.get("/decks/{deck_id}", response_model=DeckOut)
def get_deck_endpoint(deck_id: str, db: Session = Depends(get_db)):
    if not validate_uuid(deck_id):
        return validation_error(
            detail="Invalid deck ID format",
            field="deck_id",
            instance=f"/decks/{deck_id}",
        )

    deck = get_deck(db, deck_id)
    if not deck:
        return not_found_error("deck", deck_id, f"/decks/{deck_id}")
    return deck


@app.post(
    "/decks/{deck_id}/cards",
    response_model=CardOut,
    status_code=status.HTTP_201_CREATED,
)
def create_card_endpoint(deck_id: str, payload: CardCreate, db: Session = Depends(get_db)):
    if not validate_uuid(deck_id):
        return validation_error(
            detail="Invalid deck ID format",
            field="deck_id",
            instance=f"/decks/{deck_id}/cards",
        )

    card = create_card(db, deck_id, payload.front, payload.back, payload.hint)
    if not card:
        return not_found_error("deck", deck_id, f"/decks/{deck_id}/cards")
    return card


@app.get("/decks/{deck_id}/cards/random", response_model=CardOut)
def get_random_card_endpoint(deck_id: str, db: Session = Depends(get_db)):
    if not validate_uuid(deck_id):
        return validation_error(
            detail="Invalid deck ID format",
            field="deck_id",
            instance=f"/decks/{deck_id}/cards/random",
        )

    card = random_card(db, deck_id)
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
def post_review(payload: ReviewIn, db: Session = Depends(get_db)):
    if not validate_uuid(payload.card_id):
        return validation_error(
            detail="Invalid card ID format", field="card_id", instance="/reviews"
        )

    card = review(db, payload.card_id, payload.grade)
    if not card:
        return not_found_error("card", payload.card_id, "/reviews")
    return card


@app.post("/decks/{deck_id}/cards/{card_id}/image")
def upload_card_image(
    deck_id: str, card_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)
):
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

    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        return not_found_error("deck", deck_id, f"/decks/{deck_id}/cards/{card_id}/image")

    card = db.query(Card).filter(Card.id == card_id, Card.deck_id == deck_id).first()
    if not card:
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

    card.image_path = result
    db.commit()

    return {
        "message": "Image uploaded successfully",
        "image_path": result,
        "card_id": card_id,
    }
