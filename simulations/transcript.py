from simulations.models import Simulation

SPEAKERS = {"assistant": "Agent", "user": "Caller"}


def chat_items(simulation: Simulation) -> list[dict]:
    return (simulation.report or {}).get("chat_history", {}).get("items", [])


def message_text(item: dict) -> str:
    return " ".join(map(str, item["content"]))


def spoken_lines(simulation: Simulation) -> list[str]:
    return [
        f"{SPEAKERS[item['role']]}: {message_text(item)}"
        for item in chat_items(simulation)
        if item["type"] == "message" and item["role"] in SPEAKERS
    ]
