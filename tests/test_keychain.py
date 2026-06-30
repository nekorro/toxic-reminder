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
