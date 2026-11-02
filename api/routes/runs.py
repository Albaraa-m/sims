from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.exc import NoResultFound

from api.schemas import AttemptLogEntry, EvaluationDetail, RunDetail, RunRow
from evaluations.crud import (
    current_evaluation_of_simulation,
    list_evaluations_of_simulation,
)
from evaluations.evaluate import evaluate_simulation
from evaluations.execution import find_execution_failure
from evaluations.models import Outcome
from regression_tests.crud import get_test, list_test_runs
from regression_tests.models import Test
from simulations.conversation import conversation_of_simulation
from simulations.crud import get_simulation
from simulations.models import Simulation, SimulationStatus

router = APIRouter(prefix="/api/runs")


def get_simulation_or_404(run_id: str) -> Simulation:
    try:
        return get_simulation(run_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail=f"run {run_id} not found")


def build_run_row(simulation: Simulation, test: Test) -> RunRow:
    evaluation = current_evaluation_of_simulation(simulation)
    # A run that gave up has no grade, but still has a reason it couldn't run.
    could_not_run = simulation.status == SimulationStatus.FAILED or (
        evaluation is not None and evaluation.outcome == Outcome.EXECUTION_FAILED
    )
    execution_failure = find_execution_failure(simulation) if could_not_run else None
    return RunRow(
        id=simulation.id,
        test_id=test.id,
        test_lineage_id=test.lineage_id,
        test_name=test.name,
        test_version=test.version,
        agent_version=simulation.agent_version,
        status=simulation.status,
        attempt=simulation.attempt,
        attempts=[
            AttemptLogEntry.model_validate(entry) for entry in simulation.attempts
        ],
        started_at=simulation.started_at,
        call_started_at=simulation.call_started_at,
        ended_at=simulation.ended_at,
        outcome=evaluation and evaluation.outcome,
        reason=evaluation and evaluation.reason,
        judge_model=evaluation and evaluation.judge_model,
        judge_prompt_version=evaluation and evaluation.judge_prompt_version,
        execution_failure_kind=execution_failure and execution_failure.kind,
    )


@router.get("")
def list_runs(
    test_id: str | None = None,
    agent_version: Literal["v1", "v2"] | None = None,
    outcome: Outcome | None = None,
) -> list[RunRow]:
    """Runs of tests, newest first; test_id matches every version of that test."""
    lineage_id = get_test_or_404(test_id).lineage_id if test_id else None
    rows = [
        build_run_row(simulation, test)
        for simulation, test in list_test_runs(lineage_id, agent_version)
    ]
    return [row for row in rows if outcome is None or has_outcome(row, outcome)]


def has_outcome(row: RunRow, outcome: Outcome) -> bool:
    """A run that couldn't run has no grade, but counts as an execution failure."""
    if outcome == Outcome.EXECUTION_FAILED and row.status == SimulationStatus.FAILED:
        return True
    return row.outcome == outcome


def get_test_or_404(test_id: str) -> Test:
    try:
        return get_test(test_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail=f"test {test_id} not found")


@router.get("/{run_id}")
def read_run(run_id: str) -> RunDetail:
    simulation = get_simulation_or_404(run_id)
    test = get_test(simulation.test_id) if simulation.test_id else None
    return RunDetail(
        id=simulation.id,
        agent_version=simulation.agent_version,
        status=simulation.status,
        attempt=simulation.attempt,
        max_attempts=simulation.max_attempts,
        attempts=[
            AttemptLogEntry.model_validate(entry) for entry in simulation.attempts
        ],
        started_at=simulation.started_at,
        call_started_at=simulation.call_started_at,
        ended_at=simulation.ended_at,
        error=simulation.error,
        test_id=test and test.id,
        test_name=test and test.name,
        test_version=test and test.version,
        conversation=conversation_of_simulation(simulation),
        has_recording=simulation.recording_path is not None,
        evaluations=[
            EvaluationDetail.model_validate(evaluation, from_attributes=True)
            for evaluation in list_evaluations_of_simulation(simulation.id)
        ],
    )


@router.post("/{run_id}/evaluate")
async def regrade_run(run_id: str) -> EvaluationDetail:
    """Adds a new evaluation; earlier ones stay in the run's history."""
    get_simulation_or_404(run_id)
    evaluation = await evaluate_simulation(run_id)
    return EvaluationDetail.model_validate(evaluation, from_attributes=True)


@router.get("/{run_id}/recording")
def read_run_recording(run_id: str) -> FileResponse:
    recording_path = get_simulation_or_404(run_id).recording_path
    if recording_path is None:
        raise HTTPException(status_code=404, detail=f"run {run_id} has no recording")
    return FileResponse(recording_path, media_type="audio/ogg")
