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
