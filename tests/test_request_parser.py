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


def test_keywords_in_any_case() -> None:
    assert parse_request("BOOK HYD TO BLR ON 2026-10-31")["destination"] == "BLR"
    assert parse_request("Book a flight from HYD To BLR On 2026-10-31!")["origin"] == "HYD"


def test_malformed_date_is_kept_whole() -> None:
    assert parse_request("Book HYD to BLR on 2026-10-31-")["date"] == "2026-10-31-"


def test_two_routes_are_rejected() -> None:
    with pytest.raises(ValueError, match="could not read the trip"):
        parse_request("Do not book HYD to BLR; book DEL to BOM on 2026-11-02")


def test_long_garbage_is_rejected_quickly() -> None:
    with pytest.raises(ValueError, match="could not read the trip"):
        parse_request("AAA to BBB " * 20000)


@pytest.mark.parametrize("code", ["H\u0131D", "H\u0130D", "H\u212aD"])
def test_airport_codes_are_ascii_letters_only(code: str) -> None:
    with pytest.raises(ValueError, match="could not read the trip"):
        parse_request(f"Book {code} to BLR on 2026-10-31")
