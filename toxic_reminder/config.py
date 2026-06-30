"""Конфигурация приложения в ~/.toxic-reminder/config.json."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .link_extractor import DEFAULT_PATTERNS

DEFAULT_PATH = Path.home() / ".toxic-reminder" / "config.json"


@dataclass
class Config:
    login: str = ""
    server_url: str = "https://caldav.yandex-team.ru"
    refresh_interval_sec: int = 300
    lookahead_hours: int = 24
    allowed_notification_window: int = 60  # секунд до и после старта встречи
    link_patterns: list[str] = field(default_factory=lambda: list(DEFAULT_PATTERNS))


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
