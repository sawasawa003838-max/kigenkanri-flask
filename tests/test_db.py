import sqlite3
from datetime import date

import pytest

import db
import expiry


def test_existing_schema_and_data_survive_initialization(tmp_path):
    database = tmp_path / "existing.db"
    # 改修前と同じスキーマを、改修後の初期化に渡す。
    with sqlite3.connect(database) as conn:
        conn.execute("""CREATE TABLE foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL
        )""")
        conn.execute(
            "INSERT INTO foods VALUES (?, ?, ?)", (42, "milk", "2026-07-05")
        )

    db.init_db(database)
    db.init_db(database)

    assert db.fetch_foods(database, date(2026, 7, 2)) == [
        db.Food(42, "milk", "2026-07-05", expiry.EXPIRY_STATUS_SOON)
    ]
    assert db.insert_food(database, "eggs", "2026-07-06") == 43


def test_crud_without_flask_context(tmp_path):
    database = tmp_path / "foods.db"
    db.init_db(database)
    food_id = db.insert_food(database, "milk'; DROP TABLE foods;--", "2026-07-05")
    assert db.get_food(database, food_id) == (
        "milk'; DROP TABLE foods;--", "2026-07-05"
    )
    db.update_food(database, food_id, "cheese", "2026-07-06")
    assert db.get_food(database, food_id) == ("cheese", "2026-07-06")
    db.delete_food(database, food_id)
    assert db.get_food(database, food_id) is None
    assert db.fetch_foods(database) == []


def test_failed_write_keeps_existing_data_and_allows_next_write(tmp_path):
    database = tmp_path / "foods.db"
    db.init_db(database)
    food_id = db.insert_food(database, "milk", "2026-07-05")

    with pytest.raises(sqlite3.IntegrityError):
        db.update_food(database, food_id, None, "2026-07-06")

    assert db.get_food(database, food_id) == ("milk", "2026-07-05")
    db.update_food(database, food_id, "cheese", "2026-07-06")
    assert db.get_food(database, food_id) == ("cheese", "2026-07-06")
