"""通知対象の選定、メール本文の作成、Resendによる送信。"""

from collections.abc import Iterable

import resend

from db import Food
from expiry import EXPIRY_STATUS_EXPIRED, EXPIRY_STATUS_SOON


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


def notify_foods(foods, *, api_key, sender_email, recipient_email):
    """HTTPとCLIで共通の通知手順。送信失敗は呼び出し元に伝える。"""
    targets = extract_notification_targets(foods)
    if not targets:
        return "通知対象の食品はありません"

    resend.api_key = api_key
    send_notification_email(
        targets,
        sender_email=sender_email,
        recipient_email=recipient_email,
    )
    return "通知メールを送信しました"
