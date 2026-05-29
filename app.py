import sqlite3
from datetime import date as datetime_date

from flask import Flask, render_template, request, redirect

app = Flask(__name__)
app.config["DATABASE"] = "database.db"


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


def is_valid_food_input(name, expiration_date):
    if not name.strip():
        return False

    try:
        datetime_date.fromisoformat(expiration_date)
    except ValueError:
        return False

    return True


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        date = request.form.get("date", "").strip()

        if is_valid_food_input(name, date):
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO foods (name, date) VALUES (?, ?)",
                (name, date)
            )

            conn.commit()
            conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM foods")
    foods = cursor.fetchall()

    conn.close()

    return render_template("index.html", foods=foods)

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
    name = request.form.get("name", "").strip()
    date = request.form.get("date", "").strip()

    if not is_valid_food_input(name, date):
        return redirect("/")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE foods SET name = ?, date = ? WHERE id = ?",
        (name, date, food_id)
    )

    conn.commit()
    conn.close()

    return redirect("/")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
