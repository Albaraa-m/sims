import asyncio

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import NoResultFound

from api.schemas import (
    CreateTestRequest,
    EditTestRequest,
    InferTestRequest,
    InferTestResponse,
    RunRow,
    StartRunsRequest,
    TestDetail,
    TestRow,
)
from regression_tests.convert import infer_test_spec_from_transcript
from regression_tests.crud import (
    create_test_from_transcript,
    edit_test,
    get_test,
    list_latest_tests,
    list_runs_of_every_test_version,
    list_test_versions,
    mark_ready,
)
from regression_tests.models import Test, TestStatus
from regression_tests.run import run_test_against_agent_version

router = APIRouter(prefix="/api/tests")

# The event loop keeps only weak references to tasks; these must outlive the request.
running_tasks: set[asyncio.Task] = set()


@router.get("")
def list_tests() -> list[TestRow]:
    return [
        TestRow.model_validate(test, from_attributes=True)
        for test in list_latest_tests()
    ]


def get_test_or_404(test_id: str) -> Test:
    try:
        return get_test(test_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail=f"test {test_id} not found")


@router.get("/{test_id}")
def read_test(test_id: str) -> TestDetail:
    return TestDetail.model_validate(get_test_or_404(test_id), from_attributes=True)


@router.get("/{test_id}/versions")
def list_versions_of_test(test_id: str) -> list[TestRow]:
    lineage_id = get_test_or_404(test_id).lineage_id
    return [
        TestRow.model_validate(version, from_attributes=True)
        for version in list_test_versions(lineage_id)
    ]


@router.post("/{test_id}/ready")
def mark_test_ready(test_id: str) -> TestDetail:
    get_test_or_404(test_id)
    return TestDetail.model_validate(mark_ready(test_id), from_attributes=True)


@router.put("/{test_id}")
def edit_test_as_new_version(test_id: str, request: EditTestRequest) -> TestDetail:
    get_test_or_404(test_id)
    new_version = edit_test(test_id, name=request.name, **request.spec.model_dump())
    return TestDetail.model_validate(new_version, from_attributes=True)


@router.post("/infer")
async def infer_test(request: InferTestRequest) -> InferTestResponse:
    inferred = await infer_test_spec_from_transcript(
        request.transcript, request.reported_issue
    )
    return InferTestResponse(
        reason=inferred.reason, name=inferred.name, spec=inferred.spec
    )


@router.post("", status_code=201)
def create_test(request: CreateTestRequest) -> TestRow:
    test = create_test_from_transcript(
        request.transcript,
        request.reported_issue,
        request.agent_version,
        name=request.name,
        spec=request.spec,
        inferred_spec=request.inferred_spec,
    )
    return TestRow.model_validate(test, from_attributes=True)


@router.post("/{test_id}/runs", status_code=202)
async def start_runs_of_test(test_id: str, request: StartRunsRequest) -> None:
    """Starts the runs and returns at once; each run appears in the runs list."""
    if get_test_or_404(test_id).status != TestStatus.READY:
        raise HTTPException(status_code=409, detail="mark the test ready first")
    for agent_version in request.agent_versions:
        task = asyncio.create_task(
            run_test_against_agent_version(
                test_id, agent_version, request.runs_per_version
            )
        )
        running_tasks.add(task)
        task.add_done_callback(running_tasks.discard)


@router.get("/{test_id}/runs")
def list_runs_of_test(test_id: str) -> list[RunRow]:
    lineage_id = get_test_or_404(test_id).lineage_id
    return [
        RunRow(
            id=simulation.id,
            test_id=test.id,
            test_version=test.version,
            agent_version=simulation.agent_version,
            status=simulation.status,
            started_at=simulation.started_at,
            ended_at=simulation.ended_at,
        )
        for simulation, test in list_runs_of_every_test_version(lineage_id)
    ]
