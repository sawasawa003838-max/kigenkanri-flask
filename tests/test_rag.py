from pathlib import Path

from ai_guidance import build_food_guidance_prompt, generate_food_guidance
from rag import find_food_reference, load_knowledge

def test_find_food_reference_returns_matching_reference():
    knowledge = {
        "卵": {
            "source": "テスト用参考情報",
            "points": [
                "冷蔵状態を確認する",
                "殻の状態を確認する",
            ],
        },
        "牛乳": {
            "source": "テスト用参考情報",
            "points": [
                "開封済みか確認する",
            ],
        },
    }

    result = find_food_reference(
        food_name="卵",
        knowledge=knowledge,
    )

    assert result == knowledge["卵"]


def test_find_food_reference_returns_none_when_not_found():
    knowledge = {
        "卵": {
            "source": "テスト用参考情報",
            "points": [
                "冷蔵状態を確認する",
            ],
        },
    }

    result = find_food_reference(
        food_name="りんご",
        knowledge=knowledge,
    )

    assert result is None


def test_load_knowledge_reads_json_file(tmp_path):
    knowledge_file = tmp_path / "food_guidance.json"

    knowledge_file.write_text(
        """
        {
            "卵": {
                "source": "テスト用参考情報",
                "points": [
                    "冷蔵状態を確認する"
                ]
            }
        }
        """,
        encoding="utf-8",
    )

    result = load_knowledge(knowledge_file)

    assert result["卵"]["source"] == "テスト用参考情報"
    assert result["卵"]["points"] == ["冷蔵状態を確認する"]


def test_real_knowledge_file_contains_egg_reference():
    knowledge_file = Path("knowledge/food_guidance.json")

    knowledge = load_knowledge(knowledge_file)
    reference = find_food_reference(
        food_name="卵",
        knowledge=knowledge,
    )

    assert reference is not None
    assert "source" in reference
    assert "source_url" in reference
    assert "points" in reference
    assert len(reference["points"]) > 0
    assert reference["source_url"].startswith("https://")


def test_real_egg_reference_can_be_added_to_ai_prompt():
    knowledge_file = Path("knowledge/food_guidance.json")

    knowledge = load_knowledge(knowledge_file)
    reference = find_food_reference(
        food_name="卵",
        knowledge=knowledge,
    )

    prompt = build_food_guidance_prompt(
        food_name="卵",
        expiry_date="2026-08-09",
        expiry_status="期限間近",
        reference=reference,
    )

    assert reference["source"] in prompt

    for point in reference["points"]:
        assert point in prompt


def test_unknown_food_can_build_prompt_without_reference():
    knowledge_file = Path("knowledge/food_guidance.json")

    knowledge = load_knowledge(knowledge_file)
    reference = find_food_reference(
        food_name="りんご",
        knowledge=knowledge,
    )

    prompt = build_food_guidance_prompt(
        food_name="りんご",
        expiry_date="2026-08-09",
        expiry_status="期限間近",
        reference=reference,
    )

    assert reference is None
    assert "食品名: りんご" in prompt
    assert "参考情報:" not in prompt


class RecordingResponses:
    def __init__(self):
        self.input = None

    def create(self, model: str, input: str):
        self.input = input

        class FakeResponse:
            output_text = "確認ポイントです。"

        return FakeResponse()


class RecordingClient:
    def __init__(self):
        self.responses = RecordingResponses()


def test_real_knowledge_reaches_ai_request():
    knowledge_file = Path("knowledge/food_guidance.json")

    knowledge = load_knowledge(knowledge_file)
    reference = find_food_reference(
        food_name="卵",
        knowledge=knowledge,
    )

    client = RecordingClient()

    generate_food_guidance(
        client=client,
        food_name="卵",
        expiry_date="2026-08-09",
        expiry_status="期限間近",
        reference=reference,
    )

    assert reference["source"] in client.responses.input

    for point in reference["points"]:
        assert point in client.responses.input
