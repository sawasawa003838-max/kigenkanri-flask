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

    assert status == app_module.EXPIRY_STATUS_EXPIRED


def test_expiry_status_is_expiring_soon_for_today():
    today = date(2026, 7, 2)

    status = app_module.determine_expiry_status("2026-07-02", today)

    assert status == app_module.EXPIRY_STATUS_SOON


def test_expiry_status_is_expiring_soon_for_three_days_later():
    today = date(2026, 7, 2)

    status = app_module.determine_expiry_status("2026-07-05", today)

    assert status == app_module.EXPIRY_STATUS_SOON


def test_expiry_status_is_normal_for_four_days_later():
    today = date(2026, 7, 2)

    status = app_module.determine_expiry_status("2026-07-06", today)

    assert status == app_module.EXPIRY_STATUS_NORMAL


def test_fetch_foods_includes_expiry_status(client):
    reference_date = date(2026, 6, 1)

    food_id = add_food(
        name="milk",
        date="2026-06-04",
    )

    foods = app_module.fetch_foods(
        reference_date=reference_date
    )

    assert foods == [
        app_module.Food(
            id=food_id,
            name="milk",
            expiry_date="2026-06-04",
            expiry_status=app_module.EXPIRY_STATUS_SOON,
        )
    ]


def test_invalid_expiry_date_does_not_return_500(client):
    add_food(
        name="invalid-date-food",
        date="not-a-date",
    )

    foods = app_module.fetch_foods(
        reference_date=date(2026, 6, 1)
    )

    response = client.get("/")

    assert foods[0].expiry_status == (
        app_module.EXPIRY_STATUS_INVALID
    )
    assert response.status_code == 200


def test_home_page_shows_expiry_status(client):
    add_food(
        name="invalid-date-food",
        date="not-a-date",
    )

    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert app_module.EXPIRY_STATUS_INVALID in body


def test_build_notification_email_includes_expired_food():
    expired_food = app_module.Food(
        id=1,
        name="milk",
        expiry_date="2026-07-19",
        expiry_status=app_module.EXPIRY_STATUS_EXPIRED,
    )

    subject, body = app_module.build_notification_email(
        [expired_food]
    )

    assert subject == "【賞味期限管理】確認が必要な食品があります"
    assert "milk" in body
    assert "2026-07-19" in body
    assert app_module.EXPIRY_STATUS_EXPIRED in body


def test_build_notification_email_includes_expiring_soon_food():
    food = app_module.Food(
        id=2,
        name="eggs",
        expiry_date="2026-07-22",
        expiry_status=app_module.EXPIRY_STATUS_SOON,
    )

    subject, body = app_module.build_notification_email([food])

    assert "eggs" in body
    assert "2026-07-22" in body
    assert app_module.EXPIRY_STATUS_SOON in body


def test_build_notification_email_keeps_food_order():
    milk = app_module.Food(
        id=1,
        name="milk",
        expiry_date="2026-07-19",
        expiry_status=app_module.EXPIRY_STATUS_EXPIRED,
    )
    eggs = app_module.Food(
        id=2,
        name="eggs",
        expiry_date="2026-07-22",
        expiry_status=app_module.EXPIRY_STATUS_SOON,
    )

    subject, body = app_module.build_notification_email(
        [milk, eggs]
    )

    assert body.index("milk") < body.index("eggs")


def test_build_notification_email_returns_none_for_empty_targets():
    result = app_module.build_notification_email([])

    assert result is None


def test_build_notification_email_creates_email_for_expired_food():
    expired_food = app_module.Food(
        id=1,
        name="牛乳",
        expiry_date="2026-07-19",
        expiry_status=app_module.EXPIRY_STATUS_EXPIRED,
    )

    subject, body = app_module.build_notification_email(
        [expired_food]
    )

    assert subject == "【賞味期限管理】確認が必要な食品があります"
    assert body == (
        "期限の確認が必要な食品をお知らせします。\n"
        "\n"
        "・牛乳（期限：2026-07-19、状態：期限切れ）\n"
        "\n"
        "食品の状態を確認してください。"
    )


def test_build_notification_email_includes_multiple_targets_in_order():
    expired_food = app_module.Food(
        id=1,
        name="牛乳",
        expiry_date="2026-07-19",
        expiry_status=app_module.EXPIRY_STATUS_EXPIRED,
    )
    expiring_soon_food = app_module.Food(
        id=2,
        name="卵",
        expiry_date="2026-07-22",
        expiry_status=app_module.EXPIRY_STATUS_SOON,
    )

    subject, body = app_module.build_notification_email(
        [
            expired_food,
            expiring_soon_food,
        ]
    )

    assert subject == "【賞味期限管理】確認が必要な食品があります"
    assert "・牛乳（期限：2026-07-19、状態：期限切れ）" in body
    assert "・卵（期限：2026-07-22、状態：期限間近）" in body
    assert body.index("牛乳") < body.index("卵")


def test_send_notification_email_sends_expected_email(monkeypatch):
    expired_food = app_module.Food(
        id=1,
        name="牛乳",
        expiry_date="2026-07-19",
        expiry_status=app_module.EXPIRY_STATUS_EXPIRED,
    )

    sent_params = {}

    def fake_send(params):
        sent_params.update(params)
        return {"id": "test-email-id"}

    monkeypatch.setattr(
        app_module.resend.Emails,
        "send",
        fake_send,
    )

    result = app_module.send_notification_email(
        [expired_food],
        sender_email="sender@example.com",
        recipient_email="store@example.com",
    )

    assert result == {"id": "test-email-id"}
    assert sent_params["from"] == "sender@example.com"
    assert sent_params["to"] == ["store@example.com"]
    assert sent_params["subject"] == (
        "【賞味期限管理】確認が必要な食品があります"
    )
    assert "牛乳" in sent_params["text"]


def test_send_notification_email_does_not_send_when_targets_are_empty(
    monkeypatch,
):
    send_was_called = False

    def fake_send(params):
        nonlocal send_was_called
        send_was_called = True
        return {"id": "test-email-id"}

    monkeypatch.setattr(
        app_module.resend.Emails,
        "send",
        fake_send,
    )

    result = app_module.send_notification_email(
        [],
        sender_email="sender@example.com",
        recipient_email="store@example.com",
    )

    assert result is None
    assert send_was_called is False
