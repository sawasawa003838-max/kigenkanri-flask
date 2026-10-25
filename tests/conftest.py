"""テストから実データ・実APIへのアクセスを防ぎ、設定を毎回復元する。"""

import pytest

import ai_guidance
import app as app_module
import notifications


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    monkeypatch.setitem(app_module.app.config, "DATABASE", str(tmp_path / "test.db"))
    monkeypatch.setitem(app_module.app.config, "TESTING", True)
    for key in ("RESEND_API_KEY", "SENDER_EMAIL", "RECIPIENT_EMAIL"):
        monkeypatch.setitem(app_module.app.config, key, None)
    monkeypatch.setattr(notifications.resend, "api_key", None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def unexpected_external_call(*args, **kwargs):
        raise AssertionError("テストでは外部APIを呼び出さないでください")

    monkeypatch.setattr(notifications.resend.Emails, "send", unexpected_external_call)
    monkeypatch.setattr(ai_guidance, "OpenAI", unexpected_external_call)
