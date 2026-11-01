import argparse
import asyncio

from db import create_tables
from simulations.crud import get_simulation
from simulations.models import Simulation
from simulations.runner import run_simulation

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


def main() -> None:
    parser = argparse.ArgumentParser(prog="simulations")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Run one simulated call.")
    run.add_argument("--version", choices=["v1", "v2"], default="v2")
    show = commands.add_parser("show", help="Print a stored simulation.")
    show.add_argument("simulation_id")
    args = parser.parse_args()

    create_tables()
    if args.command == "run":
        simulation = asyncio.run(run_simulation(args.version))
        print(f"simulation {simulation.id} {simulation.status}", end="")
        print(f": {simulation.error}" if simulation.error else "")
    else:
        print_simulation(get_simulation(args.simulation_id))


if __name__ == "__main__":
    main()
