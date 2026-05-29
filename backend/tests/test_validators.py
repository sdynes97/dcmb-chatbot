import services.validators as v


def test_valid_date():
    assert v.is_valid_date("2025-09-06")
    assert not v.is_valid_date("2025-13-06")   # bad month
    assert not v.is_valid_date("2025-02-30")   # not a real day
    assert not v.is_valid_date("09/06/2025")
    assert not v.is_valid_date("")


def test_valid_time():
    assert v.is_valid_time("17:30")
    assert v.is_valid_time("00:00")
    assert v.is_valid_time("23:59")
    assert v.is_valid_time("N/A")
    assert not v.is_valid_time("24:00")
    assert not v.is_valid_time("7:30")        # needs leading zero
    assert not v.is_valid_time("17:60")


def test_valid_iso_datetime():
    assert v.is_valid_iso_datetime("2025-09-06T22:45:00+00:00")
    assert v.is_valid_iso_datetime("2025-09-06T22:45:00")
    assert not v.is_valid_iso_datetime("not-a-date")
    assert not v.is_valid_iso_datetime("")


def test_valid_table_key():
    assert v.is_valid_table_key("2025-09-06_football-lincoln")
    assert not v.is_valid_table_key("has/slash")
    assert not v.is_valid_table_key("has\\backslash")
    assert not v.is_valid_table_key("has#hash")
    assert not v.is_valid_table_key("has?question")
    assert not v.is_valid_table_key("")


def test_valid_event_type():
    assert v.is_valid_event_type("football_game")
    assert not v.is_valid_event_type("birthday_party")


def test_validate_event_clean():
    body = {
        "partition_key": "2025",
        "row_key": "2025-09-06_game",
        "event_type": "football_game",
        "event_date": "2025-09-06",
        "call_time": "17:30",
        "performance_time": "19:00",
        "estimated_return": "22:00",
    }
    assert v.validate_event(body) == []


def test_validate_event_catches_bad_fields():
    body = {
        "partition_key": "bad/key",
        "row_key": "ok",
        "event_type": "nope",
        "event_date": "2025-99-99",
        "call_time": "7:5",
        "performance_time": "19:00",
        "estimated_return": "22:00",
    }
    errors = v.validate_event(body)
    assert any("partition_key" in e for e in errors)
    assert any("event_type" in e for e in errors)
    assert any("event_date" in e for e in errors)
    assert any("call_time" in e for e in errors)
