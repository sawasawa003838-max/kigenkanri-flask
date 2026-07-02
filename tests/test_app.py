import sqlite3
from datetime import date

import pytest

import app as app_module


@pytest.fixture()
def client(tmp_path):
    test_db = tmp_path / "test.db"
    app_module.app.config["TESTING"] = True
    app_module.app.config["DATABASE"] = str(test_db)

    app_module.init_db()

    with app_module.app.test_client() as client:
        yield client


def fetch_foods():
    conn = sqlite3.connect(app_module.app.config["DATABASE"])
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, date FROM foods ORDER BY id")
    foods = cursor.fetchall()
    conn.close()
    return foods


def count_foods():
    return len(fetch_foods())


def add_food(name="milk", date="2026-05-20"):
    conn = sqlite3.connect(app_module.app.config["DATABASE"])
    cursor = conn.cursor()
    cursor.execute("INSERT INTO foods (name, date) VALUES (?, ?)", (name, date))
    food_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return food_id


def test_home_page_is_displayed(client):
    response = client.get("/")

    assert response.status_code == 200


def test_can_create_food_with_calculated_expiry_date(client):
    response = client.post(
        "/",
        data={"name": "milk", "open_date": "2026-05-20", "days": "3"},
    )

    assert response.status_code == 200
    assert fetch_foods() == [(1, "milk", "2026-05-23")]


def test_can_edit_food(client):
    food_id = add_food()

    response = client.post(
        f"/edit/{food_id}",
        data={"name": "cheese", "date": "2026-05-25"},
    )

    assert response.status_code == 302
    assert fetch_foods() == [(food_id, "cheese", "2026-05-25")]


def test_can_delete_food(client):
    food_id = add_food()

    response = client.post(f"/delete/{food_id}")

    assert response.status_code == 302
    assert fetch_foods() == []


def test_empty_food_name_does_not_save(client):
    response = client.post(
        "/",
        data={"name": "", "open_date": "2026-05-20", "days": "3"},
    )

    assert response.status_code != 500
    assert fetch_foods() == []


def test_invalid_open_date_does_not_save(client):
    response = client.post(
        "/",
        data={"name": "milk", "open_date": "not-a-date", "days": "3"},
    )

    assert response.status_code != 500
    assert fetch_foods() == []


@pytest.mark.parametrize(
    ("days", "should_save"),
    [
        ("3", True),
        ("0", False),
        ("-1", False),
        ("abc", False),
        ("3651", False),
        ("999999999999999999999999999999", False),
        ("9" * 5000, False),
    ],
)
def test_days_validation(client, days, should_save):
    before = count_foods()

    response = client.post(
        "/",
        data={
            "name": f"food-{days}",
            "open_date": "2026-05-24",
            "days": days,
        },
    )

    after = count_foods()
    body = response.get_data(as_text=True)

    assert response.status_code != 500
    if should_save:
        assert after == before + 1
    else:
        assert after == before
    assert (app_module.ERROR_SHELF_LIFE_DAYS in body) != should_save


def test_days_input_has_max_attribute(client):
    response = client.get("/")

    assert 'max="3650"' in response.get_data(as_text=True)


def test_expiry_date_overflow_shows_error_without_saving(client):
    before = count_foods()

    response = client.post(
        "/",
        data={
            "name": "overflow-date",
            "open_date": "9999-12-31",
            "days": "1",
        },
    )

    after = count_foods()
    body = response.get_data(as_text=True)

    assert response.status_code != 500
    assert after == before
    assert app_module.ERROR_DATE_OVERFLOW in body


@pytest.mark.parametrize(
    ("name", "date"),
    [
        ("", "2026-05-20"),
        ("milk", ""),
        ("milk", "not-a-date"),
    ],
)
def test_invalid_edit_does_not_update_food(client, name, date):
    food_id = add_food()

    response = client.post(
        f"/edit/{food_id}",
        data={"name": name, "date": date},
    )

    assert response.status_code != 500
    assert fetch_foods() == [(food_id, "milk", "2026-05-20")]


def test_edit_missing_id_does_not_return_500(client):
    response = client.post(
        "/edit/999",
        data={"name": "milk", "date": "2026-05-20"},
    )

    assert response.status_code != 500


def test_delete_missing_id_does_not_return_500(client):
    response = client.post("/delete/999")

    assert response.status_code != 500


def test_expiry_status_is_expired_for_yesterday():
    today = date(2026, 7, 2)

    status = app_module.determine_expiry_status("2026-07-01", today)

    assert status == app_module.STATUS_EXPIRED


def test_expiry_status_is_expiring_soon_for_today():
    today = date(2026, 7, 2)

    status = app_module.determine_expiry_status("2026-07-02", today)

    assert status == app_module.STATUS_EXPIRING_SOON


def test_expiry_status_is_expiring_soon_for_three_days_later():
    today = date(2026, 7, 2)

    status = app_module.determine_expiry_status("2026-07-05", today)

    assert status == app_module.STATUS_EXPIRING_SOON


def test_expiry_status_is_normal_for_four_days_later():
    today = date(2026, 7, 2)

    status = app_module.determine_expiry_status("2026-07-06", today)

    assert status == app_module.STATUS_NORMAL
