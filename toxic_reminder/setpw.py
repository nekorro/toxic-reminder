"""CLI: сохранить доменный пароль в Keychain со скрытым вводом в терминале.

Запуск:  python -m toxic_reminder.setpw

Пароль читается через getpass (не отображается на экране и не пишется в файл) и
кладётся в Keychain под службой `toxic-reminder` для аккаунта config.login.
"""

import getpass

from . import config as config_mod
from .keychain import set_password


def main() -> None:
    config = config_mod.load()
    if not config.login:
        raise SystemExit("Сначала укажите login в ~/.toxic-reminder/config.json")
    password = getpass.getpass(f"Доменный пароль для {config.login}: ")
    if not password:
        raise SystemExit("Пустой пароль — отмена.")
    set_password(config.login, password)
    print(f"Пароль сохранён в Keychain (служба toxic-reminder, аккаунт {config.login}).")


if __name__ == "__main__":
    main()
