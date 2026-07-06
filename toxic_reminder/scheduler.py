"""Планировщик: решает, для каких событий показать плашку. Чистая логика."""

from datetime import datetime

from .models import Event


class Scheduler:
    """Хранит события и решает, для каких показать плашку.

    Плашка показывается один раз для каждого события (дедуп по UID) в окне
    ±allowed_notification_window секунд вокруг старта.
    """

    def __init__(self, allowed_notification_window: int = 60) -> None:
        self._window = allowed_notification_window
        self._events: list[Event] = []
        self._shown: set[str] = set()

    def update_events(self, events: list[Event]) -> None:
        self._events = list(events)

    def next_event(self, now: datetime) -> Event | None:
        upcoming = [e for e in self._events if e.start >= now]
        return min(upcoming, key=lambda e: e.start) if upcoming else None

    def current_event(self, now: datetime) -> Event | None:
        """Активная сейчас встреча (start <= now < end). Без end — не считается
        активной. При наложении — самая рано начавшаяся."""
        active = [e for e in self._events
                  if e.end is not None and e.start <= now < e.end]
        return min(active, key=lambda e: e.start) if active else None

    def tick(self, now: datetime) -> list[Event]:
        """Вернуть события в окне ±allowed_notification_window вокруг старта,
        которые ещё не показывались. Помечает их как показанные."""
        due: list[Event] = []
        for event in self._events:
            if not event.link or event.uid in self._shown:
                continue
            if abs((now - event.start).total_seconds()) <= self._window:
                due.append(event)
                self._shown.add(event.uid)
        return due
