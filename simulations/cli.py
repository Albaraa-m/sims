import argparse
import asyncio
import json
from pathlib import Path

from core.db import create_tables
from regression_tests.convert import convert_source_conversation_to_test
from regression_tests.crud import (
    get_source_conversation,
    get_test,
    save_transcript_as_source_conversation,
)
from regression_tests.models import Test
from simulations.crud import get_simulation
from simulations.models import Simulation
from simulations.runner import run_simulation
from simulations.transcript import SPEAKERS, chat_items, message_text, spoken_lines


def print_simulation(simulation: Simulation) -> None:
    print(
        f"simulation {simulation.id}  version {simulation.agent_version}  {simulation.status}"
    )
    if simulation.error:
        print(f"error: {simulation.error}")
    for item in chat_items(simulation):
        match item["type"]:
            case "message" if item["role"] in SPEAKERS:
                print(f"{SPEAKERS[item['role']]:<6}: {message_text(item)}")
            case "function_call":
                print(f"  tool  {item['name']}({item['arguments']})")
            case "function_call_output":
                print(f"     -> {item['output']}")
    print(f"recording: {simulation.recording_path}")


def print_test(test: Test) -> None:
    source = get_source_conversation(test.source_conversation_id)
    print(f"test {test.id}  v{test.version}  {test.status}  source {source.id}")
    print(f"reported issue: {source.reported_issue or '-'}")
    for field, value in test.spec.items():
        edited = "" if test.inferred.get(field) == value else "  (edited)"
        print(f"{field}{edited}: {json.dumps(value)}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="simulations")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="Run one simulated call.")
    run.add_argument("--version", choices=["v1", "v2"], default="v2")

    show = commands.add_parser("show", help="Print a stored simulation.")
    show.add_argument("simulation_id")

    export = commands.add_parser(
        "export-transcript", help="Print a simulation's spoken transcript."
    )
    export.add_argument("simulation_id")

    add_transcript = commands.add_parser(
        "add-transcript", help="Save a transcript file as a source conversation."
    )
    add_transcript.add_argument("transcript_file", type=Path)
    add_transcript.add_argument("--issue", help="What the reviewer says went wrong.")
    add_transcript.add_argument("--agent-version", choices=["v1", "v2"])

    convert_to_test = commands.add_parser(
        "convert-to-test", help="Convert a source conversation into a draft test."
    )
    convert_to_test.add_argument("source_conversation_id")

    show_test = commands.add_parser("show-test", help="Print a stored test.")
    show_test.add_argument("test_id")

    args = parser.parse_args()
    create_tables()
    match args.command:
        case "run":
            simulation = asyncio.run(run_simulation(args.version))
            print(f"simulation {simulation.id} {simulation.status}", end="")
            print(f": {simulation.error}" if simulation.error else "")
        case "show":
            print_simulation(get_simulation(args.simulation_id))
        case "export-transcript":
            print("\n".join(spoken_lines(get_simulation(args.simulation_id))))
        case "add-transcript":
            source_conversation = save_transcript_as_source_conversation(
                args.transcript_file.read_text(), args.issue, args.agent_version
            )
            print(f"source conversation {source_conversation.id}")
        case "convert-to-test":
            outcome = asyncio.run(
                convert_source_conversation_to_test(args.source_conversation_id)
            )
            if outcome.test is None:
                print(f"no violation found: {outcome.reason}")
            else:
                print_test(outcome.test)
        case "show-test":
            print_test(get_test(args.test_id))


if __name__ == "__main__":
    main()
