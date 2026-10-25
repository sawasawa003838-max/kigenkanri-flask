"""SQLiteの読み書き。DBパスは呼び出し元から受け取り、Flaskに依存しない。"""

import sqlite3
from contextlib import closing
from dataclasses import dataclass

from expiry import determine_expiry_status


@dataclass
class Food:
    id: int
    name: str
    expiry_date: str
    expiry_status: str


def get_db_connection(database):
    return sqlite3.connect(database)


def init_db(database):
    with closing(get_db_connection(database)) as conn, conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS foods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT NOT NULL
            )
        """)


def fetch_foods(database, reference_date=None):
    with closing(get_db_connection(database)) as conn:
        rows = conn.execute("SELECT id, name, date FROM foods").fetchall()

    return [
        Food(food_id, name, expiry_date,
             determine_expiry_status(expiry_date, reference_date))
        for food_id, name, expiry_date in rows
    ]


def get_food(database, food_id):
    with closing(get_db_connection(database)) as conn:
        return conn.execute(
            "SELECT name, date FROM foods WHERE id = ?", (food_id,)
        ).fetchone()


def insert_food(database, name, expiry_date):
    with closing(get_db_connection(database)) as conn, conn:
        cursor = conn.execute(
            "INSERT INTO foods (name, date) VALUES (?, ?)", (name, expiry_date)
        )
        return cursor.lastrowid


def update_food(database, food_id, name, expiry_date):
    with closing(get_db_connection(database)) as conn, conn:
        conn.execute(
            "UPDATE foods SET name = ?, date = ? WHERE id = ?",
            (name, expiry_date, food_id),
        )


def delete_food(database, food_id):
    with closing(get_db_connection(database)) as conn, conn:
        conn.execute("DELETE FROM foods WHERE id = ?", (food_id,))
