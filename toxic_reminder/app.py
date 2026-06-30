"""Меню-бар приложение: опрашивает CalDAV и показывает плашку в момент встречи."""

import datetime as dt
import logging
import pathlib
import sys

import rumps

from . import config as config_mod
from .banner import show_banner
from .caldav_client import fetch_events
from .scheduler import Scheduler

log = logging.getLogger(__name__)

_TICK_SECONDS = 30
_ICON_PATH = str(pathlib.Path(__file__).parent / "assets" / "heart-kawaii-retro-style.png")
_TEST_LINK = "https://telemost.yandex.ru/j/0429743918"


def _setup_logging() -> None:
    """Лог в stdout. При автозапуске launchd перенаправляет stdout в файл
    /tmp/toxic-reminder.out.log (см. launchd/ru.nekorro.toxic-reminder.plist)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def _local_time(when: dt.datetime) -> str:
    """ЧЧ:ММ в локальной зоне."""
    return when.astimezone().strftime("%H:%M")


def _local_datetime(when: dt.datetime) -> str:
    """ДД.ММ ЧЧ:ММ в локальной зоне."""
    return when.astimezone().strftime("%d.%m %H:%M")


class ToxicReminderApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("toxic-reminder", icon=_ICON_PATH, quit_button=None)
        self.config = config_mod.load()
        self.scheduler = Scheduler(
            allowed_notification_window=self.config.allowed_notification_window
        )
        self.muted = False

        self.next_item = rumps.MenuItem("Загрузка…")
        self.menu = [
            self.next_item,
            None,
            rumps.MenuItem("Обновить", callback=self.on_refresh),
            rumps.MenuItem("Показать тестовую нотификацию", callback=self.on_test_banner),
            rumps.MenuItem("Замьютить нотификации", callback=self.on_toggle_mute),
            None,
            rumps.MenuItem("Выход", callback=self.on_quit),
        ]

        self._refresh_timer = rumps.Timer(self.on_refresh, self.config.refresh_interval_sec)
        self._tick_timer = rumps.Timer(self.on_tick, _TICK_SECONDS)
        self._refresh_timer.start()
        self._tick_timer.start()
        self.on_refresh(None)

    @staticmethod
    def _now() -> dt.datetime:
        return dt.datetime.now(dt.timezone.utc)

    def on_refresh(self, _) -> None:
        if not self.config.login:
            self.next_item.title = "Укажите login в ~/.toxic-reminder/config.json"
            return
        try:
            now = self._now()
            events = fetch_events(self.config, now)
            self.scheduler.update_events(events)
            self._update_menu()
            nxt = self.scheduler.next_event(now)
            log.info("refresh: %d events; next=%s", len(events),
                     f"{_local_datetime(nxt.start)} {nxt.title}" if nxt else "none")
        except Exception as exc:  # сеть/креды — показываем в меню, не падаем
            log.exception("refresh failed")
            self.next_item.title = f"Ошибка: {exc}"

    def on_tick(self, _) -> None:
        if not self.muted:
            for event in self.scheduler.tick(self._now()):
                log.info("banner: %s at %s", event.title, _local_time(event.start))
                show_banner(event.title, _local_time(event.start), event.link)
        self._update_menu()

    def _update_menu(self) -> None:
        nxt = self.scheduler.next_event(self._now())
        if nxt is None:
            self.next_item.title = f"Нет встреч следующие {self.config.lookahead_hours}h"
        else:
            self.next_item.title = f"{_local_datetime(nxt.start)} — {nxt.title}"

    def on_toggle_mute(self, sender) -> None:
        self.muted = not self.muted
        sender.state = self.muted
        sender.title = "Размьютить нотификации" if self.muted else "Замьютить нотификации"
        log.info("notifications %s", "muted" if self.muted else "unmuted")

    def on_test_banner(self, _) -> None:
        show_banner("Тестовая встреча", _local_time(self._now()), _TEST_LINK)

    def on_quit(self, _) -> None:
        rumps.quit_application()


def main() -> None:
    _setup_logging()
    log.info("toxic-reminder starting")
    ToxicReminderApp().run()


if __name__ == "__main__":
    main()
