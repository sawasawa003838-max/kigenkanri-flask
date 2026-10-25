import db
import expiry
import notifications


def test_notify_foods_uses_current_api_key_and_filters_targets(monkeypatch):
    expired = db.Food(1, "milk", "2026-07-01", expiry.EXPIRY_STATUS_EXPIRED)
    normal = db.Food(2, "rice", "2026-07-06", expiry.EXPIRY_STATUS_NORMAL)
    sent = []

    def fake_send(params):
        assert notifications.resend.api_key == "current-test-key"
        sent.append(params)
        return {"id": "test-id"}

    monkeypatch.setattr(notifications.resend.Emails, "send", fake_send)
    message = notifications.notify_foods(
        [normal, expired],
        api_key="current-test-key",
        sender_email="sender@example.com",
        recipient_email="recipient@example.com",
    )

    assert message == "通知メールを送信しました"
    assert len(sent) == 1
    assert "milk" in sent[0]["text"]
    assert "rice" not in sent[0]["text"]


def test_notify_foods_does_not_send_without_targets():
    # conftestの外部通信ガードが呼ばれれば、このテストは失敗する。
    message = notifications.notify_foods(
        [],
        api_key="test-key",
        sender_email="sender@example.com",
        recipient_email="recipient@example.com",
    )
    assert message == "通知対象の食品はありません"


def test_build_notification_email_includes_expired_food():
    expired_food = db.Food(
        id=1,
        name="milk",
        expiry_date="2026-07-19",
        expiry_status=expiry.EXPIRY_STATUS_EXPIRED,
    )

    subject, body = notifications.build_notification_email(
        [expired_food]
    )

    assert subject == "【賞味期限管理】確認が必要な食品があります"
    assert "milk" in body
    assert "2026-07-19" in body
    assert expiry.EXPIRY_STATUS_EXPIRED in body


def test_build_notification_email_includes_expiring_soon_food():
    food = db.Food(
        id=2,
        name="eggs",
        expiry_date="2026-07-22",
        expiry_status=expiry.EXPIRY_STATUS_SOON,
    )

    subject, body = notifications.build_notification_email([food])

    assert "eggs" in body
    assert "2026-07-22" in body
    assert expiry.EXPIRY_STATUS_SOON in body


def test_build_notification_email_keeps_food_order():
    milk = db.Food(
        id=1,
        name="milk",
        expiry_date="2026-07-19",
        expiry_status=expiry.EXPIRY_STATUS_EXPIRED,
    )
    eggs = db.Food(
        id=2,
        name="eggs",
        expiry_date="2026-07-22",
        expiry_status=expiry.EXPIRY_STATUS_SOON,
    )

    subject, body = notifications.build_notification_email(
        [milk, eggs]
    )

    assert body.index("milk") < body.index("eggs")


def test_build_notification_email_returns_none_for_empty_targets():
    result = notifications.build_notification_email([])

    assert result is None


def test_build_notification_email_creates_email_for_expired_food():
    expired_food = db.Food(
        id=1,
        name="牛乳",
        expiry_date="2026-07-19",
        expiry_status=expiry.EXPIRY_STATUS_EXPIRED,
    )

    subject, body = notifications.build_notification_email(
        [expired_food]
    )

    assert subject == "【賞味期限管理】確認が必要な食品があります"
    assert body == (
        "期限の確認が必要な食品をお知らせします。\n"
        "\n"
        "・牛乳（期限：2026-07-19、状態：期限切れ）\n"
        "\n"
        "食品の状態を確認してください。"
    )


def test_build_notification_email_includes_multiple_targets_in_order():
    expired_food = db.Food(
        id=1,
        name="牛乳",
        expiry_date="2026-07-19",
        expiry_status=expiry.EXPIRY_STATUS_EXPIRED,
    )
    expiring_soon_food = db.Food(
        id=2,
        name="卵",
        expiry_date="2026-07-22",
        expiry_status=expiry.EXPIRY_STATUS_SOON,
    )

    subject, body = notifications.build_notification_email(
        [
            expired_food,
            expiring_soon_food,
        ]
    )

    assert subject == "【賞味期限管理】確認が必要な食品があります"
    assert "・牛乳（期限：2026-07-19、状態：期限切れ）" in body
    assert "・卵（期限：2026-07-22、状態：期限間近）" in body
    assert body.index("牛乳") < body.index("卵")


def test_send_notification_email_sends_expected_email(monkeypatch):
    expired_food = db.Food(
        id=1,
        name="牛乳",
        expiry_date="2026-07-19",
        expiry_status=expiry.EXPIRY_STATUS_EXPIRED,
    )

    sent_params = {}

    def fake_send(params):
        sent_params.update(params)
        return {"id": "test-email-id"}

    monkeypatch.setattr(
        notifications.resend.Emails,
        "send",
        fake_send,
    )

    result = notifications.send_notification_email(
        [expired_food],
        sender_email="sender@example.com",
        recipient_email="store@example.com",
    )

    assert result == {"id": "test-email-id"}
    assert sent_params["from"] == "sender@example.com"
    assert sent_params["to"] == ["store@example.com"]
    assert sent_params["subject"] == (
        "【賞味期限管理】確認が必要な食品があります"
    )
    assert "牛乳" in sent_params["text"]


def test_send_notification_email_does_not_send_when_targets_are_empty(
    monkeypatch,
):
    send_was_called = False

    def fake_send(params):
        nonlocal send_was_called
        send_was_called = True
        return {"id": "test-email-id"}

    monkeypatch.setattr(
        notifications.resend.Emails,
        "send",
        fake_send,
    )

    result = notifications.send_notification_email(
        [],
        sender_email="sender@example.com",
        recipient_email="store@example.com",
    )

    assert result is None
    assert send_was_called is False


def test_extract_notification_targets_includes_expired_food():
    expired_food = db.Food(
        id=1,
        name="milk",
        expiry_date="2026-07-01",
        expiry_status=expiry.EXPIRY_STATUS_EXPIRED,
    )

    targets = notifications.extract_notification_targets(
        [expired_food]
    )

    assert targets == [expired_food]


def test_extract_notification_targets_includes_expiring_soon_food():
    expiring_soon_food = db.Food(
        id=2,
        name="eggs",
        expiry_date="2026-07-22",
        expiry_status=expiry.EXPIRY_STATUS_SOON,
    )

    targets = notifications.extract_notification_targets(
        [expiring_soon_food]
    )

    assert targets == [expiring_soon_food]


def test_extract_notification_targets_excludes_normal_food():
    normal_food = db.Food(
        id=3,
        name="rice",
        expiry_date="2026-08-01",
        expiry_status=expiry.EXPIRY_STATUS_NORMAL,
    )

    targets = notifications.extract_notification_targets(
        [normal_food]
    )

    assert targets == []


def test_extract_notification_targets_excludes_invalid_date_food():
    invalid_food = db.Food(
        id=4,
        name="invalid-food",
        expiry_date="not-a-date",
        expiry_status=expiry.EXPIRY_STATUS_INVALID,
    )

    targets = notifications.extract_notification_targets(
        [invalid_food]
    )

    assert targets == []


def test_extract_notification_targets_returns_multiple_targets_in_order():
    expired_food = db.Food(
        id=1,
        name="milk",
        expiry_date="2026-07-19",
        expiry_status=expiry.EXPIRY_STATUS_EXPIRED,
    )
    normal_food = db.Food(
        id=2,
        name="rice",
        expiry_date="2026-08-01",
        expiry_status=expiry.EXPIRY_STATUS_NORMAL,
    )
    expiring_soon_food = db.Food(
        id=3,
        name="eggs",
        expiry_date="2026-07-22",
        expiry_status=expiry.EXPIRY_STATUS_SOON,
    )
    invalid_food = db.Food(
        id=4,
        name="invalid-food",
        expiry_date="not-a-date",
        expiry_status=expiry.EXPIRY_STATUS_INVALID,
    )

    targets = notifications.extract_notification_targets(
        [
            expired_food,
            normal_food,
            expiring_soon_food,
            invalid_food,
        ]
    )

    assert targets == [
        expired_food,
        expiring_soon_food,
    ]


def test_extract_notification_targets_returns_empty_list_for_empty_input():
    targets = notifications.extract_notification_targets([])

    assert targets == []
