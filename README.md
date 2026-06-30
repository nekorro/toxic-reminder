# toxic-reminder

Меню-бар приложение для macOS против пропущенных встреч. Читает
календарь по CalDAV и **в момент начала встречи** с видеоссылкой
показывает яркую красную плашку поверх всех окон с кнопками **«Скрыть»** и
**«Подключиться»** (открывает ссылку на видеовстречу из события).

## Возможности

- Плашка поверх всех окон и Spaces в момент начала встречи, с кнопками
  «Скрыть» / «Подключиться».
- Иконка в меню-баре со строкой ближайшей встречи (`ДД.ММ ЧЧ:ММ — Название`).
- Срабатывает только для встреч с видеоссылкой (список настраивается).
- Возможность замьютить нотификации.
- Пароль хранится в macOS Keychain.

## Требования

- macOS.
- Python 3.12+.

## Установка

**1. Код и виртуальное окружение** (из корня проекта):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

**2. Конфиг с вашим логином:**

```bash
mkdir -p ~/.toxic-reminder
printf '{\n  "login": "LOGIN@CALDAV-DOMAIN"\n}\n' > ~/.toxic-reminder/config.json
```

**3. Пароль в Keychain**:

```bash
.venv/bin/python -m toxic_reminder.setpw
```

**4. Запуск:**

```bash
.venv/bin/python -m toxic_reminder.app
```

В меню-баре появится иконка-сердечко. Готово — для постоянной работы настройте
[автозапуск](#автозапуск).

## Пароль

Хранится в macOS Keychain (служба `toxic-reminder`, аккаунт — ваш `login`)
Задать/обновить:

```bash
.venv/bin/python -m toxic_reminder.setpw
```

Альтернатива — напрямую через `security add-generic-password`:

```bash
security add-generic-password -a "ВАШ_ЛОГИН@yandex-team.ru" -s "toxic-reminder" -w -U
```

## Конфигурация

`~/.toxic-reminder/config.json`:

| Поле | По умолчанию | Описание |
|------|--------------|---------- |
| `login` | `""` | `логин@yandex-team.ru` |
| `server_url` | `https://caldav.yandex-team.ru` | CalDAV-сервер |
| `refresh_interval_sec` | `300` | Период обновления календаря (секунды) |
| `lookahead_hours` | `24` | Окно выборки событий вперёд (часы) |
| `allowed_notification_window` | `60` | Окно показа плашки: ±N секунд вокруг старта встречи |
| `link_patterns` | (см. ниже) | Regexp ссылок на видеовстречу |

После правки конфига перезапустите приложение.

`link_patterns` по умолчанию (учтите экранирование `\\` в JSON):

```json
[
  "https://telemost\\.(?:[\\w-]+\\.)*yandex\\.ru/\\S+",
  "https://meet\\.google\\.com/\\S+",
  "https://[\\w.-]*zoom\\.us/\\S+",
  "https://teams\\.microsoft\\.com/\\S+"
]
```

Чтобы ловить свой сервис, добавьте в массив regexp-выражение, например
`"https://vc\\.mycorp\\.ru/\\S+"`.

## Меню

- **Ближайшая встреча** — `ДД.ММ ЧЧ:ММ — Название` или `Нет встреч следующие <lookahead_hours>h`.
- **Обновить** — перечитать календарь сейчас.
- **Показать тестовую нотификацию** — показать тестовую плашку с кнопками.
- **Замьютить нотификации** — временно отключить нотификации.
- **Запустить агент** / **Остановить агент** — переключатель автозапуска
  (название меняется по состоянию):
  - *Запустить агент* — ставит LaunchAgent с автозапуском при логине и
    автоперезапуском, стартует его и закрывает текущий процесс (чтобы не было
    двух копий).
  - *Остановить агент* — удаляет агент (отключает автозапуск и автоперезапуск).

## Автозапуск

Проще всего — через меню **Запустить агент**: приложение само
сгенерирует plist с актуальными путями и загрузит агент. Вручную:

```bash
sed -e "s#__VENV_PYTHON__#$(pwd)/.venv/bin/python#" \
    -e "s#__PROJECT_DIR__#$(pwd)#" \
    launchd/ru.nekorro.toxic-reminder.plist \
    > ~/Library/LaunchAgents/ru.nekorro.toxic-reminder.plist
launchctl load ~/Library/LaunchAgents/ru.nekorro.toxic-reminder.plist
```

Остановить можно через пункт меню **Остановить агент** или вручную : `launchctl unload ~/Library/LaunchAgents/ru.nekorro.toxic-reminder.plist`

## Логи

- При ручном запуске лог пишется в **stdout**.
- При автозапуске launchd перенаправляет вывод в `/tmp/toxic-reminder.out.log`
  и `/tmp/toxic-reminder.err.log`.

## Тесты

```bash
.venv/bin/python -m pytest -q
```
