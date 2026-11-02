from collections import Counter

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import NoResultFound

from api.routes.runs import build_run_row
from api.schemas import (
    FindPoliciesRequest,
    FoundPolicies,
    GenerateSwarmRequest,
    QueuedRuns,
    RunRow,
    SaveSwarmRequest,
    StartRunsRequest,
    SwarmDetail,
    SwarmRow,
    SwarmRunSummary,
    SwarmTest,
)
from core.db import save
from regression_tests.crud import list_latest_tests, list_test_runs
from simulations.queue import QueueFullError, RunRequest, admit_runs, cancel_runs
from simulations.runner import delete_room
from swarms.crud import (
    get_swarm,
    list_swarm_runs,
    list_swarms,
    next_swarm_run,
    save_swarm_with_tests,
)
from swarms.generate import GenerationError
from swarms.models import Swarm
from swarms.propose import (
    SwarmProposal,
    find_policies_of_agent_version,
    propose_swarm,
)

router = APIRouter(prefix="/api/swarms")


def build_swarm_row(swarm: Swarm) -> SwarmRow:
    return SwarmRow(
        id=swarm.id,
        name=swarm.name,
        agent_version=swarm.agent_version,
        test_count=len(list_latest_tests(swarm.id)),
        created_at=swarm.created_at,
    )


@router.post("/policies")
async def find_policies(request: FindPoliciesRequest) -> FoundPolicies:
    """The policies in an agent version's instructions, for the reviewer to choose from."""
    try:
        policies = await find_policies_of_agent_version(request.agent_version)
    except GenerationError as error:
        raise HTTPException(status_code=502, detail=str(error))
    return FoundPolicies(agent_version=request.agent_version, policies=policies)


@router.post("/generate")
async def generate_swarm_proposal(request: GenerateSwarmRequest) -> SwarmProposal:
    """Returns tests for the reviewer to edit; nothing is saved."""
    try:
        return await propose_swarm(request.agent_version, request.policies)
    except GenerationError as error:
        raise HTTPException(status_code=502, detail=str(error))


@router.post("", status_code=201)
def save_swarm(request: SaveSwarmRequest) -> SwarmRow:
    swarm = save_swarm_with_tests(
        request.name, request.agent_version, request.policies, request.scenarios
    )
    return build_swarm_row(swarm)


@router.get("")
def list_swarm_rows() -> list[SwarmRow]:
    return [build_swarm_row(swarm) for swarm in list_swarms()]


@router.get("/{swarm_id}")
def read_swarm(swarm_id: str) -> SwarmDetail:
    try:
        swarm = get_swarm(swarm_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail=f"swarm {swarm_id} not found")
    # Oldest first: the order the reviewer saw when saving.
    tests = list_latest_tests(swarm.id)[::-1]
    return SwarmDetail(
        **build_swarm_row(swarm).model_dump(),
        policies=swarm.policies,
        tests=[SwarmTest.model_validate(test, from_attributes=True) for test in tests],
    )


def get_swarm_or_404(swarm_id: str) -> Swarm:
    try:
        return get_swarm(swarm_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail=f"swarm {swarm_id} not found")


EARLIER_RUNS_ID = "earlier"


@router.post("/{swarm_id}/runs", status_code=202)
def queue_runs_of_swarm(swarm_id: str, request: StartRunsRequest) -> QueuedRuns:
    """Queues every test against each version as the swarm's next numbered run; a run
    that doesn't fit the queue is refused whole."""
    swarm = get_swarm_or_404(swarm_id)
    swarm_run = next_swarm_run(
        swarm.id, list(request.agent_versions), request.runs_per_version
    )
    requests = [
        RunRequest(agent_version, test.id)
        for test in list_latest_tests(swarm.id)
        for agent_version in request.agent_versions
        for _ in range(request.runs_per_version)
    ]
    try:
        admit_runs(requests, swarm.id, swarm_run.id)
    except QueueFullError as error:
        raise HTTPException(status_code=409, detail=str(error))
    save(swarm_run)
    return QueuedRuns(
        queued=len(requests),
        swarm_run_id=swarm_run.id,
        swarm_run_number=swarm_run.number,
    )


def runs_of_swarm_run(swarm_id: str, swarm_run_id: str | None) -> list[RunRow]:
    rows = [
        build_run_row(simulation, test)
        for simulation, test in list_test_runs(swarm_id=swarm_id)
        if swarm_run_id is None
        or simulation.swarm_run_id == swarm_run_id
        or (swarm_run_id == EARLIER_RUNS_ID and simulation.swarm_run_id is None)
    ]
    return rows


def summarize_swarm_run(
    id: str, number: int, created_at, agent_versions: list[str], runs: list[RunRow]
) -> SwarmRunSummary:
    status_counts = Counter(run.status.value for run in runs)
    outcome_counts = Counter(run.outcome.value for run in runs if run.outcome)
    if status_counts["running"]:
        status = "running"
    elif status_counts["queued"]:
        status = "queued"
    elif status_counts["cancelled"]:
        status = "cancelled"
    else:
        status = "completed"
    return SwarmRunSummary(
        id=id,
        number=number,
        created_at=created_at,
        agent_versions=agent_versions,
        status=status,
        total=len(runs),
        status_counts=dict(status_counts),
        outcome_counts=dict(outcome_counts),
    )


@router.get("/{swarm_id}/swarm-runs")
def list_runs_of_swarm_by_press(swarm_id: str) -> list[SwarmRunSummary]:
    """Each press of Run swarm, newest first, with its progress."""
    get_swarm_or_404(swarm_id)
    calls = runs_of_swarm_run(swarm_id, None)
    run_of_call = {
        simulation.id: simulation.swarm_run_id
        for simulation, _ in list_test_runs(swarm_id=swarm_id)
    }
    summaries = [
        summarize_swarm_run(
            swarm_run.id,
            swarm_run.number,
            swarm_run.created_at,
            swarm_run.agent_versions,
            [call for call in calls if run_of_call[call.id] == swarm_run.id],
        )
        for swarm_run in list_swarm_runs(swarm_id)
    ]
    earlier = [call for call in calls if run_of_call[call.id] is None]
    if earlier:
        summaries.append(
            summarize_swarm_run(
                EARLIER_RUNS_ID,
                0,
                None,
                sorted({call.agent_version for call in earlier}),
                earlier,
            )
        )
    return summaries


@router.get("/{swarm_id}/runs")
def list_runs_of_swarm(swarm_id: str, swarm_run_id: str | None = None) -> list[RunRow]:
    """The swarm's calls; only one run's when swarm_run_id is given."""
    get_swarm_or_404(swarm_id)
    return runs_of_swarm_run(swarm_id, swarm_run_id)


@router.post("/{swarm_id}/swarm-runs/{swarm_run_id}/cancel")
async def cancel_swarm_run(swarm_id: str, swarm_run_id: str) -> None:
    """Stops one run's waiting calls and ends its calls in progress."""
    get_swarm_or_404(swarm_id)
    for room in cancel_runs(swarm_id, swarm_run_id):
        await delete_room(room)
