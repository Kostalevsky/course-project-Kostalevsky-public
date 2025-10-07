from datetime import datetime
from typing import Optional

from pydantic import BaseModel, constr, field_validator

# Создаем строгий паттерн айди для колоды и карточки, чтобы валидировать UUID корректнее
DeckId = constr(pattern=r"^[a-f0-9-]{4,}$")
CardId = constr(pattern=r"^[a-f0-9-]{4,}$")


class DeckCreate(BaseModel):  # Модель для создания колоды
    name: constr(
        min_length=1, max_length=100
    )  # Обязательное поле - имя колоды карточек
    description: Optional[constr(max_length=500)] = (
        None  # Необязательное поле - описание колоды
    )


class DeckOut(BaseModel):  # Модель для вывода информации о колоде
    id: DeckId  # Айди колоды
    name: str  # Имя колоды
    description: Optional[str] = None  # Описание колоды
    cards: int = 0  # Количество карточек в колоде


class CardCreate(BaseModel):  # Модель для создания карточки
    front: constr(min_length=1, max_length=200)  # Вопрос или слово на карточке
    back: constr(min_length=1, max_length=500)  # Ответ или перевод на карточке
    hint: Optional[constr(max_length=200)] = (
        None  # Необязательная подсказка для карточки
    )


class CardOut(BaseModel):  # Модель для вывода информации о карточке
    id: CardId  # Айди карточки
    deck_id: DeckId  # Айди колоды, к которой принадлежит карточка
    front: str  # Вопрос или слово на карточке
    back: str  # Ответ или перевод на карточке
    hint: Optional[str] = None  # Подсказка для карточки
    due_at: Optional[datetime] = None  # Дата, когда карточка должна быть повторена
    interval_days: int = 0  # Интервал в днях до следующего повторения
    ease: float = 2.5  # Коэффициент легкости карточки


class ReviewIn(BaseModel):  # Модель для отправки ответа по карточке
    card_id: CardId  # Айди карточки
    grade: constr(
        pattern="^(again|hard|good)$"
    )  # Оценка ответа: "again", "hard" или "good"

    @field_validator("grade")  # Приводим оценку к нижнему регистру
    def _norm(cls, v):
        return v.lower()
