from toxic_reminder import config as config_mod
from toxic_reminder.config import Config


def test_defaults():
    c = Config()
    assert c.server_url == "https://caldav.yandex-team.ru"
    assert c.refresh_interval_sec == 300
    assert c.lookahead_hours == 24
    assert c.allowed_notification_window == 60
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


def test_default_link_patterns():
    from toxic_reminder.link_extractor import DEFAULT_PATTERNS
    assert Config().link_patterns == list(DEFAULT_PATTERNS)


def test_link_patterns_independent_per_instance():
    a, b = Config(), Config()
    a.link_patterns.append("x")
    assert "x" not in b.link_patterns
