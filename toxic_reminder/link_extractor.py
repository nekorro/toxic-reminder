"""Извлечение ссылки на видеовстречу из полей VEVENT. Без сети — чистая логика.

Шаблоны провайдеров настраиваются через Config.link_patterns; здесь лежат
дефолты (DEFAULT_PATTERNS), которые используются, если ничего не передано.
"""

import re
from collections.abc import Mapping, Sequence
from functools import lru_cache

# Дефолтные шаблоны (регулярки) известных провайдеров видеовстреч.
DEFAULT_PATTERNS: tuple[str, ...] = (
    r"https://telemost\.(?:[\w-]+\.)*yandex\.ru/\S+",  # Telemost, в т.ч. telemost.360.yandex.ru
    r"https://meet\.google\.com/\S+",
    r"https://[\w.-]*zoom\.us/\S+",
    r"https://teams\.microsoft\.com/\S+",
)

# Поля, где ссылка лежит «как есть» (приоритет — порядок в кортеже).
_DIRECT_FIELDS = ("URL", "CONFERENCE")
# Поля со свободным текстом, где ссылку нужно искать.
_TEXT_FIELDS = ("LOCATION", "DESCRIPTION")


@lru_cache(maxsize=16)
def _compile(patterns: tuple[str, ...]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)


def _first_match(text: str, regex: re.Pattern) -> str | None:
    m = regex.search(text)
    return m.group(0) if m else None


def extract_link(
    fields: Mapping[str, str], patterns: Sequence[str] | None = None
) -> str | None:
    """Вернуть первую ссылку на видеовстречу или None.

    :param patterns: список регулярок провайдеров; None → DEFAULT_PATTERNS.
    Порядок поиска: прямые поля URL/CONFERENCE → X-*-поля с конференцией → текст.
    """
    regex = _compile(tuple(patterns) if patterns else DEFAULT_PATTERNS)

    # 1. Прямые поля: значение целиком должно быть ссылкой провайдера.
    for key in _DIRECT_FIELDS:
        val = fields.get(key)
        if val and (link := _first_match(val.strip(), regex)):
            return link

    # 2. X-*-свойства, относящиеся к конференции.
    for key, val in fields.items():
        upper = key.upper()
        if upper.startswith("X-") and ("CONF" in upper or "TELEMOST" in upper or "MEET" in upper):
            if val and (link := _first_match(val.strip(), regex)):
                return link

    # 3. Свободный текст.
    for key in _TEXT_FIELDS:
        val = fields.get(key)
        if val and (link := _first_match(val, regex)):
            return link

    return None
