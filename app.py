from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import date, timedelta

app = Flask(__name__)


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


@app.route("/", methods=["GET", "POST"])
def home():
    error = None

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        open_date_text = request.form.get("open_date", "")
        days_text = request.form.get("days", "")

        if name == "":
            error = "食品名を入力してください"
        elif not days_text.isdigit():
            error = "保存日数は1以上の数字で入力してください"
        else:
            days = int(days_text)

            if days < 1:
                error = "保存日数は1以上で入力してください"
            else:
                try:
                    open_date_obj = date.fromisoformat(open_date_text)
                    expiry_date = calculate_expiry_date(open_date_obj, days)
                    expiry_date_text = expiry_date.isoformat()

                    cursor.execute(
                        "INSERT INTO foods (name, date) VALUES (?, ?)",
                        (name, expiry_date_text)
                    )
                    conn.commit()
                except ValueError:
                    error = "開封日を正しい形式で入力してください"

    cursor.execute("SELECT * FROM foods")
    foods = cursor.fetchall()

    conn.close()

    return render_template("index.html", foods=foods, error=error)


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
    name = request.form["name"]
    date_text = request.form["date"]

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