"""期限の計算・状態判定と日付入力の検証。FlaskやDBには依存しない。"""

from datetime import date, timedelta


MAX_SHELF_LIFE_DAYS = 3650
EXPIRING_SOON_DAYS = 3
EXPIRY_STATUS_EXPIRED = "期限切れ"
EXPIRY_STATUS_SOON = "期限間近"
EXPIRY_STATUS_NORMAL = "通常"
EXPIRY_STATUS_INVALID = "日付エラー"
ERROR_DATE_SUFFIX = "を正しい形式で入力してください"
ERROR_OPEN_DATE_INVALID = "開封日を正しい形式で入力してください"
ERROR_DATE_OVERFLOW = "開封日と保存日数の組み合わせが大きすぎます"
ERROR_SHELF_LIFE_DAYS = (
    "保存日数は1日以上"
    f"{MAX_SHELF_LIFE_DAYS}"
    "日以下で入力してください"
)


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
