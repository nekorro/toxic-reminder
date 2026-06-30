import plistlib

from toxic_reminder import launchagent


def test_render_plist_keys():
    data = plistlib.loads(launchagent.render_plist("/venv/bin/python", "/proj", True))
    assert data["Label"] == launchagent.LABEL
    assert data["ProgramArguments"] == ["/venv/bin/python", "-m", "toxic_reminder.app"]
    assert data["WorkingDirectory"] == "/proj"
    assert data["RunAtLoad"] is True
    assert data["KeepAlive"] is True


def test_render_plist_keep_alive_false():
    data = plistlib.loads(launchagent.render_plist("/p", "/d", False))
    assert data["KeepAlive"] is False


def test_read_keep_alive_true(tmp_path):
    p = tmp_path / "a.plist"
    p.write_bytes(launchagent.render_plist("/p", "/d", True))
    assert launchagent.read_keep_alive(p) is True


def test_read_keep_alive_false(tmp_path):
    p = tmp_path / "a.plist"
    p.write_bytes(launchagent.render_plist("/p", "/d", False))
    assert launchagent.read_keep_alive(p) is False


def test_read_keep_alive_missing_defaults_true(tmp_path):
    assert launchagent.read_keep_alive(tmp_path / "nope.plist") is True
