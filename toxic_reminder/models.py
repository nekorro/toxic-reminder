"""Доменная модель: нормализованное событие календаря."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Event:
    """Событие календаря, нормализованное под нужды приложения.

    start/end всегда timezone-aware (UTC); end — None, если не задан в событии.
    link — ссылка на видеовстречу или None.
    """

    uid: str
    title: str
    start: datetime
    link: str | None
    end: datetime | None = None
