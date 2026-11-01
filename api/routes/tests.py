from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import NoResultFound

from api.schemas import (
    CreateTestRequest,
    EditTestRequest,
    InferTestRequest,
    InferTestResponse,
    TestDetail,
    TestRow,
)
from regression_tests.convert import infer_test_spec_from_transcript
from regression_tests.crud import (
    create_test_from_transcript,
    edit_test,
    get_test,
    list_latest_tests,
    list_test_versions,
)
from regression_tests.models import Test

router = APIRouter(prefix="/api/tests")


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
