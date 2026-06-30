"""Доменная модель: нормализованное событие календаря."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Event:
    """Событие календаря, нормализованное под нужды приложения.

    start всегда timezone-aware (UTC). link — ссылка на видеовстречу или None.
    """

    uid: str
    title: str
    start: datetime
    link: str | None
