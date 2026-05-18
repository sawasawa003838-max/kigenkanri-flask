import sqlite3

import pytest

from app import app, init_db


@pytest.fixture()
def client(tmp_path):
    test_db = tmp_path / "test.db"
    app.config["TESTING"] = True
    app.config["DATABASE"] = str(test_db)

    init_db()

    with app.test_client() as client:
        yield client


def fetch_foods():
    conn = sqlite3.connect(app.config["DATABASE"])
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, date FROM foods ORDER BY id")
    foods = cursor.fetchall()
    conn.close()
    return foods


def add_food(name="milk", date="2026-05-20"):
    conn = sqlite3.connect(app.config["DATABASE"])
    cursor = conn.cursor()
    cursor.execute("INSERT INTO foods (name, date) VALUES (?, ?)", (name, date))
    food_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return food_id


def test_home_page_is_displayed(client):
    response = client.get("/")

    assert response.status_code == 200


def test_can_create_food(client):
    response = client.post("/", data={"name": "milk", "date": "2026-05-20"})

    assert response.status_code == 200
    assert fetch_foods() == [(1, "milk", "2026-05-20")]


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


def test_empty_food_name_does_not_return_500(client):
    response = client.post("/", data={"name": "", "date": "2026-05-20"})

    assert response.status_code != 500


@pytest.mark.parametrize("date", ["", "not-a-date"])
def test_empty_or_invalid_date_does_not_return_500(client, date):
    response = client.post("/", data={"name": "milk", "date": date})

    assert response.status_code != 500


def test_non_numeric_storage_days_does_not_return_500(client):
    response = client.post(
        "/",
        data={"name": "milk", "date": "2026-05-20", "storage_days": "abc"},
    )

    assert response.status_code != 500


def test_storage_days_less_than_one_does_not_return_500(client):
    response = client.post(
        "/",
        data={"name": "milk", "date": "2026-05-20", "storage_days": "0"},
    )

    assert response.status_code != 500


def test_edit_missing_id_does_not_return_500(client):
    response = client.post(
        "/edit/999",
        data={"name": "milk", "date": "2026-05-20"},
    )

    assert response.status_code != 500


def test_delete_missing_id_does_not_return_500(client):
    response = client.post("/delete/999")

    assert response.status_code != 500
