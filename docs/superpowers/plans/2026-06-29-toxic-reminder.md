# toxic-reminder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Меню-бар приложение на macOS, которое напрямую по CalDAV читает Яндексовый календарь и в момент начала встречи с видеоссылкой показывает яркую красную плашку поверх всех окон с кнопками «Скрыть» и «Подключиться».

**Architecture:** Изолированные Python-модули с одной ответственностью. Вся логика (извлечение ссылки, конфиг, Keychain, парсинг событий, планировщик) вынесена из UI и покрыта тестами. UI-слой (`banner.py` на PyObjC, `app.py` на rumps) тонкий и проверяется вручную. Приложение опрашивает планировщик таймером rumps и периодически обновляет события по CalDAV.

**Tech Stack:** Python 3.14, `rumps` (меню-бар), `pyobjc-framework-Cocoa` (плашка), `caldav` + `icalendar` (календарь), `pytest` (тесты), macOS Keychain через `security` CLI, автозапуск через `launchd`.

---

## File Structure

| Файл | Ответственность |
|------|-----------------|
| `toxic_reminder/__init__.py` | Пакет (пустой). |
| `toxic_reminder/models.py` | `Event` dataclass. |
| `toxic_reminder/link_extractor.py` | Чистая функция `extract_link(fields) -> str \| None`. |
| `toxic_reminder/config.py` | `Config` dataclass + `load`/`save`. |
| `toxic_reminder/keychain.py` | `get_password`/`set_password` через `security`. |
| `toxic_reminder/caldav_client.py` | `parse_events` (чистый) + `fetch_events` (сеть). |
| `toxic_reminder/scheduler.py` | `Scheduler`: `update_events`/`next_event`/`tick`. |
| `toxic_reminder/banner.py` | PyObjC плашка `show_banner`. |
| `toxic_reminder/app.py` | rumps меню-бар, `main()`. |
| `tests/test_link_extractor.py` | Тесты извлечения ссылки. |
| `tests/test_config.py` | Тесты конфига. |
| `tests/test_keychain.py` | Тесты Keychain (мок `subprocess`). |
| `tests/test_caldav_client.py` | Тесты `parse_events` на ICS-строках. |
| `tests/test_scheduler.py` | Тесты планировщика. |
| `requirements.txt` / `requirements-dev.txt` | Зависимости. |
| `launchd/ru.nekorro.toxic-reminder.plist` | LaunchAgent. |
| `README.md` | Установка и запуск. |

---

## Task 0: Scaffolding

**Files:**
- Create: `requirements.txt`, `requirements-dev.txt`, `toxic_reminder/__init__.py`, `tests/__init__.py`, `pytest.ini`

- [ ] **Step 1: Create requirements files**

`requirements.txt`:
```
rumps>=0.4.0
pyobjc-framework-Cocoa>=10.0
caldav>=1.3.0
icalendar>=5.0.0
```

`requirements-dev.txt`:
```
-r requirements.txt
pytest>=8.0
```

- [ ] **Step 2: Create package files**

`toxic_reminder/__init__.py`:
```python
"""toxic-reminder: агрессивные напоминания о встречах для macOS."""
```

`tests/__init__.py`: (пустой файл)

`pytest.ini`:
```ini
[pytest]
testpaths = tests
```

- [ ] **Step 3: Create venv and install dev deps**

Run:
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```
Expected: установка без ошибок (есть колёса под Python 3.14 / macOS).

- [ ] **Step 4: Verify pytest runs**

Run: `.venv/bin/python -m pytest -q`
Expected: `no tests ran` (тестов ещё нет) — это успех.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt requirements-dev.txt toxic_reminder/__init__.py tests/__init__.py pytest.ini
git commit -m "chore: scaffold toxic-reminder package and tooling"
```

---

## Task 1: Event model

**Files:**
- Create: `toxic_reminder/models.py`

- [ ] **Step 1: Write the model**

`toxic_reminder/models.py`:
```python
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
```

- [ ] **Step 2: Commit**

```bash
git add toxic_reminder/models.py
git commit -m "feat: add Event model"
```

---

## Task 2: Link extractor

**Files:**
- Create: `toxic_reminder/link_extractor.py`
- Test: `tests/test_link_extractor.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_link_extractor.py`:
```python
from toxic_reminder.link_extractor import extract_link


def test_telemost_in_url_field():
    fields = {"URL": "https://telemost.yandex.ru/j/0429743918"}
    assert extract_link(fields) == "https://telemost.yandex.ru/j/0429743918"


def test_telemost_in_description():
    fields = {"DESCRIPTION": "Повестка дня\nПодключиться: https://telemost.yandex.ru/j/123 спасибо"}
    assert extract_link(fields) == "https://telemost.yandex.ru/j/123"


def test_telemost_in_location():
    fields = {"LOCATION": "https://telemost.yandex.ru/j/999"}
    assert extract_link(fields) == "https://telemost.yandex.ru/j/999"


def test_google_meet_in_description():
    fields = {"DESCRIPTION": "join https://meet.google.com/abc-defg-hij now"}
    assert extract_link(fields) == "https://meet.google.com/abc-defg-hij"


def test_zoom_and_teams():
    assert extract_link({"DESCRIPTION": "https://us02web.zoom.us/j/8412"}) == "https://us02web.zoom.us/j/8412"
    assert extract_link({"DESCRIPTION": "https://teams.microsoft.com/l/meetup-join/xyz"}) == "https://teams.microsoft.com/l/meetup-join/xyz"


def test_url_field_takes_priority_over_description():
    fields = {
        "URL": "https://telemost.yandex.ru/j/aaa",
        "DESCRIPTION": "запасная https://telemost.yandex.ru/j/bbb",
    }
    assert extract_link(fields) == "https://telemost.yandex.ru/j/aaa"


def test_x_conference_property():
    fields = {"X-TELEMOST-CONFERENCE": "https://telemost.yandex.ru/j/xprop"}
    assert extract_link(fields) == "https://telemost.yandex.ru/j/xprop"


def test_no_link_returns_none():
    assert extract_link({"LOCATION": "переговорка 5", "DESCRIPTION": "без ссылки"}) is None


def test_empty_fields():
    assert extract_link({}) is None


def test_non_meeting_url_in_description_ignored():
    fields = {"DESCRIPTION": "см. https://wiki.yandex-team.ru/page"}
    assert extract_link(fields) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_link_extractor.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'toxic_reminder.link_extractor'`

- [ ] **Step 3: Write the implementation**

`toxic_reminder/link_extractor.py`:
```python
"""Извлечение ссылки на видеовстречу из полей VEVENT. Без сети — чистая логика."""

import re
from collections.abc import Mapping

# Известные провайдеры видеовстреч.
_PROVIDER_RE = re.compile(
    r"https://(?:"
    r"telemost\.yandex\.ru/\S+"
    r"|meet\.google\.com/\S+"
    r"|[\w.-]*zoom\.us/\S+"
    r"|teams\.microsoft\.com/\S+"
    r")",
    re.IGNORECASE,
)

# Поля, где ссылка лежит «как есть» (приоритет — порядок в кортеже).
_DIRECT_FIELDS = ("URL", "CONFERENCE")
# Поля со свободным текстом, где ссылку нужно искать.
_TEXT_FIELDS = ("LOCATION", "DESCRIPTION")


def _first_match(text: str) -> str | None:
    m = _PROVIDER_RE.search(text)
    return m.group(0) if m else None


def extract_link(fields: Mapping[str, str]) -> str | None:
    """Вернуть первую ссылку на видеовстречу или None.

    Порядок: прямые поля URL/CONFERENCE → X-*-поля с конференцией → текстовые поля.
    """
    # 1. Прямые поля: значение целиком должно быть ссылкой провайдера.
    for key in _DIRECT_FIELDS:
        val = fields.get(key)
        if val and (link := _first_match(val.strip())):
            return link

    # 2. X-*-свойства, относящиеся к конференции.
    for key, val in fields.items():
        upper = key.upper()
        if upper.startswith("X-") and ("CONF" in upper or "TELEMOST" in upper or "MEET" in upper):
            if val and (link := _first_match(val.strip())):
                return link

    # 3. Свободный текст.
    for key in _TEXT_FIELDS:
        val = fields.get(key)
        if val and (link := _first_match(val)):
            return link

    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_link_extractor.py -q`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add toxic_reminder/link_extractor.py tests/test_link_extractor.py
git commit -m "feat: add link extractor for video meeting URLs"
```

---

## Task 3: Config

**Files:**
- Create: `toxic_reminder/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:
```python
from toxic_reminder import config as config_mod
from toxic_reminder.config import Config


def test_defaults():
    c = Config()
    assert c.server_url == "https://caldav.yandex-team.ru"
    assert c.refresh_interval_sec == 300
    assert c.lookahead_hours == 24
    assert c.grace_seconds == 90
    assert c.login == ""


def test_load_missing_returns_defaults(tmp_path):
    c = config_mod.load(tmp_path / "nope.json")
    assert c == Config()


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "sub" / "config.json"
    original = Config(login="user@yandex-team.ru", lookahead_hours=12)
    config_mod.save(original, path)
    assert path.exists()
    loaded = config_mod.load(path)
    assert loaded == original


def test_load_ignores_unknown_keys(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"login": "u@yandex-team.ru", "bogus": 1}')
    loaded = config_mod.load(path)
    assert loaded.login == "u@yandex-team.ru"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_config.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'toxic_reminder.config'`

- [ ] **Step 3: Write the implementation**

`toxic_reminder/config.py`:
```python
"""Конфигурация приложения в ~/.toxic-reminder/config.json."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_PATH = Path.home() / ".toxic-reminder" / "config.json"


@dataclass
class Config:
    login: str = ""
    server_url: str = "https://caldav.yandex-team.ru"
    refresh_interval_sec: int = 300
    lookahead_hours: int = 24
    grace_seconds: int = 90


def load(path: Path = DEFAULT_PATH) -> Config:
    path = Path(path)
    if not path.exists():
        return Config()
    data = json.loads(path.read_text(encoding="utf-8"))
    known = {k: v for k, v in data.items() if k in Config.__dataclass_fields__}
    return Config(**known)


def save(config: Config, path: Path = DEFAULT_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(config), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_config.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add toxic_reminder/config.py tests/test_config.py
git commit -m "feat: add config load/save"
```

---

## Task 4: Keychain

**Files:**
- Create: `toxic_reminder/keychain.py`
- Test: `tests/test_keychain.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_keychain.py`:
```python
import subprocess

from toxic_reminder import keychain


def test_get_password_success(monkeypatch):
    def fake_run(cmd, **kwargs):
        assert cmd[:2] == ["security", "find-generic-password"]
        return subprocess.CompletedProcess(cmd, 0, stdout="s3cret\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert keychain.get_password("user@yandex-team.ru") == "s3cret"


def test_get_password_not_found(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(44, cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert keychain.get_password("user@yandex-team.ru") is None


def test_set_password_invokes_add(monkeypatch):
    calls = {}

    def fake_run(cmd, **kwargs):
        calls["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    keychain.set_password("user@yandex-team.ru", "p@ss")
    assert calls["cmd"][:2] == ["security", "add-generic-password"]
    assert "p@ss" in calls["cmd"]
    assert "-U" in calls["cmd"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_keychain.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'toxic_reminder.keychain'`

- [ ] **Step 3: Write the implementation**

`toxic_reminder/keychain.py`:
```python
"""Доступ к доменному паролю в macOS Keychain через CLI `security`."""

import subprocess

SERVICE = "toxic-reminder"


def get_password(account: str) -> str | None:
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-a", account, "-s", SERVICE, "-w"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return None
    return result.stdout.strip() or None


def set_password(account: str, password: str) -> None:
    subprocess.run(
        ["security", "add-generic-password", "-a", account, "-s", SERVICE, "-w", password, "-U"],
        capture_output=True,
        text=True,
        check=True,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_keychain.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add toxic_reminder/keychain.py tests/test_keychain.py
git commit -m "feat: add Keychain password storage"
```

---

## Task 5: CalDAV client (parse_events)

**Files:**
- Create: `toxic_reminder/caldav_client.py`
- Test: `tests/test_caldav_client.py`

Примечание: `fetch_events` (сеть) не покрывается юнит-тестами; тестируем чистый `parse_events`.

- [ ] **Step 1: Write the failing tests**

`tests/test_caldav_client.py`:
```python
from datetime import datetime, timedelta, timezone

from toxic_reminder.caldav_client import parse_events


def _ics(uid, summary, dtstart_utc, extra=""):
    stamp = dtstart_utc.strftime("%Y%m%dT%H%M%SZ")
    return (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\n"
        f"UID:{uid}\r\nSUMMARY:{summary}\r\nDTSTART:{stamp}\r\n{extra}"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    )


NOW = datetime(2026, 6, 29, 9, 0, tzinfo=timezone.utc)


def test_parses_event_with_telemost_link():
    ics = _ics("u1", "Стендап", NOW + timedelta(hours=1),
               "URL:https://telemost.yandex.ru/j/111\r\n")
    events = parse_events([ics], NOW, timedelta(hours=24))
    assert len(events) == 1
    ev = events[0]
    assert ev.uid == "u1"
    assert ev.title == "Стендап"
    assert ev.link == "https://telemost.yandex.ru/j/111"
    assert ev.start == NOW + timedelta(hours=1)


def test_event_without_link_has_none():
    ics = _ics("u2", "Без ссылки", NOW + timedelta(hours=2))
    events = parse_events([ics], NOW, timedelta(hours=24))
    assert events[0].link is None


def test_events_outside_window_excluded():
    ics = _ics("u3", "Завтра+", NOW + timedelta(hours=48))
    assert parse_events([ics], NOW, timedelta(hours=24)) == []


def test_past_events_excluded():
    ics = _ics("u4", "Час назад", NOW - timedelta(hours=1))
    assert parse_events([ics], NOW, timedelta(hours=24)) == []


def test_just_started_event_included_within_lookback():
    ics = _ics("u5", "Только что", NOW - timedelta(minutes=2))
    events = parse_events([ics], NOW, timedelta(hours=24))
    assert len(events) == 1


def test_all_day_event_skipped():
    ics = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\n"
        "UID:u6\r\nSUMMARY:Весь день\r\nDTSTART;VALUE=DATE:20260629\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    assert parse_events([ics], NOW, timedelta(hours=24)) == []


def test_results_sorted_by_start():
    a = _ics("a", "Позже", NOW + timedelta(hours=5))
    b = _ics("b", "Раньше", NOW + timedelta(hours=1))
    events = parse_events([a, b], NOW, timedelta(hours=24))
    assert [e.uid for e in events] == ["b", "a"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_caldav_client.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'toxic_reminder.caldav_client'`

- [ ] **Step 3: Write the implementation**

`toxic_reminder/caldav_client.py`:
```python
"""Чтение событий по CalDAV и парсинг iCalendar в Event."""

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from icalendar import Calendar

from .config import Config
from .keychain import get_password
from .link_extractor import extract_link
from .models import Event

# Поля VEVENT, из которых извлекается ссылка.
_LINK_FIELDS = ("URL", "CONFERENCE", "LOCATION", "DESCRIPTION")
# Насколько назад от now ещё считаем событие актуальным (только что начавшееся).
_LOOKBACK = timedelta(minutes=5)


def _to_utc(value) -> datetime | None:
    """datetime → UTC-aware; date (all-day) → None (пропускаем)."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


def parse_events(
    ical_texts: Iterable[str], now: datetime, lookahead: timedelta
) -> list[Event]:
    """Распарсить ICS-строки в отсортированный список Event внутри окна."""
    window_start = now - _LOOKBACK
    window_end = now + lookahead
    events: list[Event] = []

    for text in ical_texts:
        cal = Calendar.from_ical(text)
        for comp in cal.walk("VEVENT"):
            dtstart = comp.get("DTSTART")
            if dtstart is None:
                continue
            start = _to_utc(dtstart.dt)
            if start is None or not (window_start <= start <= window_end):
                continue

            fields: dict[str, str] = {}
            for key in _LINK_FIELDS:
                val = comp.get(key)
                if val is not None:
                    fields[key] = str(val)
            for key in comp.keys():
                if key.upper().startswith("X-"):
                    fields[key.upper()] = str(comp.get(key))

            events.append(
                Event(
                    uid=str(comp.get("UID", "")),
                    title=str(comp.get("SUMMARY", "(без названия)")),
                    start=start,
                    link=extract_link(fields),
                )
            )

    events.sort(key=lambda e: e.start)
    return events


def fetch_events(config: Config, now: datetime) -> list[Event]:
    """Сходить на CalDAV-сервер и вернуть события. Требует пароль в Keychain.

    Не покрыто юнит-тестами (сеть). Проверяется вручную.
    """
    import caldav

    password = get_password(config.login)
    if not password:
        raise RuntimeError("Пароль не задан. Меню → «Задать пароль».")

    client = caldav.DAVClient(
        url=config.server_url, username=config.login, password=password
    )
    principal = client.principal()
    lookahead = timedelta(hours=config.lookahead_hours)

    texts: list[str] = []
    for calendar in principal.calendars():
        found = calendar.search(
            start=now - _LOOKBACK,
            end=now + lookahead,
            event=True,
            expand=True,
        )
        texts.extend(obj.data for obj in found)

    return parse_events(texts, now, lookahead)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_caldav_client.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add toxic_reminder/caldav_client.py tests/test_caldav_client.py
git commit -m "feat: add CalDAV event parsing and fetching"
```

---

## Task 6: Scheduler

**Files:**
- Create: `toxic_reminder/scheduler.py`
- Test: `tests/test_scheduler.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_scheduler.py`:
```python
from datetime import datetime, timedelta, timezone

from toxic_reminder.models import Event
from toxic_reminder.scheduler import Scheduler

NOW = datetime(2026, 6, 29, 9, 0, tzinfo=timezone.utc)


def _ev(uid, minutes_from_now, link="https://telemost.yandex.ru/j/x"):
    return Event(uid=uid, title=uid, start=NOW + timedelta(minutes=minutes_from_now), link=link)


def test_tick_fires_at_start():
    s = Scheduler(grace_seconds=90)
    s.update_events([_ev("a", 0)])
    due = s.tick(NOW)
    assert [e.uid for e in due] == ["a"]


def test_tick_does_not_fire_before_start():
    s = Scheduler(grace_seconds=90)
    s.update_events([_ev("a", 1)])  # начнётся через минуту
    assert s.tick(NOW) == []


def test_tick_within_grace():
    # начали 60с назад, grace 90с — должно сработать
    s = Scheduler(grace_seconds=90)
    s.update_events([_ev("a", 0)])
    assert [e.uid for e in s.tick(NOW + timedelta(seconds=60))] == ["a"]


def test_tick_after_grace_does_not_fire():
    s = Scheduler(grace_seconds=90)
    s.update_events([_ev("a", 0)])
    assert s.tick(NOW + timedelta(seconds=120)) == []


def test_tick_fires_only_once():
    s = Scheduler(grace_seconds=90)
    s.update_events([_ev("a", 0)])
    assert len(s.tick(NOW)) == 1
    assert s.tick(NOW + timedelta(seconds=30)) == []


def test_tick_ignores_events_without_link():
    s = Scheduler(grace_seconds=90)
    s.update_events([_ev("a", 0, link=None)])
    assert s.tick(NOW) == []


def test_next_event_returns_soonest_future():
    s = Scheduler()
    s.update_events([_ev("late", 50), _ev("soon", 10), _ev("past", -100)])
    nxt = s.next_event(NOW)
    assert nxt.uid == "soon"


def test_next_event_none_when_empty():
    s = Scheduler()
    s.update_events([])
    assert s.next_event(NOW) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_scheduler.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'toxic_reminder.scheduler'`

- [ ] **Step 3: Write the implementation**

`toxic_reminder/scheduler.py`:
```python
"""Планировщик: решает, для каких событий показать плашку. Чистая логика."""

from datetime import datetime

from .models import Event


class Scheduler:
    def __init__(self, grace_seconds: int = 90) -> None:
        self._grace = grace_seconds
        self._events: list[Event] = []
        self._shown: set[str] = set()

    def update_events(self, events: list[Event]) -> None:
        self._events = list(events)

    def next_event(self, now: datetime) -> Event | None:
        upcoming = [e for e in self._events if e.start >= now]
        return min(upcoming, key=lambda e: e.start) if upcoming else None

    def tick(self, now: datetime) -> list[Event]:
        """Вернуть события, которые только что начались (в пределах grace) и ещё
        не показывались. Помечает их как показанные."""
        due: list[Event] = []
        for event in self._events:
            if not event.link or event.uid in self._shown:
                continue
            elapsed = (now - event.start).total_seconds()
            if 0 <= elapsed <= self._grace:
                due.append(event)
                self._shown.add(event.uid)
        return due
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_scheduler.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Run full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS (все тесты зелёные)

- [ ] **Step 6: Commit**

```bash
git add toxic_reminder/scheduler.py tests/test_scheduler.py
git commit -m "feat: add scheduler with grace-window deduplicated triggering"
```

---

## Task 7: Banner (PyObjC)

**Files:**
- Create: `toxic_reminder/banner.py`

UI-слой. Юнит-тестами не покрывается — проверяется вручную (Step 3).

- [ ] **Step 1: Write the implementation**

`toxic_reminder/banner.py`:
```python
"""Яркая красная плашка поверх всех окон с кнопками «Скрыть»/«Подключиться»."""

import objc
import AppKit

# Контроллеры держим в модульном списке, чтобы их не собрал GC, пока окно открыто.
_controllers: list = []


class BannerController(AppKit.NSObject):
    def initWithTitle_time_link_(self, title, time_str, link):
        self = objc.super(BannerController, self).init()
        if self is None:
            return None
        self.link = link
        self.window = self._build(title, time_str, bool(link))
        return self

    def _build(self, title, time_str, has_link):
        frame = AppKit.NSScreen.mainScreen().frame()
        height = 160.0
        rect = AppKit.NSMakeRect(0, frame.size.height - height, frame.size.width, height)
        win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            AppKit.NSWindowStyleMaskBorderless,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        win.setLevel_(AppKit.NSScreenSaverWindowLevel)
        win.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        win.setBackgroundColor_(
            AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.80, 0.05, 0.05, 1.0)
        )
        win.setReleasedWhenClosed_(False)
        view = win.contentView()

        label = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(40, 72, frame.size.width - 80, 70)
        )
        label.setStringValue_(f"{time_str}  {title}")
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.setTextColor_(AppKit.NSColor.whiteColor())
        label.setFont_(AppKit.NSFont.boldSystemFontOfSize_(32))
        view.addSubview_(label)

        dismiss = AppKit.NSButton.alloc().initWithFrame_(AppKit.NSMakeRect(40, 24, 160, 44))
        dismiss.setTitle_("Скрыть")
        dismiss.setBezelStyle_(AppKit.NSBezelStyleRounded)
        dismiss.setTarget_(self)
        dismiss.setAction_("dismiss:")
        view.addSubview_(dismiss)

        if has_link:
            connect = AppKit.NSButton.alloc().initWithFrame_(
                AppKit.NSMakeRect(212, 24, 240, 44)
            )
            connect.setTitle_("Подключиться")
            connect.setBezelStyle_(AppKit.NSBezelStyleRounded)
            connect.setKeyEquivalent_("\r")
            connect.setTarget_(self)
            connect.setAction_("connect:")
            view.addSubview_(connect)

        win.makeKeyAndOrderFront_(None)
        AppKit.NSApp.activateIgnoringOtherApps_(True)
        return win

    def connect_(self, sender):
        if self.link:
            url = AppKit.NSURL.URLWithString_(self.link)
            if url is not None:
                AppKit.NSWorkspace.sharedWorkspace().openURL_(url)
        self._close()

    def dismiss_(self, sender):
        self._close()

    def _close(self):
        self.window.orderOut_(None)
        if self in _controllers:
            _controllers.remove(self)


def show_banner(title: str, time_str: str, link: str | None) -> "BannerController":
    controller = BannerController.alloc().initWithTitle_time_link_(title, time_str, link)
    _controllers.append(controller)
    return controller
```

- [ ] **Step 2: Add a manual demo entry point**

В конец `toxic_reminder/banner.py` добавить:
```python
if __name__ == "__main__":
    show_banner("Тестовая встреча", "12:30", "https://telemost.yandex.ru/j/0429743918")
    AppKit.NSApp.run()
```

- [ ] **Step 3: Manual smoke test**

Run: `.venv/bin/python -m toxic_reminder.banner`
Expected: сверху экрана появляется красная плашка с текстом «12:30 Тестовая встреча» и двумя кнопками. «Подключиться» открывает ссылку в браузере и закрывает плашку; «Скрыть» закрывает её. (Закрыть процесс: Ctrl-C.)

- [ ] **Step 4: Commit**

```bash
git add toxic_reminder/banner.py
git commit -m "feat: add fullscreen red banner with connect/dismiss buttons"
```

---

## Task 8: Menu-bar app (rumps)

**Files:**
- Create: `toxic_reminder/app.py`

UI-слой. Проверяется вручную (Step 2).

- [ ] **Step 1: Write the implementation**

`toxic_reminder/app.py`:
```python
"""Меню-бар приложение: опрашивает CalDAV и показывает плашку в момент встречи."""

import datetime as dt

import rumps

from . import config as config_mod
from .banner import show_banner
from .caldav_client import fetch_events
from .keychain import set_password
from .scheduler import Scheduler

_TICK_SECONDS = 30


class ToxicReminderApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("⏰", quit_button=None)
        self.config = config_mod.load()
        self.scheduler = Scheduler(grace_seconds=self.config.grace_seconds)

        self.next_item = rumps.MenuItem("Загрузка…")
        self.menu = [
            self.next_item,
            None,
            rumps.MenuItem("Обновить", callback=self.on_refresh),
            rumps.MenuItem("Задать пароль", callback=self.on_set_password),
            None,
            rumps.MenuItem("Выход", callback=self.on_quit),
        ]

        self.refresh_timer = rumps.Timer(self.on_refresh, self.config.refresh_interval_sec)
        self.tick_timer = rumps.Timer(self.on_tick, _TICK_SECONDS)
        self.refresh_timer.start()
        self.tick_timer.start()
        self.on_refresh(None)

    @staticmethod
    def _now() -> dt.datetime:
        return dt.datetime.now(dt.timezone.utc)

    def on_refresh(self, _) -> None:
        if not self.config.login:
            self.next_item.title = "Укажите login в ~/.toxic-reminder/config.json"
            return
        try:
            events = fetch_events(self.config, self._now())
            self.scheduler.update_events(events)
            self._update_menu()
        except Exception as exc:  # сеть/креды — показываем в меню, не падаем
            self.next_item.title = f"Ошибка: {exc}"

    def on_tick(self, _) -> None:
        now = self._now()
        for event in self.scheduler.tick(now):
            local = event.start.astimezone()
            show_banner(event.title, local.strftime("%H:%M"), event.link)
        self._update_menu()

    def _update_menu(self) -> None:
        nxt = self.scheduler.next_event(self._now())
        if nxt is None:
            self.next_item.title = "Нет ближайших встреч"
            return
        local = nxt.start.astimezone()
        self.next_item.title = f"{local.strftime('%d.%m %H:%M')} — {nxt.title}"

    def on_set_password(self, _) -> None:
        window = rumps.Window(
            title="Доменный пароль",
            message=f"Пароль для {self.config.login}",
            secure=True,
            dimensions=(320, 24),
        )
        response = window.run()
        if response.clicked and response.text:
            set_password(self.config.login, response.text)
            self.on_refresh(None)

    def on_quit(self, _) -> None:
        rumps.quit_application()


def main() -> None:
    ToxicReminderApp().run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Manual smoke test**

1. Создать конфиг:
   ```bash
   mkdir -p ~/.toxic-reminder
   printf '{\n  "login": "ВАШ_ЛОГИН@yandex-team.ru"\n}\n' > ~/.toxic-reminder/config.json
   ```
2. Run: `.venv/bin/python -m toxic_reminder.app`
3. В меню-баре появляется «⏰». Открыть меню → «Задать пароль», ввести доменный пароль.
4. Ожидаемо: первая строка меню показывает ближайшую встречу `ДД.ММ ЧЧ:ММ — Название` (или «Нет ближайших встреч»). При наступлении встречи с видеоссылкой всплывает красная плашка.

Если CalDAV не пускает — проверить логин/пароль и доступность `caldav.yandex-team.ru`.

- [ ] **Step 3: Commit**

```bash
git add toxic_reminder/app.py
git commit -m "feat: add menu-bar app wiring scheduler, fetch and banner"
```

---

## Task 9: Autostart + README

**Files:**
- Create: `launchd/ru.nekorro.toxic-reminder.plist`, `README.md`

- [ ] **Step 1: Write the LaunchAgent plist**

`launchd/ru.nekorro.toxic-reminder.plist` (пути `__VENV_PYTHON__` и `__PROJECT_DIR__` заменяются при установке в Step 3):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ru.nekorro.toxic-reminder</string>
    <key>ProgramArguments</key>
    <array>
        <string>__VENV_PYTHON__</string>
        <string>-m</string>
        <string>toxic_reminder.app</string>
    </array>
    <key>WorkingDirectory</key>
    <string>__PROJECT_DIR__</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/tmp/toxic-reminder.err.log</string>
    <key>StandardOutPath</key>
    <string>/tmp/toxic-reminder.out.log</string>
</dict>
</plist>
```

- [ ] **Step 2: Write the README**

`README.md`:
```markdown
# toxic-reminder

Меню-бар приложение для macOS: читает Яндексовый календарь по CalDAV и в момент
начала встречи с видеоссылкой показывает яркую красную плашку поверх всех окон
с кнопками «Скрыть» и «Подключиться».

## Установка

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p ~/.toxic-reminder
printf '{\n  "login": "ВАШ_ЛОГИН@yandex-team.ru"\n}\n' > ~/.toxic-reminder/config.json
```

Запустить и задать пароль через меню → «Задать пароль»:

```bash
.venv/bin/python -m toxic_reminder.app
```

## Конфигурация

`~/.toxic-reminder/config.json`:

| Поле | По умолчанию | Описание |
|------|--------------|----------|
| `login` | `""` | `логин@yandex-team.ru` |
| `server_url` | `https://caldav.yandex-team.ru` | CalDAV-сервер |
| `refresh_interval_sec` | `300` | Период обновления календаря |
| `lookahead_hours` | `24` | Окно выборки событий вперёд |
| `grace_seconds` | `90` | Окно показа после начала встречи |

Доменный пароль хранится в macOS Keychain (служба `toxic-reminder`), не в файле.

## Автозапуск

```bash
sed -e "s#__VENV_PYTHON__#$(pwd)/.venv/bin/python#" \
    -e "s#__PROJECT_DIR__#$(pwd)#" \
    launchd/ru.nekorro.toxic-reminder.plist \
    > ~/Library/LaunchAgents/ru.nekorro.toxic-reminder.plist
launchctl load ~/Library/LaunchAgents/ru.nekorro.toxic-reminder.plist
```

Остановить: `launchctl unload ~/Library/LaunchAgents/ru.nekorro.toxic-reminder.plist`

## Тесты

```bash
.venv/bin/python -m pytest -q
```
```

- [ ] **Step 3: Verify plist install renders correct paths (dry run)**

Run:
```bash
sed -e "s#__VENV_PYTHON__#$(pwd)/.venv/bin/python#" \
    -e "s#__PROJECT_DIR__#$(pwd)#" \
    launchd/ru.nekorro.toxic-reminder.plist | grep -E "venv/bin/python|WorkingDirectory" -A1
```
Expected: видны абсолютные пути к `.venv/bin/python` и каталогу проекта (без `__…__`).

- [ ] **Step 4: Commit**

```bash
git add launchd/ru.nekorro.toxic-reminder.plist README.md
git commit -m "docs: add LaunchAgent autostart and README"
```

---

## Final Verification

- [ ] **Run the full test suite**

Run: `.venv/bin/python -m pytest -q`
Expected: все тесты проходят (link_extractor, config, keychain, caldav_client, scheduler).

- [ ] **Manual end-to-end**

Запустить `.venv/bin/python -m toxic_reminder.app`, убедиться что: иконка в меню-баре есть; ближайшая встреча отображается; для теста можно создать в календаре встречу с Telemost-ссылкой на ближайшую минуту и дождаться плашки.
