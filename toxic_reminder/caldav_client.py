"""Чтение событий по CalDAV и парсинг iCalendar в Event."""

import logging
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta, timezone

from icalendar import Calendar

from .config import Config
from .keychain import get_password
from .link_extractor import extract_link
from .models import Event

log = logging.getLogger(__name__)

# Поля VEVENT, из которых извлекается ссылка.
_LINK_FIELDS = ("URL", "CONFERENCE", "LOCATION", "DESCRIPTION")
# Насколько назад от now ещё считаем событие актуальным (только что начавшееся).
_LOOKBACK = timedelta(minutes=5)


def _to_utc(value) -> datetime | None:
    """datetime → UTC-aware; date (all-day) → None (пропускаем)."""
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _link_fields(comp) -> dict[str, str]:
    """Строковые поля VEVENT, в которых может встретиться ссылка на встречу."""
    fields = {
        key: str(value)
        for key in _LINK_FIELDS
        if (value := comp.get(key)) is not None
    }
    for key in comp.keys():
        if key.upper().startswith("X-"):
            fields[key.upper()] = str(comp.get(key))
    return fields


def parse_events(
    ical_texts: Iterable[str],
    now: datetime,
    lookahead: timedelta,
    patterns: Sequence[str] | None = None,
) -> list[Event]:
    """Распарсить ICS-строки в отсортированный список Event внутри окна."""
    window_start = now - _LOOKBACK
    window_end = now + lookahead
    events: list[Event] = []

    for text in ical_texts:
        for comp in Calendar.from_ical(text).walk("VEVENT"):
            dtstart = comp.get("DTSTART")
            start = _to_utc(dtstart.dt) if dtstart is not None else None
            if start is None or not (window_start <= start <= window_end):
                continue
            events.append(
                Event(
                    uid=str(comp.get("UID", "")),
                    title=str(comp.get("SUMMARY", "(без названия)")),
                    start=start,
                    link=extract_link(_link_fields(comp), patterns),
                )
            )

    events.sort(key=lambda e: e.start)
    log.debug("parse_events: %d events in [%s .. %s]",
              len(events), window_start.isoformat(), window_end.isoformat())
    return events


def _calendar_name(calendar) -> str:
    getter = getattr(calendar, "get_display_name", None)
    return getter() if getter else str(calendar)


def fetch_events(config: Config, now: datetime) -> list[Event]:
    """Сходить на CalDAV-сервер и вернуть события за окно lookahead.

    Требует пароль в Keychain. Сетевая часть юнит-тестами не покрыта.
    """
    import caldav

    password = get_password(config.login)
    if not password:
        raise RuntimeError("Пароль не задан. Задайте его: python -m toxic_reminder.setpw")

    client = caldav.DAVClient(
        url=config.server_url, username=config.login, password=password
    )
    lookahead = timedelta(hours=config.lookahead_hours)
    calendars = client.principal().calendars()
    log.info("fetch_events: %d calendars, lookahead %dh",
             len(calendars), config.lookahead_hours)

    texts: list[str] = []
    for calendar in calendars:
        found = list(calendar.search(
            start=now - _LOOKBACK, end=now + lookahead, event=True, expand=True,
        ))
        log.debug("  %s: %d raw events", _calendar_name(calendar), len(found))
        texts.extend(obj.data for obj in found)

    events = parse_events(texts, now, lookahead, config.link_patterns)
    log.info("fetch_events: %d events after window+parse", len(events))
    return events
