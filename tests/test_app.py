import sqlite3
from pathlib import Path

import pytest

import app as app_module


TEST_DB = Path(__file__).resolve().parents[1] / ".test-database.db"


@pytest.fixture
def client(monkeypatch):
    if TEST_DB.exists():
        TEST_DB.unlink()

    original_connect = sqlite3.connect

    def connect_test_db(*args, **kwargs):
        return original_connect(TEST_DB, **kwargs)

    monkeypatch.setattr(app_module.sqlite3, "connect", connect_test_db)
    app_module.app.config["TESTING"] = True
    app_module.init_db()

    yield app_module.app.test_client()

    if TEST_DB.exists():
        TEST_DB.unlink()


def count_foods():
    conn = sqlite3.connect(TEST_DB)
    try:
        return conn.execute("SELECT COUNT(*) FROM foods").fetchone()[0]
    finally:
        conn.close()


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
    assert after == before + 1 if should_save else after == before
    assert ("保存日数は1日以上3650日以下で入力してください" in body) != should_save


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
    assert "開封日と保存日数の組み合わせが大きすぎます" in body
