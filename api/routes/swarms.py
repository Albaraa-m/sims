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
    SwarmTest,
)
from regression_tests.crud import list_latest_tests, list_test_runs
from simulations.queue import QueueFullError, RunRequest, admit_runs, cancel_runs
from simulations.runner import delete_room
from swarms.crud import get_swarm, list_swarms, save_swarm_with_tests
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


@router.post("/{swarm_id}/runs", status_code=202)
def queue_runs_of_swarm(swarm_id: str, request: StartRunsRequest) -> QueuedRuns:
    """Queues every test against each version; a start that doesn't fit is refused whole."""
    swarm = get_swarm_or_404(swarm_id)
    requests = [
        RunRequest(agent_version, test.id)
        for test in list_latest_tests(swarm.id)
        for agent_version in request.agent_versions
        for _ in range(request.runs_per_version)
    ]
    try:
        admit_runs(requests, swarm.id)
    except QueueFullError as error:
        raise HTTPException(status_code=409, detail=str(error))
    return QueuedRuns(queued=len(requests))


@router.get("/{swarm_id}/runs")
def list_runs_of_swarm(swarm_id: str) -> list[RunRow]:
    get_swarm_or_404(swarm_id)
    return [
        build_run_row(simulation, test)
        for simulation, test in list_test_runs(swarm_id=swarm_id)
    ]


@router.post("/{swarm_id}/cancel")
async def cancel_runs_of_swarm(swarm_id: str) -> None:
    """Stops the swarm's waiting runs and ends its calls in progress."""
    get_swarm_or_404(swarm_id)
    for room in cancel_runs(swarm_id):
        await delete_room(room)
