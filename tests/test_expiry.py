from datetime import datetime, timedelta

import pytest
from werkzeug.exceptions import Gone

from drop.expiry import (
    EXPIRY_CHOICES,
    abort_if_expired,
    expires_at_from,
    parse_expires_in,
)
from drop.models import Link

NOW = datetime(2026, 1, 1, 12, 0, 0)


def test_choices_are_one_hour_one_day_seven_days():
    assert set(EXPIRY_CHOICES) == {3600, 86400, 604800}


@pytest.mark.parametrize("value", [None, ""])
def test_parse_never(value):
    assert parse_expires_in(value) is None


@pytest.mark.parametrize("value", [3600, 86400, 604800, "3600", "604800"])
def test_parse_allowed_values(value):
    assert parse_expires_in(value) == int(value)


@pytest.mark.parametrize(
    "value", [0, 60, -3600, "abc", "3600.0", " 3600", 3600.0, True, [3600], {}]
)
def test_parse_rejects_other_values(value):
    with pytest.raises(ValueError):
        parse_expires_in(value)


def test_expires_at_from_adds_seconds():
    assert expires_at_from(3600, now=NOW) == NOW + timedelta(hours=1)
    assert expires_at_from(None, now=NOW) is None


def test_abort_if_expired_raises_410_only_after_expiry():
    abort_if_expired(Link(slug="a", kind="url"))  # nie
    abort_if_expired(Link(slug="b", kind="url", expires_at=datetime(2999, 1, 1)))

    with pytest.raises(Gone):
        abort_if_expired(Link(slug="c", kind="url", expires_at=datetime(2000, 1, 1)))
