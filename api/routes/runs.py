from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.exc import NoResultFound

from api.schemas import EvaluationDetail, RunDetail, RunRow
from evaluations.crud import (
    latest_evaluation_of_simulation,
    list_evaluations_of_simulation,
)
from evaluations.evaluate import evaluate_simulation
from regression_tests.crud import get_test
from regression_tests.models import Test
from simulations.conversation import conversation_of_simulation
from simulations.crud import get_simulation
from simulations.models import Simulation

router = APIRouter(prefix="/api/runs")


def get_simulation_or_404(run_id: str) -> Simulation:
    try:
        return get_simulation(run_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail=f"run {run_id} not found")


def build_run_row(simulation: Simulation, test: Test) -> RunRow:
    evaluation = latest_evaluation_of_simulation(simulation.id)
    return RunRow(
        id=simulation.id,
        test_id=test.id,
        test_name=test.name,
        test_version=test.version,
        agent_version=simulation.agent_version,
        status=simulation.status,
        started_at=simulation.started_at,
        ended_at=simulation.ended_at,
        outcome=evaluation and evaluation.outcome,
    )


@router.get("/{run_id}")
def read_run(run_id: str) -> RunDetail:
    simulation = get_simulation_or_404(run_id)
    test = get_test(simulation.test_id) if simulation.test_id else None
    return RunDetail(
        id=simulation.id,
        agent_version=simulation.agent_version,
        status=simulation.status,
        started_at=simulation.started_at,
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
