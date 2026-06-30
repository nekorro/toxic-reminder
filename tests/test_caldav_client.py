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
