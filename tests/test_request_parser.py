import pytest

from tripmate.request import EXAMPLE, parse_request


def test_example_request() -> None:
    assert parse_request(EXAMPLE) == {"origin": "HYD", "destination": "BLR", "date": "2026-10-31"}


def test_lowercase_codes_and_trailing_period() -> None:
    assert parse_request("please book del to bom on 2026-11-02.") == {
        "origin": "DEL",
        "destination": "BOM",
        "date": "2026-11-02",
    }


def test_date_is_kept_as_written() -> None:
    assert parse_request("Book HYD to BLR on 31/10/2026")["date"] == "31/10/2026"


def test_unreadable_request() -> None:
    with pytest.raises(ValueError, match="could not read the trip"):
        parse_request("Book me something nice")
