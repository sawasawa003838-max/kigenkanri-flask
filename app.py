import sqlite3
from datetime import date, timedelta

from flask import Flask, render_template, request, redirect

app = Flask(__name__)

MAX_SHELF_LIFE_DAYS = 3650


def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def calculate_expiry_date(open_date, shelf_life_days):
    return open_date + timedelta(days=shelf_life_days)


def fetch_foods():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM foods")
    foods = cursor.fetchall()
    conn.close()
    return foods


def render_home_with_error(error):
    return render_template(
        "index.html",
        foods=fetch_foods(),
        error=error,
        max_shelf_life_days=MAX_SHELF_LIFE_DAYS
    ), 400


def validate_name(name):
    name = name.strip()
    if name == "":
        return None, "食品名を入力してください"
    return name, None


def validate_iso_date(date_text, label):
    try:
        date.fromisoformat(date_text)
    except ValueError:
        return None, f"{label}を正しい形式で入力してください"
    return date_text, None


def validate_shelf_life_days(days_text):
    error = f"保存日数は1日以上{MAX_SHELF_LIFE_DAYS}日以下で入力してください"

    if not days_text.isdigit():
        return None, error

    try:
        days = int(days_text)
    except ValueError:
        return None, error
    if days < 1 or days > MAX_SHELF_LIFE_DAYS:
        return None, error

    return days, None


@app.route("/", methods=["GET", "POST"])
def home():
    error = None

    if request.method == "POST":
        name, error = validate_name(request.form.get("name", ""))
        open_date_text = request.form.get("open_date", "")
        days_text = request.form.get("days", "").strip()

        if error is None:
            days, error = validate_shelf_life_days(days_text)

        if error is None:
            try:
                open_date_obj = date.fromisoformat(open_date_text)
                expiry_date = calculate_expiry_date(open_date_obj, days)
                expiry_date_text = expiry_date.isoformat()

                conn = sqlite3.connect("database.db")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO foods (name, date) VALUES (?, ?)",
                    (name, expiry_date_text)
                )
                conn.commit()
                conn.close()
            except ValueError:
                error = "開封日を正しい形式で入力してください"

    return render_template(
        "index.html",
        foods=fetch_foods(),
        error=error,
        max_shelf_life_days=MAX_SHELF_LIFE_DAYS
    )


@app.route("/delete/<int:food_id>", methods=["POST"])
def delete_food(food_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM foods WHERE id = ?", (food_id,))

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/edit/<int:food_id>", methods=["POST"])
def edit_food(food_id):
    name, error = validate_name(request.form.get("name", ""))
    if error is not None:
        return render_home_with_error(error)

    date_text, error = validate_iso_date(request.form.get("date", ""), "賞味期限")
    if error is not None:
        return render_home_with_error(error)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE foods SET name = ?, date = ? WHERE id = ?",
        (name, date_text, food_id)
    )

    conn.commit()
    conn.close()

    return redirect("/")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
