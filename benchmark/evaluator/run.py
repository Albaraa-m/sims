import asyncio
import json
from contextlib import contextmanager

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from benchmark.evaluator.case_files import (
    RESULTS_PATH,
    EvaluatorCase,
    load_evaluator_cases,
)
from benchmark.evaluator.score import write_scores
from core import db, llm
from evaluations.evaluate import evaluate_simulation
from regression_tests.crud import (
    create_test_from_spec,
    save_transcript_as_source_conversation,
)
from regression_tests.models import TestSpec
from simulations.crud import create_simulation, update_simulation
from simulations.models import SimulationStatus

GRADINGS_PER_CASE = 3
# Keeps the judge calls within LiveKit Inference's rate limits.
MAX_CONCURRENT_GRADINGS = 8


def use_in_memory_database() -> None:
    """Benchmark rows never reach sims.db."""
    db.engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(db.engine)


def save_case_as_simulation(case: EvaluatorCase) -> str:
    source = save_transcript_as_source_conversation(f"benchmark case {case.name}")
    test = create_test_from_spec(source, case.name, TestSpec.model_validate(case.spec))
    simulation = create_simulation(case.run["agent_version"], test.id)
    update_simulation(
        simulation.id,
        status=SimulationStatus(case.run["status"]),
        error=case.run["error"],
        report=case.report,
        recording_path="benchmark/audio.ogg" if case.run["has_recording"] else None,
    )
    return simulation.id


@contextmanager
def judge_replying_with_invalid_json():
    async def invalid_reply(_prompt: str, _model: str = "") -> str:
        return "not json"

    real_generate_text = llm.generate_text
    llm.generate_text = invalid_reply
    try:
        yield
    finally:
        llm.generate_text = real_generate_text


async def grade_case(case: EvaluatorCase, limit: asyncio.Semaphore) -> dict:
    simulation_id = save_case_as_simulation(case)
    gradings = []
    for _ in range(GRADINGS_PER_CASE):
        async with limit:
            evaluation = await evaluate_simulation(simulation_id)
        gradings.append(
            {
                "outcome": evaluation.outcome.value,
                "cited_turns": evaluation.cited_turns,
                "reason": evaluation.reason,
            }
        )
    print(f"{case.name}: {[grading['outcome'] for grading in gradings]}")
    return {"case": case.name, "label": case.label, "gradings": gradings}


async def grade_all_cases(cases: list[EvaluatorCase]) -> list[dict]:
    limit = asyncio.Semaphore(MAX_CONCURRENT_GRADINGS)
    # The broken judge is swapped in globally, so its cases run alone, first.
    broken_judge_cases = [case for case in cases if case.run["judge_fails"]]
    with judge_replying_with_invalid_json():
        results = [await grade_case(case, limit) for case in broken_judge_cases]
    results += await asyncio.gather(
        *(grade_case(case, limit) for case in cases if not case.run["judge_fails"])
    )
    return sorted(results, key=lambda result: result["case"])


def main() -> None:
    use_in_memory_database()
    results = asyncio.run(grade_all_cases(load_evaluator_cases()))
    RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n")
    write_scores(results)


if __name__ == "__main__":
    main()
