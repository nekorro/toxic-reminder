from datetime import datetime, timedelta, timezone

from toxic_reminder.models import Event
from toxic_reminder.scheduler import Scheduler

NOW = datetime(2026, 6, 29, 9, 0, tzinfo=timezone.utc)
WINDOW = 90  # секунд до и после старта


def _ev(uid, seconds_from_now, link="https://telemost.yandex.ru/j/x"):
    return Event(uid=uid, title=uid, start=NOW + timedelta(seconds=seconds_from_now), link=link)


def test_fires_at_start():
    s = Scheduler(allowed_notification_window=WINDOW)
    s.update_events([_ev("a", 0)])
    assert [e.uid for e in s.tick(NOW)] == ["a"]


def test_fires_within_window_before_start():
    # старт через 60с, окно 90с -> срабатывает заранее
    s = Scheduler(allowed_notification_window=WINDOW)
    s.update_events([_ev("a", 60)])
    assert [e.uid for e in s.tick(NOW)] == ["a"]


def test_does_not_fire_before_window():
    # старт через 120с, окно 90с -> ещё рано
    s = Scheduler(allowed_notification_window=WINDOW)
    s.update_events([_ev("a", 120)])
    assert s.tick(NOW) == []


def test_fires_within_window_after_start():
    s = Scheduler(allowed_notification_window=WINDOW)
    s.update_events([_ev("a", 0)])
    assert [e.uid for e in s.tick(NOW + timedelta(seconds=60))] == ["a"]


def test_does_not_fire_after_window():
    s = Scheduler(allowed_notification_window=WINDOW)
    s.update_events([_ev("a", 0)])
    assert s.tick(NOW + timedelta(seconds=120)) == []


def test_fires_only_once():
    s = Scheduler(allowed_notification_window=WINDOW)
    s.update_events([_ev("a", 0)])
    assert len(s.tick(NOW)) == 1
    assert s.tick(NOW + timedelta(seconds=30)) == []


def test_ignores_events_without_link():
    s = Scheduler(allowed_notification_window=WINDOW)
    s.update_events([_ev("a", 0, link=None)])
    assert s.tick(NOW) == []


def test_next_event_returns_soonest_future():
    s = Scheduler()
    s.update_events([_ev("late", 3000), _ev("soon", 600), _ev("past", -6000)])
    assert s.next_event(NOW).uid == "soon"


def test_next_event_none_when_empty():
    s = Scheduler()
    s.update_events([])
    assert s.next_event(NOW) is None
