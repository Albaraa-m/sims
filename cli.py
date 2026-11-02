import argparse
import asyncio
import json
import os
import signal
import socket
from contextlib import nullcontext, suppress
from itertools import groupby
from pathlib import Path

import uvicorn

# Registers the swarm table, so create_tables makes it before the website loads.
import swarms.models  # noqa: F401
from agents.servers import running_agent_servers
from core.config import LOGS_DIR
from core.db import create_tables
from evaluations.crud import latest_evaluation_of_simulation
from evaluations.evaluate import evaluate_simulation
from evaluations.models import Evaluation
from regression_tests.convert import convert_transcript_to_test
from regression_tests.crud import (
    get_source_conversation,
    get_test,
    mark_ready,
)
from regression_tests.models import Test
from regression_tests.run import queue_test_runs
from simulations.crud import get_simulation, list_simulations_of_test
from simulations.models import Simulation, SimulationStatus
from simulations.queue import MAX_CONCURRENT_CALLS, RunRequest, admit_runs
from simulations.transcript import SPEAKERS, chat_items, message_text, spoken_lines
from simulations.worker import run_worker


def print_evaluation(evaluation: Evaluation | None) -> None:
    if evaluation is None:
        print("outcome: not evaluated")
        return
    print(f"outcome: {evaluation.outcome}  ({evaluation.reason})")
    if evaluation.cited_turns:
        print(f"cited turns: {evaluation.cited_turns}")


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
    print_evaluation(latest_evaluation_of_simulation(simulation.id))


def print_test(test: Test) -> None:
    source = (
        get_source_conversation(test.source_conversation_id)
        if test.source_conversation_id
        else None
    )
    print(
        f"test {test.id}  {test.name}  v{test.version}  {test.status}  "
        f"source {source.id if source else '-'}"
    )
    print(f"reported issue: {(source and source.reported_issue) or '-'}")
    for field, value in test.spec.items():
        edited = "" if (test.inferred or {}).get(field) == value else "  (edited)"
        print(f"{field}{edited}: {json.dumps(value, ensure_ascii=False)}")
    simulations = list_simulations_of_test(test.id)
    for version, runs in groupby(simulations, key=lambda s: s.agent_version):
        runs = list(runs)
        statuses = ", ".join(f"{s.id} {s.status}" for s in runs)
        print(f"{version}: {len(runs)} simulations ({statuses})")


def worker_id_of_this_process() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def is_settled(simulation: Simulation) -> bool:
    """Finished for good: given up, cancelled, or done and graded on its last attempt."""
    if simulation.status in (SimulationStatus.FAILED, SimulationStatus.CANCELLED):
        return True
    evaluation = latest_evaluation_of_simulation(simulation.id)
    return (
        simulation.status == SimulationStatus.DONE
        and evaluation is not None
        and evaluation.attempt == simulation.attempt
    )


async def wait_for_runs_to_settle(
    simulation_ids: list[str], with_worker: bool
) -> list[Simulation]:
    """Prints each run's progress; with_worker also runs a worker in this process."""
    stop = asyncio.Event()
    worker = (
        asyncio.create_task(run_worker(worker_id_of_this_process(), stop=stop))
        if with_worker
        else None
    )
    if worker is None:
        print("waiting for a worker: run `sims worker` in another terminal")
    last_seen: dict[str, tuple] = {}
    while True:
        simulations = [
            get_simulation(simulation_id) for simulation_id in simulation_ids
        ]
        for simulation in simulations:
            state = (simulation.status, simulation.attempt)
            if last_seen.get(simulation.id) != state:
                last_seen[simulation.id] = state
                print(
                    f"{simulation.agent_version}  simulation {simulation.id}  "
                    f"attempt {simulation.attempt}  {simulation.status}"
                )
        if all(is_settled(simulation) for simulation in simulations):
            break
        await asyncio.sleep(2)
    if worker:
        stop.set()
        await worker
    return simulations


def print_run_results(simulations: list[Simulation]) -> None:
    for simulation in simulations:
        evaluation = latest_evaluation_of_simulation(simulation.id)
        outcome = evaluation.outcome if evaluation else "-"
        error = f"  ({simulation.error})" if simulation.error else ""
        print(
            f"{simulation.agent_version}  simulation {simulation.id} "
            f"{simulation.status}  {outcome}{error}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(prog="sims")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="Run one simulated call.")
    run.add_argument("--version", choices=["v1", "v2"], default="v2")
    run.add_argument(
        "--start-agents",
        action="store_true",
        help="Start the agent servers and a worker for this call, then stop them.",
    )

    worker = commands.add_parser(
        "worker", help="Place and grade queued calls until stopped."
    )
    worker.add_argument(
        "--max-calls",
        type=int,
        default=MAX_CONCURRENT_CALLS,
        help="Calls this worker places at once.",
    )
    worker.add_argument(
        "--fail-rate",
        type=float,
        default=0.0,
        help="Fail this share of attempts before placing the call, to test retries.",
    )
    worker.add_argument(
        "--start-agents",
        action="store_true",
        help="Also run the agent servers in this process.",
    )

    commands.add_parser("agents", help="Run both agent servers until stopped.")

    web = commands.add_parser("web", help="Serve the web app and its API.")
    web.add_argument("--port", type=int, default=8000)
    web.add_argument(
        "--start-agents",
        action="store_true",
        help="Start the agent servers with the web app and stop them with it.",
    )

    show = commands.add_parser("show", help="Print a stored simulation.")
    show.add_argument("simulation_id")

    evaluate = commands.add_parser(
        "evaluate", help="Grade a simulation again; earlier grades are kept."
    )
    evaluate.add_argument("simulation_id")

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
        help="Start the agent servers and a worker for these runs, then stop them.",
    )

    args = parser.parse_args()
    create_tables()
    match args.command:
        case "run":
            simulations = admit_runs([RunRequest(args.version)])
            with running_agent_servers() if args.start_agents else nullcontext():
                simulations = asyncio.run(
                    wait_for_runs_to_settle(
                        [s.id for s in simulations], with_worker=args.start_agents
                    )
                )
            print_run_results(simulations)
        case "worker":
            # Treat a terminate like Ctrl-C, so the worker stops its calls either way.
            signal.signal(signal.SIGTERM, signal.default_int_handler)
            with running_agent_servers() if args.start_agents else nullcontext():
                print(
                    f"worker {worker_id_of_this_process()} placing up to "
                    f"{args.max_calls} calls; Ctrl-C to stop"
                )
                with suppress(KeyboardInterrupt):
                    asyncio.run(
                        run_worker(
                            worker_id_of_this_process(),
                            args.max_calls,
                            args.fail_rate,
                        )
                    )
        case "agents":
            # Treat a terminate like Ctrl-C, so the agent servers are stopped either way.
            signal.signal(signal.SIGTERM, signal.default_int_handler)
            with running_agent_servers():
                print(f"agent servers running, logs in {LOGS_DIR}; Ctrl-C to stop")
                with suppress(KeyboardInterrupt):
                    signal.pause()
        case "web":
            # Uvicorn re-raises SIGTERM after shutting down; as Ctrl-C it lets the
            # agent servers be stopped instead of killing this process first.
            signal.signal(signal.SIGTERM, signal.default_int_handler)
            with (
                running_agent_servers() if args.start_agents else nullcontext(),
                suppress(KeyboardInterrupt),
            ):
                uvicorn.run("api.app:app", port=args.port)
        case "show":
            print_simulation(get_simulation(args.simulation_id))
        case "evaluate":
            print_evaluation(asyncio.run(evaluate_simulation(args.simulation_id)))
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
            simulations = queue_test_runs(args.test_id, args.versions, args.runs)
            with running_agent_servers() if args.start_agents else nullcontext():
                simulations = asyncio.run(
                    wait_for_runs_to_settle(
                        [s.id for s in simulations], with_worker=args.start_agents
                    )
                )
            print_run_results(simulations)


if __name__ == "__main__":
    main()
