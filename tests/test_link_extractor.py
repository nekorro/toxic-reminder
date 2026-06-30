from toxic_reminder.link_extractor import extract_link


def test_telemost_in_url_field():
    fields = {"URL": "https://telemost.yandex.ru/j/0429743918"}
    assert extract_link(fields) == "https://telemost.yandex.ru/j/0429743918"


def test_telemost_in_description():
    fields = {"DESCRIPTION": "Повестка дня\nПодключиться: https://telemost.yandex.ru/j/123 спасибо"}
    assert extract_link(fields) == "https://telemost.yandex.ru/j/123"


def test_telemost_in_location():
    fields = {"LOCATION": "https://telemost.yandex.ru/j/999"}
    assert extract_link(fields) == "https://telemost.yandex.ru/j/999"


def test_google_meet_in_description():
    fields = {"DESCRIPTION": "join https://meet.google.com/abc-defg-hij now"}
    assert extract_link(fields) == "https://meet.google.com/abc-defg-hij"


def test_zoom_and_teams():
    assert extract_link({"DESCRIPTION": "https://us02web.zoom.us/j/8412"}) == "https://us02web.zoom.us/j/8412"
    assert extract_link({"DESCRIPTION": "https://teams.microsoft.com/l/meetup-join/xyz"}) == "https://teams.microsoft.com/l/meetup-join/xyz"


def test_url_field_takes_priority_over_description():
    fields = {
        "URL": "https://telemost.yandex.ru/j/aaa",
        "DESCRIPTION": "запасная https://telemost.yandex.ru/j/bbb",
    }
    assert extract_link(fields) == "https://telemost.yandex.ru/j/aaa"


def test_x_conference_property():
    fields = {"X-TELEMOST-CONFERENCE": "https://telemost.yandex.ru/j/xprop"}
    assert extract_link(fields) == "https://telemost.yandex.ru/j/xprop"


def test_no_link_returns_none():
    assert extract_link({"LOCATION": "переговорка 5", "DESCRIPTION": "без ссылки"}) is None


def test_empty_fields():
    assert extract_link({}) is None


def test_non_meeting_url_in_description_ignored():
    fields = {"DESCRIPTION": "см. https://wiki.yandex-team.ru/page"}
    assert extract_link(fields) is None


def test_telemost_360_subdomain():
    fields = {"DESCRIPTION": "Link to the video meeting: https://telemost.360.yandex.ru/j/2199875878"}
    assert extract_link(fields) == "https://telemost.360.yandex.ru/j/2199875878"


def test_custom_patterns_match_new_provider():
    fields = {"DESCRIPTION": "join https://vc.example.com/room/42 now"}
    # дефолтные шаблоны такой домен не знают
    assert extract_link(fields) is None
    # но кастомный шаблон — находит
    assert extract_link(fields, [r"https://vc\.example\.com/\S+"]) == "https://vc.example.com/room/42"
