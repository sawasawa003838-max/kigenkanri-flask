import json


def find_food_reference(
    food_name: str,
    knowledge: dict,
):
    return knowledge.get(food_name)


def load_knowledge(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)
