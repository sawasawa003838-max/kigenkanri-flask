import sqlite3
from datetime import date, timedelta

from flask import Flask, render_template, request, redirect

app = Flask(__name__)
app.config["DATABASE"] = "database.db"

MAX_SHELF_LIFE_DAYS = 3650
ERROR_NAME_REQUIRED = "\u98df\u54c1\u540d\u3092\u5165\u529b\u3057\u3066\u304f\u3060\u3055\u3044"
ERROR_DATE_SUFFIX = "\u3092\u6b63\u3057\u3044\u5f62\u5f0f\u3067\u5165\u529b\u3057\u3066\u304f\u3060\u3055\u3044"
ERROR_OPEN_DATE_INVALID = "\u958b\u5c01\u65e5\u3092\u6b63\u3057\u3044\u5f62\u5f0f\u3067\u5165\u529b\u3057\u3066\u304f\u3060\u3055\u3044"
ERROR_DATE_OVERFLOW = "\u958b\u5c01\u65e5\u3068\u4fdd\u5b58\u65e5\u6570\u306e\u7d44\u307f\u5408\u308f\u305b\u304c\u5927\u304d\u3059\u304e\u307e\u3059"
ERROR_SHELF_LIFE_DAYS = (
    "\u4fdd\u5b58\u65e5\u6570\u306f1\u65e5\u4ee5\u4e0a"
    f"{MAX_SHELF_LIFE_DAYS}"
    "\u65e5\u4ee5\u4e0b\u3067\u5165\u529b\u3057\u3066\u304f\u3060\u3055\u3044"
)
LABEL_EXPIRY_DATE = "\u8cde\u5473\u671f\u9650"


def get_db_connection():
    return sqlite3.connect(app.config["DATABASE"])


def init_db():
    conn = get_db_connection()
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
    conn = get_db_connection()
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
        max_shelf_life_days=MAX_SHELF_LIFE_DAYS,
    ), 400


def validate_name(name):
    name = name.strip()
    if name == "":
        return None, ERROR_NAME_REQUIRED
    return name, None


def validate_iso_date(date_text, label):
    try:
        date.fromisoformat(date_text)
    except ValueError:
        return None, f"{label}{ERROR_DATE_SUFFIX}"
    return date_text, None


def validate_shelf_life_days(days_text):
    if not days_text.isdigit():
        return None, ERROR_SHELF_LIFE_DAYS

    try:
        days = int(days_text)
    except ValueError:
        return None, ERROR_SHELF_LIFE_DAYS
    if days < 1 or days > MAX_SHELF_LIFE_DAYS:
        return None, ERROR_SHELF_LIFE_DAYS

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

                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO foods (name, date) VALUES (?, ?)",
                    (name, expiry_date_text),
                )
                conn.commit()
                conn.close()
            except ValueError:
                error = ERROR_OPEN_DATE_INVALID
            except OverflowError:
                error = ERROR_DATE_OVERFLOW

    return render_template(
        "index.html",
        foods=fetch_foods(),
        error=error,
        max_shelf_life_days=MAX_SHELF_LIFE_DAYS,
    )


@app.route("/delete/<int:food_id>", methods=["POST"])
def delete_food(food_id):
    conn = get_db_connection()
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

    date_text, error = validate_iso_date(request.form.get("date", ""), LABEL_EXPIRY_DATE)
    if error is not None:
        return render_home_with_error(error)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE foods SET name = ?, date = ? WHERE id = ?",
        (name, date_text, food_id),
    )

    conn.commit()
    conn.close()

    return redirect("/")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
