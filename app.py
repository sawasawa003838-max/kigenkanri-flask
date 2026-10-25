import os
import sys
from datetime import date


import openai
from flask import Flask, redirect, render_template, request, url_for
from resend.exceptions import ResendError

import ai_guidance
import db
import notifications
from expiry import (
    ERROR_DATE_OVERFLOW,
    ERROR_OPEN_DATE_INVALID,
    EXPIRY_STATUS_EXPIRED,
    EXPIRY_STATUS_SOON,
    MAX_SHELF_LIFE_DAYS,
    calculate_expiry_date,
    determine_expiry_status,
    validate_iso_date,
    validate_shelf_life_days,
)


app = Flask(__name__)
app.config["DATABASE"] = "database.db"

app.config["RESEND_API_KEY"] = os.environ.get("RESEND_API_KEY")
app.config["SENDER_EMAIL"] = os.environ.get("SENDER_EMAIL")
app.config["RECIPIENT_EMAIL"] = os.environ.get("RECIPIENT_EMAIL")


ERROR_NAME_REQUIRED = "食品名を入力してください"
LABEL_EXPIRY_DATE = "賞味期限"


def init_db():
    """起動時にアプリ設定のDBを初期化する。"""
    db.init_db(app.config["DATABASE"])


def fetch_foods(reference_date=None):
    """アプリ設定のDBから、状態付きの食品を取得する。"""
    return db.fetch_foods(app.config["DATABASE"], reference_date)


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


@app.route("/", methods=["GET", "POST"])
def home():
    error = None
    message = request.args.get("message")

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

                db.insert_food(app.config["DATABASE"], name, expiry_date_text)
            except ValueError:
                error = ERROR_OPEN_DATE_INVALID
            except OverflowError:
                error = ERROR_DATE_OVERFLOW

    return render_template(
        "index.html",
        foods=fetch_foods(),
        error=error,
        message=message,
        max_shelf_life_days=MAX_SHELF_LIFE_DAYS,
    )


@app.route("/notifications/send", methods=["POST"])
def send_notifications():
    api_key = app.config["RESEND_API_KEY"]
    sender_email = app.config["SENDER_EMAIL"]
    recipient_email = app.config["RECIPIENT_EMAIL"]

    if not api_key or not sender_email or not recipient_email:
        return redirect("/")

    try:
        message = notifications.notify_foods(
            fetch_foods(),
            api_key=api_key,
            sender_email=sender_email,
            recipient_email=recipient_email,
        )
    except ResendError:
        message = "通知メールの送信に失敗しました"

    return redirect(url_for("home", message=message))


@app.cli.command("send-notifications")
def send_notifications_command():
    api_key = app.config["RESEND_API_KEY"]
    sender_email = app.config["SENDER_EMAIL"]
    recipient_email = app.config["RECIPIENT_EMAIL"]

    if not api_key or not sender_email or not recipient_email:
        print("メール設定が不足しています")
        sys.exit(1)

    try:
        message = notifications.notify_foods(
            fetch_foods(),
            api_key=api_key,
            sender_email=sender_email,
            recipient_email=recipient_email,
        )
    except ResendError:
        print("通知メールの送信に失敗しました")
        sys.exit(1)

    print(message)


@app.route("/delete/<int:food_id>", methods=["POST"])
def delete_food(food_id):
    db.delete_food(app.config["DATABASE"], food_id)

    return redirect("/")


@app.route("/edit/<int:food_id>", methods=["POST"])
def edit_food(food_id):
    name, error = validate_name(request.form.get("name", ""))
    if error is not None:
        return render_home_with_error(error)

    date_text, error = validate_iso_date(request.form.get("date", ""), LABEL_EXPIRY_DATE)
    if error is not None:
        return render_home_with_error(error)

    db.update_food(app.config["DATABASE"], food_id, name, date_text)

    return redirect("/")


@app.route("/ai-guidance/<int:food_id>", methods=["POST"])
def show_ai_guidance(food_id):
    row = db.get_food(app.config["DATABASE"], food_id)

    if row is None:
        return render_home_with_error("食品が見つかりません。")

    name, expiry_date = row
    expiry_status = determine_expiry_status(expiry_date)

    if expiry_status not in (
        EXPIRY_STATUS_EXPIRED,
        EXPIRY_STATUS_SOON,
    ):
        return render_home_with_error(
            "AI確認は期限切れ・期限間近の食品で利用できます。"
        )

    try:
        client = ai_guidance.create_openai_client()
        guidance = ai_guidance.generate_food_guidance(
            client=client,
            food_name=name,
            expiry_date=expiry_date,
            expiry_status=expiry_status,
        )
    except (ValueError, openai.APIError):
        return render_home_with_error(
            "AIから確認ポイントを取得できませんでした。"
        )

    return render_template(
        "index.html",
        foods=fetch_foods(),
        error=None,
        ai_guidance_text=guidance,
        max_shelf_life_days=MAX_SHELF_LIFE_DAYS,
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
