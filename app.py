from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime, timedelta

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

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form["name"]
        open_date = request.form["open_date"]
        days = int(request.form["days"])

        open_date_obj = datetime.strptime(open_date, "%Y-%m-%d")
        expiry_date = open_date_obj + timedelta(days=days)
        date = expiry_date.strftime("%Y-%m-%d")

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO foods (name, date) VALUES (?, ?)",
            (name, date)
        )

        conn.commit()
        conn.close()

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM foods")
    foods = cursor.fetchall()

    conn.close()

    return render_template("index.html", foods=foods)

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
    date = request.form["date"]

    conn = sqlite3.connect("database.db")
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
    