from datetime import date

import expiry
import pytest


@pytest.mark.parametrize("days", [-1, 0, 1, 2, 3, 4])
def test_all_status_boundaries(days):
    from datetime import timedelta

    today = date(2026, 7, 2)
    text = (today + timedelta(days=days)).isoformat()
    expected = (
        expiry.EXPIRY_STATUS_EXPIRED if days < 0
        else expiry.EXPIRY_STATUS_SOON if days <= 3
        else expiry.EXPIRY_STATUS_NORMAL
    )
    assert expiry.determine_expiry_status(text, today) == expected


@pytest.mark.parametrize("value", [None, "", "not-a-date", "2026-02-30"])
def test_invalid_status_dates(value):
    assert expiry.determine_expiry_status(value, date(2026, 7, 2)) == (
        expiry.EXPIRY_STATUS_INVALID
    )


def test_expiry_calculation_crosses_month_and_leap_day():
    assert expiry.calculate_expiry_date(date(2024, 2, 28), 2) == date(2024, 3, 1)


@pytest.mark.parametrize("value", ["", "0", "-1", "abc", "3651", "9" * 5000])
def test_invalid_shelf_life(value):
    assert expiry.validate_shelf_life_days(value) == (None, expiry.ERROR_SHELF_LIFE_DAYS)


@pytest.mark.parametrize("value", ["1", "3650"])
def test_valid_shelf_life_limits(value):
    assert expiry.validate_shelf_life_days(value) == (int(value), None)


def test_expiry_status_is_expired_for_yesterday():
    today = date(2026, 7, 2)

    status = expiry.determine_expiry_status("2026-07-01", today)

    assert status == expiry.EXPIRY_STATUS_EXPIRED


def test_expiry_status_is_expiring_soon_for_today():
    today = date(2026, 7, 2)

    status = expiry.determine_expiry_status("2026-07-02", today)

    assert status == expiry.EXPIRY_STATUS_SOON


def test_expiry_status_is_expiring_soon_for_three_days_later():
    today = date(2026, 7, 2)

    status = expiry.determine_expiry_status("2026-07-05", today)

    assert status == expiry.EXPIRY_STATUS_SOON


def test_expiry_status_is_normal_for_four_days_later():
    today = date(2026, 7, 2)

    status = expiry.determine_expiry_status("2026-07-06", today)

    assert status == expiry.EXPIRY_STATUS_NORMAL
