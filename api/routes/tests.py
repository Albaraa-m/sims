from fastapi import APIRouter

from api.schemas import CreateTestRequest, InferTestRequest, InferTestResponse, TestRow
from regression_tests.convert import infer_test_spec_from_transcript
from regression_tests.crud import create_test_from_transcript, list_latest_tests

router = APIRouter(prefix="/api/tests")


@router.get("")
def list_tests() -> list[TestRow]:
    return [
        TestRow.model_validate(test, from_attributes=True)
        for test in list_latest_tests()
    ]


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
