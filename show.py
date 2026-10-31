import sys

from sqlmodel import Session

from db import Simulation, engine

SPEAKERS = {"assistant": "agent ", "user": "caller"}


def print_simulation(simulation: Simulation) -> None:
    print(
        f"simulation {simulation.id}  version {simulation.agent_version}  {simulation.status}"
    )
    if simulation.error:
        print(f"error: {simulation.error}")
    for item in (simulation.report or {}).get("chat_history", {}).get("items", []):
        match item["type"]:
            case "message" if item["role"] in SPEAKERS:
                print(
                    f"{SPEAKERS[item['role']]}: {' '.join(map(str, item['content']))}"
                )
            case "function_call":
                print(f"  tool  {item['name']}({item['arguments']})")
            case "function_call_output":
                print(f"     -> {item['output']}")
    print(f"recording: {simulation.recording_path}")


if __name__ == "__main__":
    with Session(engine) as session:
        print_simulation(session.get_one(Simulation, sys.argv[1]))
