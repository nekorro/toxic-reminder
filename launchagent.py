"""Управление LaunchAgent (launchd): установка/удаление с автозапуском.

plist генерируется динамически с актуальными путями (sys.executable + корень
проекта). «Установлен» (plist на месте) ⇒ автозапуск при логине (RunAtLoad) и
автоперезапуск (KeepAlive) включены.
"""

import os
import plistlib
import subprocess
import sys
from pathlib import Path

LABEL = "ru.nekorro.toxic-reminder"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
_OUT_LOG = "/tmp/toxic-reminder.out.log"
_ERR_LOG = "/tmp/toxic-reminder.err.log"


def render_plist(python: str, workdir: str, keep_alive: bool) -> bytes:
    """Собрать содержимое plist (bytes) для LaunchAgent."""
    return plistlib.dumps({
        "Label": LABEL,
        "ProgramArguments": [python, "-m", "toxic_reminder.app"],
        "WorkingDirectory": workdir,
        "RunAtLoad": True,
        "KeepAlive": keep_alive,
        "StandardOutPath": _OUT_LOG,
        "StandardErrorPath": _ERR_LOG,
    })


def read_keep_alive(plist_path: Path = PLIST_PATH) -> bool:
    """KeepAlive из установленного plist; True, если plist ещё нет."""
    if not plist_path.exists():
        return True
    return bool(plistlib.loads(plist_path.read_bytes()).get("KeepAlive", False))


def is_installed() -> bool:
    return PLIST_PATH.exists()


def _project_dir() -> str:
    return str(Path(__file__).resolve().parent.parent)


def _domain() -> str:
    return f"gui/{os.getuid()}"


def _target() -> str:
    return f"{_domain()}/{LABEL}"


def _launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["launchctl", *args], capture_output=True, text=True)


def write_plist(keep_alive: bool) -> None:
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_bytes(render_plist(sys.executable, _project_dir(), keep_alive))


def install(keep_alive: bool = True) -> None:
    """Записать plist (RunAtLoad + KeepAlive) и загрузить агент."""
    write_plist(keep_alive)
    result = _launchctl("bootstrap", _domain(), str(PLIST_PATH))
    if result.returncode != 0:
        PLIST_PATH.unlink(missing_ok=True)
        raise RuntimeError(result.stderr.strip() or f"bootstrap failed ({result.returncode})")


def uninstall() -> None:
    """Удалить plist и выгрузить агент (откл. автозапуск и автоперезапуск).

    plist удаляем ПЕРВЫМ: если текущий процесс — это сам агент, последующий
    bootout завершит его, и важно, чтобы plist к тому моменту уже был удалён.
    """
    PLIST_PATH.unlink(missing_ok=True)
    _launchctl("bootout", _target())
