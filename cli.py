import argparse
import asyncio
import json
import signal
from contextlib import nullcontext, suppress
from itertools import groupby
from pathlib import Path

from agents.servers import running_agent_servers
from core.config import LOGS_DIR
from core.db import create_tables
from regression_tests.convert import convert_transcript_to_test
from regression_tests.crud import (
    get_source_conversation,
    get_test,
    mark_ready,
)
from regression_tests.models import Test
from regression_tests.run import run_test_against_agent_version
from simulations.crud import get_simulation, list_simulations_of_test
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
        print(f"{field}{edited}: {json.dumps(value, ensure_ascii=False)}")
    simulations = list_simulations_of_test(test.id)
    for version, runs in groupby(simulations, key=lambda s: s.agent_version):
        runs = list(runs)
        statuses = ", ".join(f"{s.id} {s.status}" for s in runs)
        print(f"{version}: {len(runs)} simulations ({statuses})")


async def run_test_against_agent_versions(
    test_id: str, agent_versions: list[str], runs: int
) -> list[Simulation]:
    simulations = []
    for agent_version in agent_versions:
        simulations += await run_test_against_agent_version(
            test_id, agent_version, runs
        )
    return simulations


def main() -> None:
    parser = argparse.ArgumentParser(prog="sims")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="Run one simulated call.")
    run.add_argument("--version", choices=["v1", "v2"], default="v2")
    run.add_argument(
        "--start-agents",
        action="store_true",
        help="Start the agent servers for this call and stop them afterwards.",
    )

    commands.add_parser("agents", help="Run both agent servers until stopped.")

    show = commands.add_parser("show", help="Print a stored simulation.")
    show.add_argument("simulation_id")

    export = commands.add_parser(
        "export-transcript", help="Print a simulation's spoken transcript."
    )
    export.add_argument("simulation_id")

    create_test = commands.add_parser(
        "create-test", help="Turn a failed call's transcript into a draft test."
    )
    create_test.add_argument("transcript_file", type=Path)
    create_test.add_argument("--issue", help="What the reviewer says went wrong.")
    create_test.add_argument(
        "--agent-version", choices=["v1", "v2"], help="Version that made the call."
    )

    show_test = commands.add_parser(
        "show-test", help="Print a stored test and its simulations."
    )
    show_test.add_argument("test_id")

    ready = commands.add_parser("mark-ready", help="Mark a test ready to run.")
    ready.add_argument("test_id")

    run_test = commands.add_parser(
        "run-test", help="Run a ready test against agent versions."
    )
    run_test.add_argument("test_id")
    run_test.add_argument(
        "--versions", nargs="+", choices=["v1", "v2"], default=["v1", "v2"]
    )
    run_test.add_argument(
        "--runs", type=int, default=1, help="Simulations per agent version."
    )
    run_test.add_argument(
        "--start-agents",
        action="store_true",
        help="Start the agent servers for this run and stop them afterwards.",
    )

    args = parser.parse_args()
    create_tables()
    match args.command:
        case "run":
            with running_agent_servers() if args.start_agents else nullcontext():
                simulation = asyncio.run(run_simulation(args.version))
            print(f"simulation {simulation.id} {simulation.status}", end="")
            print(f": {simulation.error}" if simulation.error else "")
        case "agents":
            # Treat a terminate like Ctrl-C, so the agent servers are stopped either way.
            signal.signal(signal.SIGTERM, signal.default_int_handler)
            with running_agent_servers():
                print(f"agent servers running, logs in {LOGS_DIR}; Ctrl-C to stop")
                with suppress(KeyboardInterrupt):
                    signal.pause()
        case "show":
            print_simulation(get_simulation(args.simulation_id))
        case "export-transcript":
            print("\n".join(spoken_lines(get_simulation(args.simulation_id))))
        case "create-test":
            outcome = asyncio.run(
                convert_transcript_to_test(
                    args.transcript_file.read_text(), args.issue, args.agent_version
                )
            )
            if outcome.test is None:
                print(f"no violation found: {outcome.reason}")
            else:
                print_test(outcome.test)
        case "show-test":
            print_test(get_test(args.test_id))
        case "mark-ready":
            print(f"test {mark_ready(args.test_id).id} is ready")
        case "run-test":
            with running_agent_servers() if args.start_agents else nullcontext():
                simulations = asyncio.run(
                    run_test_against_agent_versions(
                        args.test_id, args.versions, args.runs
                    )
                )
            for simulation in simulations:
                print(
                    f"{simulation.agent_version}  simulation {simulation.id} {simulation.status}"
                )


if __name__ == "__main__":
    main()
