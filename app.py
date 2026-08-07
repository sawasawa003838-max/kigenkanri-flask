import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

import resend
from flask import Flask, render_template, request, redirect

app = Flask(__name__)
app.config["DATABASE"] = "database.db"

MAX_SHELF_LIFE_DAYS = 3650
EXPIRING_SOON_DAYS = 3

EXPIRY_STATUS_EXPIRED = "期限切れ"
EXPIRY_STATUS_SOON = "期限間近"
EXPIRY_STATUS_NORMAL = "通常"
EXPIRY_STATUS_INVALID = "日付エラー"

ERROR_NAME_REQUIRED = "食品名を入力してください"
ERROR_DATE_SUFFIX = "を正しい形式で入力してください"
ERROR_OPEN_DATE_INVALID = "開封日を正しい形式で入力してください"
ERROR_DATE_OVERFLOW = "開封日と保存日数の組み合わせが大きすぎます"
ERROR_SHELF_LIFE_DAYS = (
    "保存日数は1日以上"
    f"{MAX_SHELF_LIFE_DAYS}"
    "日以下で入力してください"
)
LABEL_EXPIRY_DATE = "賞味期限"


@dataclass
class Food:
    id: int
    name: str
    expiry_date: str
    expiry_status: str


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


def determine_expiry_status(expiry_date_text, today=None):
    if today is None:
        today = date.today()

    try:
        expiry_date = date.fromisoformat(expiry_date_text)
    except (TypeError, ValueError):
        return EXPIRY_STATUS_INVALID

    days_until_expiry = (expiry_date - today).days

    if days_until_expiry < 0:
        return EXPIRY_STATUS_EXPIRED

    if days_until_expiry <= EXPIRING_SOON_DAYS:
        return EXPIRY_STATUS_SOON

    return EXPIRY_STATUS_NORMAL


def build_notification_email(targets):
    if not targets:
        return None

    subject = "【賞味期限管理】確認が必要な食品があります"
    lines = ["期限の確認が必要な食品をお知らせします。", ""]

    for food in targets:
        lines.append(
            f"・{food.name}"
            f"（期限：{food.expiry_date}、"
            f"状態：{food.expiry_status}）"
        )

    lines.extend(["", "食品の状態を確認してください。"])
    body = "\n".join(lines)

    return subject, body


def send_notification_email(
    targets: Iterable[Food],
    sender_email: str,
    recipient_email: str,
):
    email_content = build_notification_email(targets)

    if email_content is None:
        return None

    subject, body = email_content

    params: resend.Emails.SendParams = {
        "from": sender_email,
        "to": [recipient_email],
        "subject": subject,
        "text": body,
    }

    return resend.Emails.send(params)


def extract_notification_targets(
    foods: Iterable[Food],
) -> list[Food]:
    targets = []

    for food in foods:
        if food.expiry_status in (
            EXPIRY_STATUS_EXPIRED,
            EXPIRY_STATUS_SOON,
        ):
            targets.append(food)

    return targets


def fetch_foods(reference_date=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, date FROM foods"
    )

    food_rows = cursor.fetchall()
    conn.close()

    foods = []

    for food_id, name, expiry_date in food_rows:
        status = determine_expiry_status(
            expiry_date,
            reference_date,
        )

        foods.append(
            Food(
                id=food_id,
                name=name,
                expiry_date=expiry_date,
                expiry_status=status,
            )
        )

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


@app.route("/notifications/send", methods=["POST"])
def send_notifications():
    foods = fetch_foods()
    targets = extract_notification_targets(foods)

    send_notification_email(
        targets,
        sender_email=app.config["SENDER_EMAIL"],
        recipient_email=app.config["RECIPIENT_EMAIL"],
    )

    return redirect("/")


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